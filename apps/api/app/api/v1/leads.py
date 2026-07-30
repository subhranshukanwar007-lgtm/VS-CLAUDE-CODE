from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ServiceUnavailableError
from app.database import get_db
from app.deps import get_current_user
from app.models.lead import Lead, LeadSource
from app.models.notification import NotificationType
from app.models.user import User, UserRole
from app.schemas.ai import AIGenerationResult
from app.schemas.lead import FollowUpResult, LeadCreate, LeadRead, LeadUpdate
from app.schemas.task import TaskRead
from app.services.ai.base import AIProviderError
from app.services.followup_service import is_lead_stale, trigger_follow_up
from app.services.notification_service import notify

router = APIRouter(prefix="/leads", tags=["crm"])

_PRIVILEGED = {UserRole.OWNER, UserRole.ADMIN}


def _visible_query(user: User):
    query = select(Lead)
    if user.role not in _PRIVILEGED:
        query = query.where(Lead.owner_id == user.id)
    return query


def _get_owned_lead(db: Session, user: User, lead_id: UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead")
    if user.role not in _PRIVILEGED and lead.owner_id != user.id:
        raise ForbiddenError()
    return lead


def _to_read(db: Session, lead: Lead) -> LeadRead:
    return LeadRead.model_validate(lead).model_copy(update={"is_stale": is_lead_stale(db, lead)})


@router.get("", response_model=list[LeadRead])
def list_leads(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    country: str | None = Query(default=None, min_length=2, max_length=2, description="ISO alpha-2, e.g. US"),
    source: LeadSource | None = None,
) -> list[LeadRead]:
    query = _visible_query(user)
    if country is not None:
        query = query.where(Lead.country == country.upper())
    if source is not None:
        query = query.where(Lead.source == source)
    leads = db.scalars(query.order_by(Lead.created_at.desc())).all()
    return [_to_read(db, lead) for lead in leads]


@router.post("", response_model=LeadRead, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LeadRead:
    lead = Lead(owner_id=user.id, **payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    notify(db, user.id, NotificationType.LEAD_CREATED, title=f"New lead: {lead.full_name}", link=f"/crm/leads/{lead.id}")
    return _to_read(db, lead)


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LeadRead:
    return _to_read(db, _get_owned_lead(db, user, lead_id))


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: UUID, payload: LeadUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LeadRead:
    lead = _get_owned_lead(db, user, lead_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return _to_read(db, lead)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    lead = _get_owned_lead(db, user, lead_id)
    db.delete(lead)
    db.commit()


@router.post("/{lead_id}/follow-up", response_model=FollowUpResult)
async def suggest_follow_up(
    lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> FollowUpResult:
    """Manually generate an AI follow-up draft for a lead right now, regardless of
    the automatic staleness threshold — creates a reminder task and notification
    the same way the daily automation does."""

    lead = _get_owned_lead(db, user, lead_id)
    try:
        generation, task = await trigger_follow_up(db, user, lead)
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc

    return FollowUpResult(
        generation=AIGenerationResult(
            id=generation.id, provider=generation.provider, model=generation.model, result=generation.result
        ),
        task=TaskRead.model_validate(task),
    )
