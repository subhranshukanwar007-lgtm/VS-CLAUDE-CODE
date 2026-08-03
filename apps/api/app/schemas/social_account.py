from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.post import Platform


class SocialAccountCreate(BaseModel):
    platform: Platform
    handle: str = Field(min_length=1, max_length=255)
    external_account_id: str | None = Field(
        default=None,
        description="The platform's business/account ID for this handle — required for incoming webhook "
        "events (e.g. comment capture) to route to you. Find it in your Meta Business Suite / API dashboard.",
    )


class SocialAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: Platform
    handle: str
    external_account_id: str | None
    is_active: bool
