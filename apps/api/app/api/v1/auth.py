from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserRead
from app.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.auth_service import verify_google_id_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    is_first_user = db.scalar(select(User.id).limit(1)) is None
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.OWNER if is_first_user else UserRole.MEMBER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(tokens=_tokens_for(user), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or user.hashed_password is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")

    return AuthResponse(tokens=_tokens_for(user), user=UserRead.model_validate(user))


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    profile = await verify_google_id_token(payload.id_token)

    user = db.scalar(select(User).where(User.google_sub == profile.sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == profile.email))

    if user is None:
        is_first_user = db.scalar(select(User.id).limit(1)) is None
        user = User(
            email=profile.email,
            full_name=profile.name,
            google_sub=profile.sub,
            avatar_url=profile.picture,
            role=UserRole.OWNER if is_first_user else UserRole.MEMBER,
        )
        db.add(user)
    elif user.google_sub is None:
        user.google_sub = profile.sub

    db.commit()
    db.refresh(user)

    return AuthResponse(tokens=_tokens_for(user), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired refresh token") from exc

    user = db.get(User, UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return _tokens_for(user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
