import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Platform(StrEnum):
    """Extension point: add a new social platform here, then implement a matching
    Publisher in app/integrations/ (see app/integrations/base.py)."""

    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    PINTEREST = "pinterest"
    TIKTOK = "tiktok"
    X = "x"


class PostFormat(StrEnum):
    REEL = "reel"
    POST = "post"
    STORY = "story"
    CAROUSEL = "carousel"
    VIDEO = "video"


class PostGoal(StrEnum):
    """What a post is *for*. Without this, "which of my content actually produces
    leads" is unanswerable — you can only see views, which is not the same thing.

    The format each goal favours is encoded in RECOMMENDED_FORMATS below.
    """

    REACH = "reach"
    LEADS = "leads"
    SALES = "sales"
    TRUST = "trust"
    SAVES = "saves"


# Which format each goal is usually best served by, and why. Advisory only: the
# app suggests, it never overrides what the user picked.
RECOMMENDED_FORMATS: dict[PostGoal, tuple[PostFormat, str]] = {
    PostGoal.REACH: (PostFormat.REEL, "Reels are pushed to people who don't follow you yet."),
    PostGoal.LEADS: (PostFormat.STORY, "Stories reach people who already follow you, daily, with a direct reply box."),
    PostGoal.SALES: (PostFormat.REEL, "Lead with the problem, then the solution — don't open with the offer."),
    PostGoal.TRUST: (PostFormat.POST, "Personal, behind-the-scenes content is what makes people believe you."),
    PostGoal.SAVES: (PostFormat.CAROUSEL, "Carousels get saved because people come back to them."),
}


class PostStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class Post(BaseModel):
    __tablename__ = "posts"

    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="post_platform"), nullable=False)
    format: Mapped[PostFormat] = mapped_column(Enum(PostFormat, name="post_format"), default=PostFormat.POST)
    caption: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    hashtags: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus, name="post_status"), default=PostStatus.DRAFT)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    external_post_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="The platform's own id for the published post. Indexed because engagement capture looks leads up by it.",
    )
    goal: Mapped[PostGoal] = mapped_column(
        Enum(PostGoal, name="post_goal"), default=PostGoal.REACH, nullable=False, index=True
    )

    author: Mapped["User"] = relationship(back_populates="posts")  # noqa: F821
