from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.database import get_db
from app.models.user import User, UserRole
from app.security import InvalidTokenError, TokenType, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise UnauthorizedError("Not authenticated")
    try:
        payload = decode_token(token, TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise UnauthorizedError() from exc

    user_id = UUID(payload["sub"])
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Dependency factory for RBAC: usage `Depends(require_roles(UserRole.ADMIN))`."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(f"Requires one of roles: {', '.join(r.value for r in allowed_roles)}")
        return user

    return dependency


require_admin = require_roles(UserRole.OWNER, UserRole.ADMIN)
