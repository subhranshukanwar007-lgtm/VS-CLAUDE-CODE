from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.user import UserRead, UserRoleUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at)))


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserRead)
def update_role(
    user_id: UUID, payload: UserRoleUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundError("User")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target
