import os
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory, current_app, abort
from app.public import public_bp
from app.public.forms import ComplaintForm, TrackForm
from app.models import db, Complaint, ComplaintImage, StatusHistory, User, AppSetting, generate_tracking_id
from app.services.deadline_service import calculate_target_resolution
from app.services.image_service import validate_and_save_image
from app.services.rate_limiter import is_rate_limited, record_attempt
from app.services.notification_service import send_notification

@public_bp.route('/')
def index():
    # Live stats retrieved strictly from database
    total_complaints = Complaint.query.count()
    verified_cleaned = Complaint.query.filter_by(status=Complaint.STATUS_VERIFIED).count()
    active_operations = Complaint.query.filter(
        Complaint.status.in_([Complaint.STATUS_ASSIGNED, Complaint.STATUS_ACCEPTED, Complaint.STATUS_IN_PROGRESS])
    ).count()
    
    # Calculate on-time resolution rate
    verified_tasks = Complaint.query.filter_by(status=Complaint.STATUS_VERIFIED).all()
    if verified_tasks:
        on_time_count = sum(1 for c in verified_tasks if c.is_on_time)
        on_time_pct = round((on_time_count / len(verified_tasks)) * 100, 1)
    else:
        on_time_pct = 100.0 if verified_cleaned > 0 else 0.0

    # Recent verified transformations for public display
    recent_resolved = Complaint.query.filter_by(status=Complaint.STATUS_VERIFIED)\
        .order_by(Complaint.verified_at.desc())\
        .limit(3).all()

    contact_email = AppSetting.get_value('contact_email', current_app.config.get('CONTACT_EMAIL'))
    contact_phone = AppSetting.get_value('contact_phone', current_app.config.get('CONTACT_PHONE'))
    helpline = AppSetting.get_value('emergency_helpline', current_app.config.get('MUNICIPAL_HELPLINE'))

    return render_template(
        'public/index.html',
        total_complaints=total_complaints,
        verified_cleaned=verified_cleaned,
        active_operations=active_operations,
        on_time_pct=on_time_pct,
        recent_resolved=recent_resolved,
        contact_email=contact_email,
        contact_phone=contact_phone,
        helpline=helpline
    )

@public_bp.route('/report', methods=['GET', 'POST'])
def report():
    form = ComplaintForm()
    ip_addr = request.remote_addr or 'unknown'
    rate_key = f"report_{ip_addr}"

    if form.validate_on_submit():
        if is_rate_limited(rate_key, limit=10, window_seconds=300):
            flash("You have reached the maximum number of submissions allowed in 5 minutes. Please try again shortly.", "danger")
            return render_template('public/report.html', form=form), 429

        record_attempt(rate_key)

        # Generate unique tracking ID
        tracking_id = generate_tracking_id()
        # Verify collision avoidance
        while Complaint.query.filter_by(tracking_id=tracking_id).first():
            tracking_id = generate_tracking_id()

        now = datetime.now(timezone.utc)
        deadline_hours, target_res = calculate_target_resolution(now)

        complaint = Complaint(
            tracking_id=tracking_id,
            complainant_name=form.complainant_name.data.strip() if form.complainant_name.data else None,
            complainant_phone=form.complainant_phone.data.strip() if form.complainant_phone.data else None,
            complainant_email=form.complainant_email.data.strip() if form.complainant_email.data else None,
            category=form.category.data,
            description=form.description.data.strip(),
            address=form.address.data.strip(),
            locality=form.locality.data.strip(),
            landmark=form.landmark.data.strip() if form.landmark.data else None,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            status=Complaint.STATUS_SUBMITTED,
            priority='Medium',
            deadline_hours=deadline_hours,
            target_resolution_at=target_res,
            created_at=now,
            updated_at=now
        )
        db.session.add(complaint)
        db.session.flush() # Populate complaint.id

        # Process uploaded images
        uploaded_files = request.files.getlist('images')
        saved_images_count = 0
        
        for file in uploaded_files:
            if file and file.filename:
                try:
                    rel_path, orig_name, file_size = validate_and_save_image(file, folder_type='before')
                    img_record = ComplaintImage(
                        complaint_id=complaint.id,
                        image_type='before',
                        file_path=rel_path,
                        original_filename=orig_name,
                        file_size=file_size,
                        created_at=now
                    )
                    db.session.add(img_record)
                    saved_images_count += 1
                except ValueError as err:
                    db.session.rollback()
                    flash(f"Upload error: {str(err)}", "danger")
                    return render_template('public/report.html', form=form)

        # Record initial status transition in history
        history = StatusHistory(
            complaint_id=complaint.id,
            old_status=None,
            new_status=Complaint.STATUS_SUBMITTED,
            notes="Citizen reported dirty area via web portal.",
            timestamp=now
        )
        db.session.add(history)

        # Notify admins
        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            send_notification(
                user_id=admin.id,
                title="New Cleanliness Complaint Logged",
                message=f"Complaint #{tracking_id} reported in {complaint.locality} ({complaint.category}).",
                link=f"/admin/complaints/{complaint.id}"
            )

        db.session.commit()
        return redirect(url_for('public.report_success', tracking_id=tracking_id))

    return render_template('public/report.html', form=form)

@public_bp.route('/report/success/<tracking_id>')
def report_success(tracking_id):
    complaint = Complaint.query.filter_by(tracking_id=tracking_id).first_or_404()
    return render_template('public/report_success.html', complaint=complaint)

@public_bp.route('/track', methods=['GET', 'POST'])
def track():
    form = TrackForm()
    complaint_data = None
    searched = False
    
    # Also support GET query param ?id=ASC-...
    query_id = request.args.get('id')
    if query_id and request.method == 'GET':
        form.tracking_id.data = query_id
        searched = True
        complaint = Complaint.query.filter_by(tracking_id=query_id.strip()).first()
        if complaint:
            complaint_data = complaint.get_public_dict()
        else:
            flash(f"No complaint found matching ID '{query_id}'. Please double-check your tracking ID.", "warning")

    elif form.validate_on_submit():
        searched = True
        tid = form.tracking_id.data.strip()
        complaint = Complaint.query.filter_by(tracking_id=tid).first()
        if complaint:
            complaint_data = complaint.get_public_dict()
        else:
            flash(f"No complaint found matching ID '{tid}'. Please verify the tracking ID.", "warning")

    return render_template('public/track.html', form=form, complaint_data=complaint_data, searched=searched)

@public_bp.route('/api/stats')
def api_stats():
    total = Complaint.query.count()
    verified = Complaint.query.filter_by(status=Complaint.STATUS_VERIFIED).count()
    in_progress = Complaint.query.filter(
        Complaint.status.in_([Complaint.STATUS_ASSIGNED, Complaint.STATUS_ACCEPTED, Complaint.STATUS_IN_PROGRESS])
    ).count()
    return jsonify({
        'total': total,
        'verified': verified,
        'active': in_progress
    })

@public_bp.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    # Only allow 'before' or 'after' folders
    if folder not in ['before', 'after']:
        abort(404)
        
    base_folder = current_app.config['UPLOAD_BEFORE_FOLDER'] if folder == 'before' else current_app.config['UPLOAD_AFTER_FOLDER']
    return send_from_directory(base_folder, filename)
