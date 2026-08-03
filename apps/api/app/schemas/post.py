from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.post import Platform, PostFormat, PostGoal, PostStatus


class PostCreate(BaseModel):
    platform: Platform
    format: PostFormat = PostFormat.POST
    caption: str | None = Field(default=None, max_length=4000)
    hashtags: str | None = Field(default=None, max_length=1000)
    media_url: str | None = None
    scheduled_at: datetime | None = None
    status: PostStatus = PostStatus.DRAFT
    goal: PostGoal = PostGoal.REACH


class PostUpdate(BaseModel):
    platform: Platform | None = None
    format: PostFormat | None = None
    caption: str | None = None
    hashtags: str | None = None
    media_url: str | None = None
    scheduled_at: datetime | None = None
    status: PostStatus | None = None
    goal: PostGoal | None = None
    external_post_id: str | None = Field(default=None, max_length=255)
    """Settable so a post published outside this app can still be linked to the
    platform post it became — that link is what lets engagement capture attribute
    incoming leads to it."""


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    platform: Platform
    format: PostFormat
    caption: str | None
    hashtags: str | None
    media_url: str | None
    status: PostStatus
    goal: PostGoal
    scheduled_at: datetime | None
    published_at: datetime | None
    failure_reason: str | None
    external_post_id: str | None
