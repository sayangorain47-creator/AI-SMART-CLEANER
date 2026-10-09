from datetime import datetime, timedelta, timezone
from app.models import db, Complaint, AppSetting

def get_default_deadline_hours() -> int:
    try:
        val = AppSetting.get_value('default_deadline_hours', '12')
        return int(val)
    except (ValueError, TypeError):
        return 12

def calculate_target_resolution(start_time: datetime = None, hours: int = None) -> tuple[int, datetime]:
    """
    Computes deadline hours and target_resolution_at timestamp.
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc)
    if hours is None:
        hours = get_default_deadline_hours()
    
    target_time = start_time + timedelta(hours=hours)
    return hours, target_time

def update_complaint_deadline(complaint: Complaint, new_hours: int, changed_by_user_id: int = None, reason: str = None) -> Complaint:
    """
    Updates the cleaning deadline for an active complaint.
    """
    if new_hours <= 0:
        raise ValueError("Deadline must be at least 1 hour.")
        
    start_time = complaint.created_at
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
        
    complaint.deadline_hours = new_hours
    complaint.target_resolution_at = start_time + timedelta(hours=new_hours)
    complaint.updated_at = datetime.now(timezone.utc)
    
    from app.models import StatusHistory
    note = f"Deadline updated to {new_hours} hours from report time."
    if reason:
        note += f" Reason: {reason}"
        
    history = StatusHistory(
        complaint_id=complaint.id,
        old_status=complaint.status,
        new_status=complaint.status,
        changed_by_id=changed_by_user_id,
        notes=note,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(history)
    db.session.commit()
    return complaint

def get_overdue_complaints():
    """
    Returns complaints that are currently overdue.
    A task is overdue if not verified/rejected, and:
    - If completed: completed_at > target_resolution_at
    - If still active: now > target_resolution_at
    """
    now = datetime.now(timezone.utc)
    all_active = Complaint.query.filter(
        Complaint.status.notin_([Complaint.STATUS_VERIFIED, Complaint.STATUS_REJECTED])
    ).all()
    
    overdue_list = [c for c in all_active if c.is_overdue]
    return overdue_list
