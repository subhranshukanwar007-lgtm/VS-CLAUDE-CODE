from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.post import Platform, PostFormat
from app.models.video_generation import VideoGenerationStatus, VideoProviderKind


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str | None = Field(
        default=None, description="Replicate 'owner/name' slug; defaults to REPLICATE_VIDEO_MODEL"
    )
    extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Passed straight through into the model's input alongside `prompt` "
        "(e.g. {'image': 'https://...'} for image-to-video, or a model-specific duration/aspect_ratio).",
    )


class VideoGenerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: VideoProviderKind
    model: str
    prompt: str
    status: VideoGenerationStatus
    video_url: str | None
    error: str | None
    post_id: UUID | None
    created_at: datetime


class AttachToPostRequest(BaseModel):
    platform: Platform
    format: PostFormat = PostFormat.REEL
    caption: str | None = Field(default=None, max_length=4000)
    hashtags: str | None = Field(default=None, max_length=1000)
    scheduled_at: datetime | None = None
