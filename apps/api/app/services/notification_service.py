from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


def notify(
    db: Session,
    user_id: UUID,
    type: NotificationType,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification:
    notification = Notification(user_id=user_id, type=type, title=title, body=body, link=link)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
