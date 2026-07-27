import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.notification import NotificationType
from app.models.post import Platform, Post, PostFormat, PostStatus
from app.models.user import User
from app.models.video_generation import VideoGeneration, VideoGenerationStatus, VideoProviderKind
from app.services.notification_service import notify
from app.services.video.base import VideoProviderError
from app.services.video.factory import get_video_provider

logger = logging.getLogger("video")

_IN_FLIGHT_STATUSES = (VideoGenerationStatus.PENDING, VideoGenerationStatus.PROCESSING)


class VideoNotReadyError(Exception):
    """Raised when attaching a video to a post is attempted before generation
    has succeeded."""


async def start_generation(
    db: Session,
    user: User,
    prompt: str,
    model: str | None = None,
    extra_params: dict[str, Any] | None = None,
    provider_kind: VideoProviderKind | None = None,
) -> VideoGeneration:
    resolved_model = model or settings.replicate_video_model
    provider = get_video_provider(provider_kind)

    job_id = await provider.submit(prompt, resolved_model, extra_params or {})

    generation = VideoGeneration(
        user_id=user.id,
        provider=VideoProviderKind(provider.name),
        model=resolved_model,
        prompt=prompt,
        extra_params=extra_params or {},
        external_job_id=job_id,
        status=VideoGenerationStatus.PROCESSING,
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


async def poll_generation(db: Session, generation: VideoGeneration) -> VideoGeneration:
    """Check one generation's current status with its provider and persist any
    change. Idempotent: no-ops once the job has reached a terminal state."""

    if generation.status not in _IN_FLIGHT_STATUSES:
        return generation

    provider = get_video_provider(generation.provider)
    result = await provider.poll(generation.external_job_id)

    if result.status == generation.status and result.video_url == generation.video_url:
        return generation

    generation.status = result.status
    generation.video_url = result.video_url
    generation.error = result.error
    db.commit()
    db.refresh(generation)

    if result.status == VideoGenerationStatus.SUCCEEDED:
        notify(
            db,
            generation.user_id,
            NotificationType.VIDEO_READY,
            title="Your AI-generated video is ready",
            body=generation.prompt[:200],
            link=f"/video?generation={generation.id}",
        )
    elif result.status == VideoGenerationStatus.FAILED:
        notify(
            db,
            generation.user_id,
            NotificationType.VIDEO_FAILED,
            title="Video generation failed",
            body=result.error or "Unknown error",
            link=f"/video?generation={generation.id}",
        )

    return generation


async def poll_all_pending(db: Session) -> int:
    """Entry point for the Celery beat task: polls every in-flight generation
    across all users. Provider errors on one job are logged and skipped so a
    single bad job can't block the rest of the batch."""

    generations = db.scalars(select(VideoGeneration).where(VideoGeneration.status.in_(_IN_FLIGHT_STATUSES))).all()
    updated = 0
    for generation in generations:
        try:
            before = generation.status
            after = await poll_generation(db, generation)
            if after.status != before:
                updated += 1
        except VideoProviderError as exc:
            logger.warning("failed to poll video generation %s: %s", generation.id, exc)
    return updated


def attach_to_post(
    db: Session,
    user: User,
    generation: VideoGeneration,
    platform: Platform,
    format: PostFormat = PostFormat.REEL,
    caption: str | None = None,
    hashtags: str | None = None,
    scheduled_at=None,
) -> Post:
    if generation.status != VideoGenerationStatus.SUCCEEDED or not generation.video_url:
        raise VideoNotReadyError("This video hasn't finished generating yet")

    post = Post(
        author_id=user.id,
        platform=platform,
        format=format,
        caption=caption,
        hashtags=hashtags,
        media_url=generation.video_url,
        status=PostStatus.SCHEDULED if scheduled_at else PostStatus.DRAFT,
        scheduled_at=scheduled_at,
    )
    db.add(post)
    db.flush()
    generation.post_id = post.id
    db.commit()
    db.refresh(post)
    return post
