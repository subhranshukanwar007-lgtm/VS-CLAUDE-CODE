from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.post import Platform, PostFormat
from app.models.video_generation import VideoGenerationStatus, VideoProviderKind


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    provider: VideoProviderKind | None = Field(default=None, description="Defaults to DEFAULT_VIDEO_PROVIDER")
    model: str | None = Field(
        default=None,
        description="Model/model_id for the chosen provider (Replicate 'owner/name' slug, or a Higgsfield "
        "model_id like 'higgsfield-ai/soul/standard'); defaults to that provider's configured default.",
    )
    extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Passed straight through alongside `prompt` into the provider's request body "
        "(e.g. {'image': 'https://...'} for image-to-video, reference face/voice IDs for Higgsfield, "
        "or a model-specific duration/aspect_ratio).",
    )


class VideoGenerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: VideoProviderKind
    model: str
    prompt: str
    status: VideoGenerationStatus
    video_url: str | None
    thumbnail_url: str | None
    error: str | None
    post_id: UUID | None
    created_at: datetime


class AttachToPostRequest(BaseModel):
    platform: Platform
    format: PostFormat = PostFormat.REEL
    caption: str | None = Field(default=None, max_length=4000)
    hashtags: str | None = Field(default=None, max_length=1000)
    scheduled_at: datetime | None = None
