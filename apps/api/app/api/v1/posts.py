from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.post import Post, PostStatus
from app.models.user import User, UserRole
from app.schemas.post import PostCreate, PostRead, PostUpdate

router = APIRouter(prefix="/posts", tags=["content-calendar"])

_PRIVILEGED = {UserRole.OWNER, UserRole.ADMIN}


def _get_owned_post(db: Session, user: User, post_id: UUID) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post")
    if user.role not in _PRIVILEGED and post.author_id != user.id:
        raise ForbiddenError()
    return post


@router.get("", response_model=list[PostRead])
def list_posts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status: PostStatus | None = None,
) -> list[Post]:
    query = select(Post)
    if user.role not in _PRIVILEGED:
        query = query.where(Post.author_id == user.id)
    if status is not None:
        query = query.where(Post.status == status)
    return list(db.scalars(query.order_by(Post.scheduled_at.asc().nulls_last())))


@router.post("", response_model=PostRead, status_code=201)
def create_post(payload: PostCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Post:
    data = payload.model_dump()
    if data.get("scheduled_at") and data["status"] == PostStatus.DRAFT:
        data["status"] = PostStatus.SCHEDULED
    post = Post(author_id=user.id, **data)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Post:
    return _get_owned_post(db, user, post_id)


@router.patch("/{post_id}", response_model=PostRead)
def update_post(
    post_id: UUID, payload: PostUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Post:
    post = _get_owned_post(db, user, post_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    post = _get_owned_post(db, user, post_id)
    db.delete(post)
    db.commit()


@router.post("/{post_id}/schedule", response_model=PostRead)
def schedule_post(
    post_id: UUID, scheduled_at: datetime, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Post:
    post = _get_owned_post(db, user, post_id)
    post.scheduled_at = scheduled_at if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=timezone.utc)
    post.status = PostStatus.SCHEDULED
    db.commit()
    db.refresh(post)
    return post
