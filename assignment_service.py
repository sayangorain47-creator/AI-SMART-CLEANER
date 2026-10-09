import math
from datetime import datetime, timezone
from app.models import db, Complaint, User, WorkerProfile, TaskAssignment, StatusHistory
from app.services.notification_service import send_notification

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points on Earth in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_active_workers() -> list[User]:
    """Returns all active workers."""
    return User.query.filter_by(role='worker', is_active=True).all()

def find_best_worker_for_complaint(complaint: Complaint) -> User | None:
    """
    Finds the best active worker for automatic assignment:
    1. Only active workers with role 'worker'
    2. Check workload capacity (active tasks < max_active_tasks)
    3. If complaint coordinates and worker coordinates exist, sort by proximity
    4. Otherwise, sort by lowest active task count
    """
    active_workers = get_active_workers()
    if not active_workers:
        return None

    # Filter out workers who have reached max capacity if others have capacity
    candidates = []
    for w in active_workers:
        prof = w.worker_profile
        max_tasks = prof.max_active_tasks if prof else 5
        curr_tasks = prof.active_tasks_count if prof else 0
        candidates.append({
            'worker': w,
            'curr_tasks': curr_tasks,
            'max_tasks': max_tasks,
            'has_capacity': curr_tasks < max_tasks,
            'lat': prof.current_latitude if prof else None,
            'lon': prof.current_longitude if prof else None,
        })

    # Prefer workers with capacity
    under_capacity = [c for c in candidates if c['has_capacity']]
    pool = under_capacity if under_capacity else candidates

    # Check if geographic proximity is possible
    can_use_geo = (complaint.latitude is not None and complaint.longitude is not None)
    
    if can_use_geo:
        # Check if any candidate has coordinates
        geo_candidates = [c for c in pool if c['lat'] is not None and c['lon'] is not None]
        if geo_candidates:
            # Sort by distance, then by active task count
            geo_candidates.sort(key=lambda c: (
                haversine_distance(complaint.latitude, complaint.longitude, c['lat'], c['lon']),
                c['curr_tasks']
            ))
            return geo_candidates[0]['worker']

    # Otherwise sort purely by least loaded worker
    pool.sort(key=lambda c: (c['curr_tasks'], c['worker'].id))
    return pool[0]['worker']

def assign_task(
    complaint: Complaint,
    worker: User,
    assigned_by: User,
    notes: str = None,
    reassignment_reason: str = None
) -> TaskAssignment:
    """
    Assigns or reassigns a complaint to a worker.
    """
    if not worker or not worker.is_active or worker.role != 'worker':
        raise ValueError("Cannot assign to an inactive or non-worker user.")

    current_assignment = complaint.current_assignment
    
    # Check if already assigned to the same worker
    if current_assignment and current_assignment.worker_id == worker.id and complaint.status in [Complaint.STATUS_ASSIGNED, Complaint.STATUS_ACCEPTED, Complaint.STATUS_IN_PROGRESS]:
        raise ValueError(f"Complaint is already assigned to {worker.full_name}.")

    now = datetime.now(timezone.utc)
    old_worker_id = None

    if current_assignment:
        current_assignment.is_current = False
        old_worker_id = current_assignment.worker_id
        if not reassignment_reason:
            reassignment_reason = "Administrative reassignment."

    new_assignment = TaskAssignment(
        complaint_id=complaint.id,
        worker_id=worker.id,
        assigned_by_id=assigned_by.id if assigned_by else None,
        assigned_at=now,
        is_current=True,
        reassigned_from_worker_id=old_worker_id,
        reassignment_reason=reassignment_reason,
        notes=notes
    )
    db.session.add(new_assignment)

    # Transition complaint status to ASSIGNED
    old_status = complaint.status
    complaint.status = Complaint.STATUS_ASSIGNED
    complaint.updated_at = now

    # Record history
    history_note = f"Assigned to field officer {worker.full_name} ({worker.username})."
    if reassignment_reason:
        history_note += f" Reassignment reason: {reassignment_reason}"
    if notes:
        history_note += f" Notes: {notes}"

    history = StatusHistory(
        complaint_id=complaint.id,
        old_status=old_status,
        new_status=Complaint.STATUS_ASSIGNED,
        changed_by_id=assigned_by.id if assigned_by else None,
        notes=history_note,
        timestamp=now
    )
    db.session.add(history)

    # In-app notifications
    send_notification(
        user_id=worker.id,
        title="New Sanitation Task Assigned",
        message=f"You have been assigned complaint #{complaint.tracking_id} at {complaint.locality}.",
        link=f"/worker/tasks/{complaint.id}"
    )

    if old_worker_id and old_worker_id != worker.id:
        send_notification(
            user_id=old_worker_id,
            title="Task Reassigned",
            message=f"Complaint #{complaint.tracking_id} has been reassigned to another field officer.",
            link="/worker/dashboard"
        )

    db.session.commit()
    return new_assignment
