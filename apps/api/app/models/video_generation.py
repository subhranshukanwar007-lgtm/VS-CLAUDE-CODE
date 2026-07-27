import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class VideoProviderKind(StrEnum):
    REPLICATE = "replicate"
    HIGGSFIELD = "higgsfield"


class VideoGenerationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class VideoGeneration(BaseModel):
    """One AI video generation job: prompt in, provider/model that ran it, and
    (once it finishes) the resulting video URL. `post_id` is set once the video
    has been attached to a content-calendar Post, closing the generate-to-post
    loop."""

    __tablename__ = "video_generations"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    post_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)

    provider: Mapped[VideoProviderKind] = mapped_column(
        Enum(VideoProviderKind, name="video_provider"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(String(4000), nullable=False)
    extra_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    external_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[VideoGenerationStatus] = mapped_column(
        Enum(VideoGenerationStatus, name="video_generation_status"), default=VideoGenerationStatus.PENDING
    )
    video_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
