from datetime import datetime, timedelta, timezone
import secrets
import string
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def generate_tracking_id() -> str:
    """
    Generates a secure, non-guessable, human-readable tracking ID.
    Format: ASC-YYYYMMDD-XXXX (where XXXX is 6 random uppercase chars/digits).
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    alphabet = string.ascii_uppercase + string.digits
    # Remove easily confused characters: 0, O, 1, I
    clean_alphabet = [c for c in alphabet if c not in ('0', 'O', '1', 'I')]
    suffix = ''.join(secrets.choice(clean_alphabet) for _ in range(6))
    return f"ASC-{date_str}-{suffix}"


class AppSetting(db.Model):
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_value(cls, key: str, value: str, description: str = None) -> "AppSetting":
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        else:
            setting.value = str(value)
            if description:
                setting.description = description
        db.session.commit()
        return setting


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='worker')  # 'admin' or 'worker'
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    worker_profile = db.relationship('WorkerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    assignments = db.relationship('TaskAssignment', foreign_keys='TaskAssignment.worker_id', backref='worker', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    @property
    def is_worker(self) -> bool:
        return self.role == 'worker'

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class WorkerProfile(db.Model):
    __tablename__ = 'worker_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    employee_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    assigned_locality = db.Column(db.String(100), nullable=True)
    current_latitude = db.Column(db.Float, nullable=True)
    current_longitude = db.Column(db.Float, nullable=True)
    max_active_tasks = db.Column(db.Integer, default=5, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    @property
    def active_tasks_count(self) -> int:
        from app.models import Complaint, TaskAssignment
        return TaskAssignment.query.join(Complaint).filter(
            TaskAssignment.worker_id == self.user_id,
            TaskAssignment.is_current == True,
            Complaint.status.in_(['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'REOPENED'])
        ).count()

    @property
    def completed_tasks_count(self) -> int:
        from app.models import Complaint, TaskAssignment
        return TaskAssignment.query.join(Complaint).filter(
            TaskAssignment.worker_id == self.user_id,
            Complaint.status.in_(['COMPLETED', 'VERIFIED'])
        ).count()


class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    # Status constants
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_PENDING_REVIEW = 'PENDING_REVIEW'
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'          # Awaiting Admin Verification
    STATUS_VERIFIED = 'VERIFIED'            # Verified and closed
    STATUS_REJECTED = 'REJECTED'            # Rejected with reason
    STATUS_REOPENED = 'REOPENED'            # Returned for more cleaning
    
    VALID_STATUSES = [
        STATUS_SUBMITTED,
        STATUS_PENDING_REVIEW,
        STATUS_ASSIGNED,
        STATUS_ACCEPTED,
        STATUS_IN_PROGRESS,
        STATUS_COMPLETED,
        STATUS_VERIFIED,
        STATUS_REJECTED,
        STATUS_REOPENED
    ]

    # Category constants
    CATEGORIES = [
        'Garbage Accumulation',
        'Overflowing Dustbin',
        'Illegal Dumping',
        'Road/Public Space Dirtiness',
        'Drainage Waste',
        'Other'
    ]

    # Priority constants
    PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']

    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    
    # Citizen details (optional to preserve privacy)
    complainant_name = db.Column(db.String(100), nullable=True)
    complainant_phone = db.Column(db.String(30), nullable=True)
    complainant_email = db.Column(db.String(120), nullable=True)
    
    # Waste Details
    category = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    locality = db.Column(db.String(100), nullable=False, index=True)
    landmark = db.Column(db.String(150), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Operational Status & SLA
    priority = db.Column(db.String(20), default='Medium', nullable=False)
    status = db.Column(db.String(30), default=STATUS_SUBMITTED, nullable=False, index=True)
    deadline_hours = db.Column(db.Integer, default=12, nullable=False)
    target_resolution_at = db.Column(db.DateTime, nullable=False, index=True)
    
    # Timestamps & Closure
    completed_at = db.Column(db.DateTime, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    images = db.relationship('ComplaintImage', backref='complaint', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('TaskAssignment', backref='complaint', lazy='dynamic', cascade='all, delete-orphan', order_by='TaskAssignment.assigned_at.desc()')
    evidence = db.relationship('CompletionEvidence', backref='complaint', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('StatusHistory', backref='complaint', lazy='dynamic', cascade='all, delete-orphan', order_by='StatusHistory.timestamp.asc()')

    @property
    def current_assignment(self):
        return self.assignments.filter_by(is_current=True).first()

    @property
    def assigned_worker(self):
        curr = self.current_assignment
        return curr.worker if curr else None

    @property
    def is_overdue(self) -> bool:
        # A task is overdue if not verified/completed/rejected and target_resolution_at has passed
        if self.status in [self.STATUS_VERIFIED, self.STATUS_REJECTED]:
            return False
        # If worker already marked completed, check if completion met the deadline
        if self.status == self.STATUS_COMPLETED and self.completed_at:
            return self.completed_at > self.target_resolution_at
        
        now = datetime.now(timezone.utc)
        # target_resolution_at might be naive in SQLite, ensure comparison is robust
        target = self.target_resolution_at
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        return now > target

    @property
    def is_on_time(self) -> bool:
        if not self.completed_at:
            return False
        target = self.target_resolution_at
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        comp = self.completed_at
        if comp.tzinfo is None:
            comp = comp.replace(tzinfo=timezone.utc)
        return comp <= target

    @property
    def deadline_status_info(self) -> dict:
        now = datetime.now(timezone.utc)
        target = self.target_resolution_at
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
            
        if self.status == self.STATUS_VERIFIED:
            return {'badge': 'success', 'text': 'Verified & Closed', 'overdue': False}
        if self.status == self.STATUS_REJECTED:
            return {'badge': 'secondary', 'text': 'Rejected', 'overdue': False}
        if self.status == self.STATUS_COMPLETED:
            if self.is_on_time:
                return {'badge': 'success', 'text': 'Completed on time', 'overdue': False}
            else:
                return {'badge': 'warning', 'text': 'Completed late', 'overdue': True}
                
        diff = target - now
        if diff.total_seconds() < 0:
            overdue_mins = int(abs(diff.total_seconds()) // 60)
            hours = overdue_mins // 60
            mins = overdue_mins % 60
            time_str = f"{hours}h {mins}m overdue" if hours > 0 else f"{mins}m overdue"
            return {'badge': 'danger', 'text': time_str, 'overdue': True}
        else:
            remaining_mins = int(diff.total_seconds() // 60)
            hours = remaining_mins // 60
            mins = remaining_mins % 60
            time_str = f"{hours}h {mins}m remaining" if hours > 0 else f"{mins}m remaining"
            return {'badge': 'info', 'text': time_str, 'overdue': False}

    @property
    def before_images(self):
        return self.images.filter_by(image_type='before').all()

    @property
    def after_images(self):
        return self.images.filter_by(image_type='after').all()

    @property
    def latest_evidence(self):
        return self.evidence.order_by(CompletionEvidence.submitted_at.desc()).first()

    def get_public_dict(self) -> dict:
        """
        Public-safe serialized representation of complaint.
        NEVER leaks complainant name, phone, email, internal notes, or worker identities.
        """
        # Map internal status to citizen-friendly status label and explanation
        status_map = {
            self.STATUS_SUBMITTED: ('Report Submitted', 'Your report has been logged and queued for administrative review.'),
            self.STATUS_PENDING_REVIEW: ('Under Review', 'The municipal control room is reviewing your report details and priority.'),
            self.STATUS_ASSIGNED: ('Sanitation Team Assigned', 'A field sanitation officer has been dispatched for cleanup.'),
            self.STATUS_ACCEPTED: ('Accepted by Field Officer', 'The field worker has acknowledged the task and is en route.'),
            self.STATUS_IN_PROGRESS: ('Cleaning in Progress', 'Sanitation operations are actively ongoing at the site.'),
            self.STATUS_COMPLETED: ('Cleaning Done (Pending Verification)', 'Field officer has uploaded after-cleaning evidence and requested verification.'),
            self.STATUS_VERIFIED: ('Resolved & Verified', 'Municipal authorities inspected the site evidence and confirmed full cleanup.'),
            self.STATUS_REJECTED: ('Report Closed', f"Report could not be processed: {self.rejection_reason or 'Duplicate or invalid location'}"),
            self.STATUS_REOPENED: ('Further Action Required', 'Audit requested additional cleaning at the location.')
        }
        
        friendly_label, friendly_desc = status_map.get(self.status, (self.status, 'Status update in progress.'))
        
        timeline = []
        for h in self.status_history:
            step_label, _ = status_map.get(h.new_status, (h.new_status, ''))
            timeline.append({
                'status': step_label,
                'timestamp': h.timestamp.strftime('%b %d, %Y %I:%M %p UTC'),
                'raw_status': h.new_status
            })

        return {
            'tracking_id': self.tracking_id,
            'category': self.category,
            'description': self.description,
            'locality': self.locality,
            'landmark': self.landmark,
            'address': self.address,
            'status': self.status,
            'status_label': friendly_label,
            'status_description': friendly_desc,
            'priority': self.priority,
            'created_at': self.created_at.strftime('%b %d, %Y %I:%M %p UTC'),
            'target_deadline': self.target_resolution_at.strftime('%b %d, %Y %I:%M %p UTC'),
            'verified_at': self.verified_at.strftime('%b %d, %Y %I:%M %p UTC') if self.verified_at else None,
            'before_images': [img.file_path for img in self.before_images],
            'after_images': [img.file_path for img in self.after_images] if self.status in [self.STATUS_COMPLETED, self.STATUS_VERIFIED] else [],
            'timeline': timeline,
            'is_overdue': self.is_overdue
        }


class ComplaintImage(db.Model):
    __tablename__ = 'complaint_images'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False, index=True)
    image_type = db.Column(db.String(20), nullable=False)  # 'before' or 'after'
    file_path = db.Column(db.String(255), nullable=False)   # stored relative url e.g. 'uploads/before/uuid.jpg'
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)      # bytes
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class TaskAssignment(db.Model):
    __tablename__ = 'task_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_current = db.Column(db.Boolean, default=True, nullable=False)
    reassigned_from_worker_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reassignment_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])
    reassigned_from = db.relationship('User', foreign_keys=[reassigned_from_worker_id])


class CompletionEvidence(db.Model):
    __tablename__ = 'completion_evidences'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    completion_notes = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Verification details
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    is_approved = db.Column(db.Boolean, nullable=True)

    worker = db.relationship('User', foreign_keys=[worker_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id', ondelete='CASCADE'), nullable=False, index=True)
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    changed_by = db.relationship('User', foreign_keys=[changed_by_id])


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
