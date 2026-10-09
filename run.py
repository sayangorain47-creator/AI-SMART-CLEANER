import os
import click
from datetime import datetime, timedelta, timezone
from app import create_app
from app.models import (
    db, User, WorkerProfile, Complaint, ComplaintImage, TaskAssignment,
    CompletionEvidence, StatusHistory, AppSetting, generate_tracking_id
)

app = create_app()

@app.cli.command("init-db")
def init_db_cmd():
    """Initializes database tables and default system settings."""
    with app.app_context():
        db.create_all()
        _ensure_default_settings()
        click.echo("✓ Database initialized successfully.")

def _ensure_default_settings():
    defaults = [
        ('default_deadline_hours', '12', 'Default cleaning deadline in hours'),
        ('require_after_photos', 'true', 'Require after-cleaning photo evidence'),
        ('contact_email', 'support@aismartcleaner.org', 'Public citizen support email'),
        ('contact_phone', '+1 (800) 555-0199', 'Public municipal support phone'),
        ('emergency_helpline', '1916', 'City municipal sanitation helpline'),
    ]
    for key, val, desc in defaults:
        if not AppSetting.query.filter_by(key=key).first():
            db.session.add(AppSetting(key=key, value=val, description=desc))
    db.session.commit()

@app.cli.command("create-admin")
@click.option("--username", prompt=True, help="Admin username")
@click.option("--email", prompt=True, help="Admin email address")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
@click.option("--fullname", default="System Administrator", help="Admin full name")
def create_admin_cmd(username, email, password, fullname):
    """Securely creates the first administrator account."""
    with app.app_context():
        db.create_all()
        _ensure_default_settings()

        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            click.echo(f"✗ User with username '{username}' or email '{email}' already exists.")
            return

        admin = User(
            username=username.strip(),
            email=email.strip(),
            role="admin",
            full_name=fullname.strip(),
            is_active=True
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"✓ Administrator account '{username}' created successfully!")

