import io
import csv
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from app.models import db, Complaint, User, WorkerProfile, TaskAssignment

def get_dashboard_metrics(start_date: datetime = None, end_date: datetime = None) -> dict:
    """
    Computes all live database analytics for the Admin Dashboard.
    Handles empty datasets without errors.
    """
    query = Complaint.query
    if start_date:
        query = query.filter(Complaint.created_at >= start_date)
    if end_date:
        query = query.filter(Complaint.created_at <= end_date)

    all_complaints = query.all()
    total = len(all_complaints)
    
    pending_review = sum(1 for c in all_complaints if c.status in [Complaint.STATUS_SUBMITTED, Complaint.STATUS_PENDING_REVIEW])
    unassigned = sum(1 for c in all_complaints if c.status in [Complaint.STATUS_SUBMITTED, Complaint.STATUS_PENDING_REVIEW] or c.current_assignment is None)
    assigned = sum(1 for c in all_complaints if c.status in [Complaint.STATUS_ASSIGNED, Complaint.STATUS_ACCEPTED])
    in_progress = sum(1 for c in all_complaints if c.status in [Complaint.STATUS_IN_PROGRESS, Complaint.STATUS_REOPENED])
    completed_awaiting = sum(1 for c in all_complaints if c.status == Complaint.STATUS_COMPLETED)
    verified = sum(1 for c in all_complaints if c.status == Complaint.STATUS_VERIFIED)
    rejected = sum(1 for c in all_complaints if c.status == Complaint.STATUS_REJECTED)
    
    # Overdue count
    overdue_count = sum(1 for c in all_complaints if c.is_overdue)
    
    # Average resolution time in hours for verified tasks
    verified_tasks = [c for c in all_complaints if c.status == Complaint.STATUS_VERIFIED and c.verified_at]
    if verified_tasks:
        total_resolution_seconds = sum(
            (c.verified_at - c.created_at).total_seconds() for c in verified_tasks
        )
        avg_resolution_hours = round(total_resolution_seconds / (len(verified_tasks) * 3600), 1)
    else:
        avg_resolution_hours = 0.0

    # On-time completion rate among completed/verified
    resolved_or_completed = [c for c in all_complaints if c.status in [Complaint.STATUS_COMPLETED, Complaint.STATUS_VERIFIED] and c.completed_at]
    if resolved_or_completed:
        on_time_count = sum(1 for c in resolved_or_completed if c.is_on_time)
        on_time_rate = round((on_time_count / len(resolved_or_completed)) * 100, 1)
    else:
        on_time_rate = 100.0 if verified > 0 else 0.0

    # Category breakdown
    category_counts = {}
    for cat in Complaint.CATEGORIES:
        category_counts[cat] = 0
    for c in all_complaints:
        category_counts[c.category] = category_counts.get(c.category, 0) + 1

    # Daily trend (last 7 days or date range)
    now = datetime.now(timezone.utc)
    daily_trends = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        day_count = sum(
            1 for c in all_complaints
            if day_start <= (c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)) < day_end
        )
        daily_trends.append({
            'date': day.strftime('%b %d'),
            'count': day_count
        })

    # Worker workload metrics
    active_workers = User.query.filter_by(role='worker').all()
    worker_stats = []
    for w in active_workers:
        prof = w.worker_profile
        worker_stats.append({
            'id': w.id,
            'name': w.full_name,
            'username': w.username,
            'is_active': w.is_active,
            'locality': prof.assigned_locality if prof else 'General',
            'active_tasks': prof.active_tasks_count if prof else 0,
            'completed_tasks': prof.completed_tasks_count if prof else 0,
            'max_tasks': prof.max_active_tasks if prof else 5
        })

    return {
        'total': total,
        'pending_review': pending_review,
        'unassigned': unassigned,
        'assigned': assigned,
        'in_progress': in_progress,
        'overdue': overdue_count,
        'completed': completed_awaiting,
        'verified': verified,
        'rejected': rejected,
        'avg_resolution_hours': avg_resolution_hours,
        'on_time_rate': on_time_rate,
        'category_counts': category_counts,
        'daily_trends': daily_trends,
        'worker_stats': worker_stats
    }

def generate_complaints_csv(query_filter=None) -> str:
    """
    Generates a CSV report string of complaints.
    """
    if query_filter is not None:
        complaints = query_filter.all()
    else:
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Tracking ID',
        'Category',
        'Status',
        'Priority',
        'Locality',
        'Address',
        'Landmark',
        'Reported At (UTC)',
        'Deadline (Hours)',
        'Target Resolution (UTC)',
        'Completed At (UTC)',
        'Verified At (UTC)',
        'On Time',
        'Overdue',
        'Assigned Worker',
        'Complainant Name',
        'Complainant Phone',
        'Rejection Reason'
    ])
    
    for c in complaints:
        assigned_name = c.assigned_worker.full_name if c.assigned_worker else 'Unassigned'
        writer.writerow([
            c.tracking_id,
            c.category,
            c.status,
            c.priority,
            c.locality,
            c.address,
            c.landmark or '',
            c.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            c.deadline_hours,
            c.target_resolution_at.strftime('%Y-%m-%d %H:%M:%S'),
            c.completed_at.strftime('%Y-%m-%d %H:%M:%S') if c.completed_at else '',
            c.verified_at.strftime('%Y-%m-%d %H:%M:%S') if c.verified_at else '',
            'Yes' if c.is_on_time else 'No' if c.completed_at else 'N/A',
            'Yes' if c.is_overdue else 'No',
            assigned_name,
            c.complainant_name or 'Anonymous',
            c.complainant_phone or 'N/A',
            c.rejection_reason or ''
        ])
        
    return output.getvalue()
