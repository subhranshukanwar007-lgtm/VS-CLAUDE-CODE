from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.content_idea import ContentIdea
from app.models.user import User
from app.schemas.idea import ContentIdeaCreate, ContentIdeaRead, ContentIdeaUpdate, TodaysIdea
from app.services.idea_service import ensure_seeded, format_for, get_todays_idea, mark_used

router = APIRouter(prefix="/content-ideas", tags=["content-ideas"])


def _owned(db: Session, user: User, idea_id: UUID) -> ContentIdea:
    idea = db.get(ContentIdea, idea_id)
    if idea is None:
        raise NotFoundError("Content idea")
    if idea.owner_id != user.id:
        raise ForbiddenError()
    return idea


@router.get("/today", response_model=TodaysIdea)
def todays_idea(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TodaysIdea:
    """What to make today. Stable for the whole day, so refreshing doesn't
    reshuffle the plan."""

    return get_todays_idea(db, user)


@router.get("", response_model=list[ContentIdeaRead])
def list_ideas(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ContentIdea]:
    ensure_seeded(db, user.id)
    return list(
        db.scalars(
            select(ContentIdea)
            .where(ContentIdea.owner_id == user.id)
            .order_by(ContentIdea.is_active.desc(), ContentIdea.times_used, ContentIdea.created_at)
        )
    )


@router.post("", response_model=ContentIdeaRead, status_code=201)
def create_idea(
    payload: ContentIdeaCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ContentIdea:
    data = payload.model_dump()
    if data.get("suggested_format") is None:
        data["suggested_format"] = format_for(data["suggested_goal"])
    idea = ContentIdea(owner_id=user.id, **data)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@router.patch("/{idea_id}", response_model=ContentIdeaRead)
def update_idea(
    idea_id: UUID, payload: ContentIdeaUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ContentIdea:
    idea = _owned(db, user, idea_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(idea, field, value)
    db.commit()
    db.refresh(idea)
    return idea


@router.post("/{idea_id}/used", response_model=ContentIdeaRead)
def mark_idea_used(
    idea_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ContentIdea:
    """Called once a video has actually been made from this idea, so it drops to
    the back of the rotation instead of being suggested again tomorrow."""

    return mark_used(db, _owned(db, user, idea_id))


@router.delete("/{idea_id}", status_code=204)
def delete_idea(idea_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    db.delete(_owned(db, user, idea_id))
    db.commit()