@app.cli.command("seed-data")
def seed_data_cmd():
    """Populates realistic seed data for development and demonstration."""
    with app.app_context():
        db.create_all()
        _ensure_default_settings()

        # Create Admin if not exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@aismartcleaner.org",
                role="admin",
                full_name="Chief Sanitation Officer",
                phone="+1 (800) 555-0100",
                is_active=True
            )
            admin.set_password("Admin@1234")
            db.session.add(admin)
            db.session.flush()
            click.echo("✓ Created default admin: admin / Admin@1234")

        # Create 4-5 Workers
        sample_workers = [
            ("worker_rajesh", "rajesh@cityclean.org", "Rajesh Kumar", "EMP-101", "Downtown Ward 4", 12.9716, 77.5946),
            ("worker_priya", "priya@cityclean.org", "Priya Sharma", "EMP-102", "North Sector 7", 12.9850, 77.6050),
            ("worker_arun", "arun@cityclean.org", "Arun Patel", "EMP-103", "Market Area Ward 2", 12.9600, 77.5800),
            ("worker_fatima", "fatima@cityclean.org", "Fatima Bi", "EMP-104", "Riverfront District", 12.9550, 77.6100),
            ("worker_david", "david@cityclean.org", "David Miller", "EMP-105", "Industrial East Zone", 12.9900, 77.6300),
        ]

        worker_objs = []
        for uname, uemail, ufullname, empid, locality, lat, lon in sample_workers:
            w = User.query.filter_by(username=uname).first()
            if not w:
                w = User(
                    username=uname,
                    email=uemail,
                    role="worker",
                    full_name=ufullname,
                    phone="+1-555-01" + empid[-2:],
                    is_active=True
                )
                w.set_password("Worker@1234")
                db.session.add(w)
                db.session.flush()

                prof = WorkerProfile(
                    user_id=w.id,
                    employee_id=empid,
                    assigned_locality=locality,
                    current_latitude=lat,
                    current_longitude=lon,
                    max_active_tasks=5,
                    notes=f"Dedicated sanitation supervisor for {locality}."
                )
                db.session.add(prof)
                click.echo(f"✓ Created worker: {uname} / Worker@1234")
            worker_objs.append(w)
        db.session.commit()

        # Create sample complaints across different states
        now = datetime.now(timezone.utc)
        
        sample_complaints_data = [
            {
                "cat": "Garbage Accumulation",
                "desc": "Heavy heap of mixed municipal solid waste unattended near the community park entrance.",
                "addr": "14 Green Park Road",
                "loc": "Downtown Ward 4",
                "landmark": "Near Community Gate 2",
                "prio": "High",
                "status": Complaint.STATUS_SUBMITTED,
                "hours_ago": 2,
                "deadline": 12,
                "worker_idx": None
            },
            {
                "cat": "Overflowing Dustbin",
                "desc": "Commercial market dustbin overflowing across the sidewalk, causing strong odor and obstruction.",
                "addr": "88 Central Market Avenue",
                "loc": "Market Area Ward 2",
                "landmark": "Opposite Metro Station Exit B",
                "prio": "Urgent",
                "status": Complaint.STATUS_ASSIGNED,
                "hours_ago": 3,
                "deadline": 12,
                "worker_idx": 2
            },
            {
                "cat": "Drainage Waste",
                "desc": "Plastic debris and organic waste blocking the surface drain, resulting in water overflow onto the road.",
                "addr": "52 North River Road",
                "loc": "Riverfront District",
                "landmark": "Behind Municipal Library",
                "prio": "Medium",
                "status": Complaint.STATUS_IN_PROGRESS,
                "hours_ago": 6,
                "deadline": 12,
                "worker_idx": 3
            },
            {
                "cat": "Illegal Dumping",
                "desc": "Construction debris and discarded items dumped overnight along the vacant roadside plot.",
                "addr": "104 Old Bypass Road",
                "loc": "Industrial East Zone",
                "landmark": "Near Warehouse Gate 4",
                "prio": "Medium",
                "status": Complaint.STATUS_COMPLETED,
                "hours_ago": 8,
                "deadline": 12,
                "worker_idx": 4
            },
            {
                "cat": "Road/Public Space Dirtiness",
                "desc": "Scattered litter and fallen foliage accumulated around the pedestrian walkway.",
                "addr": "25 Civic Center Plaza",
                "loc": "Downtown Ward 4",
                "landmark": "Opposite City Hall Garden",
                "prio": "Low",
                "status": Complaint.STATUS_VERIFIED,
                "hours_ago": 18,
                "deadline": 12,
                "worker_idx": 0
            },
            {
                "cat": "Overflowing Dustbin",
                "desc": "Public waste bin near hospital gate overflowing with discarded cups and wrappers.",
                "addr": "3 Hospital Road",
                "loc": "North Sector 7",
                "landmark": "Civil Hospital Gate 1",
                "prio": "Urgent",
                "status": Complaint.STATUS_IN_PROGRESS,
                "hours_ago": 15,  # OVERDUE (15 > 12)
                "deadline": 12,
                "worker_idx": 1
            }
        ]

        if Complaint.query.count() == 0:
            for item in sample_complaints_data:
                created = now - timedelta(hours=item["hours_ago"])
                target_deadline = created + timedelta(hours=item["deadline"])
                tid = generate_tracking_id()

                c = Complaint(
                    tracking_id=tid,
                    complainant_name="Civic Citizen",
                    complainant_phone="+1-555-0188",
                    complainant_email="citizen@example.org",
                    category=item["cat"],
                    description=item["desc"],
                    address=item["addr"],
                    locality=item["loc"],
                    landmark=item["landmark"],
                    priority=item["prio"],
                    status=item["status"],
                    deadline_hours=item["deadline"],
                    target_resolution_at=target_deadline,
                    created_at=created,
                    updated_at=created
                )

                if item["status"] in [Complaint.STATUS_COMPLETED, Complaint.STATUS_VERIFIED]:
                    c.completed_at = created + timedelta(hours=min(item["deadline"] - 2, item["hours_ago"]))
                if item["status"] == Complaint.STATUS_VERIFIED:
                    c.verified_at = c.completed_at + timedelta(hours=1)

                db.session.add(c)
                db.session.flush()

                # Status history log
                h1 = StatusHistory(
                    complaint_id=c.id,
                    old_status=None,
                    new_status=Complaint.STATUS_SUBMITTED,
                    notes="Public complaint submitted.",
                    timestamp=created
                )
                db.session.add(h1)

                if item["worker_idx"] is not None:
                    assigned_worker = worker_objs[item["worker_idx"]]
                    assign_time = created + timedelta(minutes=30)
                    task_assign = TaskAssignment(
                        complaint_id=c.id,
                        worker_id=assigned_worker.id,
                        assigned_by_id=admin.id,
                        assigned_at=assign_time,
                        is_current=True,
                        notes="Dispatched to field officer."
                    )
                    db.session.add(task_assign)

                    h2 = StatusHistory(
                        complaint_id=c.id,
                        old_status=Complaint.STATUS_SUBMITTED,
                        new_status=Complaint.STATUS_ASSIGNED,
                        changed_by_id=admin.id,
                        notes=f"Assigned to {assigned_worker.full_name}.",
                        timestamp=assign_time
                    )
                    db.session.add(h2)

                    if item["status"] in [Complaint.STATUS_IN_PROGRESS, Complaint.STATUS_COMPLETED, Complaint.STATUS_VERIFIED]:
                        h3 = StatusHistory(
                            complaint_id=c.id,
                            old_status=Complaint.STATUS_ASSIGNED,
                            new_status=Complaint.STATUS_IN_PROGRESS,
                            changed_by_id=assigned_worker.id,
                            notes="Field team initiated cleanup operations.",
                            timestamp=assign_time + timedelta(minutes=45)
                        )
                        db.session.add(h3)

                    if item["status"] in [Complaint.STATUS_COMPLETED, Complaint.STATUS_VERIFIED]:
                        ev = CompletionEvidence(
                            complaint_id=c.id,
                            worker_id=assigned_worker.id,
                            completion_notes="Debris thoroughly cleared, bin sanitized, surrounding sidewalk washed.",
                            submitted_at=c.completed_at
                        )
                        db.session.add(ev)

                        h4 = StatusHistory(
                            complaint_id=c.id,
                            old_status=Complaint.STATUS_IN_PROGRESS,
                            new_status=Complaint.STATUS_COMPLETED,
                            changed_by_id=assigned_worker.id,
                            notes="Cleanup completed. Evidence uploaded.",
                            timestamp=c.completed_at
                        )
                        db.session.add(h4)

                    if item["status"] == Complaint.STATUS_VERIFIED:
                        ev.verified_by_id = admin.id
                        ev.verification_notes = "Inspected and confirmed spotless cleanup."
                        ev.verified_at = c.verified_at
                        ev.is_approved = True

                        h5 = StatusHistory(
                            complaint_id=c.id,
                            old_status=Complaint.STATUS_COMPLETED,
                            new_status=Complaint.STATUS_VERIFIED,
                            changed_by_id=admin.id,
                            notes="Verified & closed by admin.",
                            timestamp=c.verified_at
                        )
                        db.session.add(h5)

            db.session.commit()
            click.echo("✓ Sample complaints seeded across various lifecycle stages (including an overdue task).")
        else:
            click.echo("✓ Database already contains complaints, skipping complaint seeding.")

if __name__ == '__main__':
    # Support both normal server startup and direct CLI commands.
    # Without this dispatch, `python run.py init-db` would ignore `init-db`
    # and start the development server, appearing to hang during setup.
    import sys

    if len(sys.argv) > 1:
        app.cli.main(args=sys.argv[1:], prog_name='run.py')
    else:
        with app.app_context():
            db.create_all()
            _ensure_default_settings()
        app.run(host='127.0.0.1', port=5000, debug=True)
