import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.post import Platform


class SocialAccount(BaseModel):
    """Connected social platform account. OAuth token exchange for each platform is
    an integration-specific extension point — see app/integrations/base.py."""

    __tablename__ = "social_accounts"

    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="social_account_platform"), nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
