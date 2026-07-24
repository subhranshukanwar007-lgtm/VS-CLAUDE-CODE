from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.lead import Lead
from app.models.notification import NotificationType
from app.models.user import User, UserRole
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
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


@router.get("", response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Lead]:
    return list(db.scalars(_visible_query(user).order_by(Lead.created_at.desc())))


@router.post("", response_model=LeadRead, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Lead:
    lead = Lead(owner_id=user.id, **payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    notify(db, user.id, NotificationType.LEAD_CREATED, title=f"New lead: {lead.full_name}", link=f"/crm/leads/{lead.id}")
    return lead


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Lead:
    return _get_owned_lead(db, user, lead_id)


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: UUID, payload: LeadUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Lead:
    lead = _get_owned_lead(db, user, lead_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    lead = _get_owned_lead(db, user, lead_id)
    db.delete(lead)
    db.commit()
