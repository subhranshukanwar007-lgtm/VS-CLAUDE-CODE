from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.social_account import SocialAccount
from app.models.user import User
from app.schemas.social_account import SocialAccountCreate, SocialAccountRead

router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])


@router.get("", response_model=list[SocialAccountRead])
def list_social_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SocialAccount]:
    return list(db.scalars(select(SocialAccount).where(SocialAccount.owner_id == user.id)))


@router.post("", response_model=SocialAccountRead, status_code=201)
def create_social_account(
    payload: SocialAccountCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SocialAccount:
    account = SocialAccount(owner_id=user.id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_social_account(account_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    account = db.get(SocialAccount, account_id)
    if account is None:
        raise NotFoundError("Social account")
    if account.owner_id != user.id:
        raise ForbiddenError()
    db.delete(account)
    db.commit()
