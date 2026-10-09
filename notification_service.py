from datetime import datetime, timezone
from app.models import db, Notification

def send_notification(user_id: int, title: str, message: str, link: str = None) -> Notification:
    """
    Creates an in-app notification for a given user.
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(notification)
    return notification

def mark_notifications_read(user_id: int):
    """Marks all unread notifications as read for a given user."""
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
