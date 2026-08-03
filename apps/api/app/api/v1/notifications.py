from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db), user: User = Depends(get_current_user), unread_only: bool = False
) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    return list(db.scalars(query.order_by(Notification.created_at.desc())))


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise NotFoundError("Notification")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all", status_code=204)
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).update(
        {"is_read": True}
    )
    db.commit()
