from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.deal import Deal, DealStatus
from app.models.lead import Lead
from app.models.notification import NotificationType
from app.models.user import User, UserRole
from app.schemas.deal import DealCreate, DealRead, DealUpdate
from app.services.notification_service import notify

router = APIRouter(prefix="/deals", tags=["crm"])

_PRIVILEGED = {UserRole.OWNER, UserRole.ADMIN}


def _get_owned_deal(db: Session, user: User, deal_id: UUID) -> Deal:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise NotFoundError("Deal")
    if user.role not in _PRIVILEGED and deal.lead.owner_id != user.id:
        raise ForbiddenError()
    return deal


@router.get("", response_model=list[DealRead])
def list_deals(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Deal]:
    query = select(Deal).join(Lead, Deal.lead_id == Lead.id)
    if user.role not in _PRIVILEGED:
        query = query.where(Lead.owner_id == user.id)
    return list(db.scalars(query.order_by(Deal.created_at.desc())))


@router.post("", response_model=DealRead, status_code=201)
def create_deal(payload: DealCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Deal:
    lead = db.get(Lead, payload.lead_id)
    if lead is None:
        raise NotFoundError("Lead")
    if user.role not in _PRIVILEGED and lead.owner_id != user.id:
        raise ForbiddenError()

    deal = Deal(**payload.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.patch("/{deal_id}", response_model=DealRead)
def update_deal(
    deal_id: UUID, payload: DealUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Deal:
    deal = _get_owned_deal(db, user, deal_id)
    was_won = deal.status == DealStatus.WON
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    db.commit()
    db.refresh(deal)

    if deal.status == DealStatus.WON and not was_won:
        notify(db, deal.lead.owner_id, NotificationType.DEAL_WON, title=f"Deal won: {deal.title}", link="/crm/pipeline")

    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(deal_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    deal = _get_owned_deal(db, user, deal_id)
    db.delete(deal)
    db.commit()
