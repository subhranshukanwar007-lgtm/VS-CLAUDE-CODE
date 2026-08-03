from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.database import get_db
from app.deps import get_current_user
from app.models.post import Post
from app.models.user import User
from app.models.video_generation import VideoGeneration
from app.schemas.post import PostRead
from app.schemas.script import ContentPackage, ContentPackageRequest
from app.schemas.video import AttachToPostRequest, VideoGenerateRequest, VideoGenerationRead
from app.services import video_service
from app.services.ai.base import AIProviderError
from app.services.script_service import generate_content_package
from app.services.video.base import VideoProviderError

router = APIRouter(prefix="/video", tags=["video"])


def _get_owned_generation(db: Session, user: User, generation_id: UUID) -> VideoGeneration:
    generation = db.get(VideoGeneration, generation_id)
    if generation is None or generation.user_id != user.id:
        raise NotFoundError("Video generation")
    return generation


@router.post("/script-package", response_model=ContentPackage)
async def create_content_package(
    payload: ContentPackageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContentPackage:
    """One topic in, a shoot-ready package out: hook options, a timed script, the
    prompt to paste into Higgsfield alongside your own avatar and voice, per-beat
    B-roll directions, and on-screen captions in your chosen script."""

    try:
        return await generate_content_package(db, user, payload)
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.post("/generate", response_model=VideoGenerationRead, status_code=201)
async def generate_video(
    payload: VideoGenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> VideoGeneration:
    try:
        return await video_service.start_generation(
            db, user, payload.prompt, payload.model, payload.extra_params, payload.provider
        )
    except VideoProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.get("", response_model=list[VideoGenerationRead])
def list_generations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[VideoGeneration]:
    return list(
        db.scalars(
            select(VideoGeneration).where(VideoGeneration.user_id == user.id).order_by(VideoGeneration.created_at.desc())
        )
    )


@router.get("/{generation_id}", response_model=VideoGenerationRead)
async def get_generation(
    generation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> VideoGeneration:
    generation = _get_owned_generation(db, user, generation_id)
    try:
        return await video_service.poll_generation(db, generation)
    except VideoProviderError:
        # Surface the last known state rather than failing the request if a
        # single poll attempt errors — the beat task will retry it shortly.
        return generation


@router.post("/{generation_id}/attach-to-post", response_model=PostRead, status_code=201)
def attach_to_post(
    generation_id: UUID,
    payload: AttachToPostRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Post:
    generation = _get_owned_generation(db, user, generation_id)
    try:
        post = video_service.attach_to_post(
            db,
            user,
            generation,
            platform=payload.platform,
            format=payload.format,
            caption=payload.caption,
            hashtags=payload.hashtags,
            scheduled_at=payload.scheduled_at,
        )
    except video_service.VideoNotReadyError as exc:
        raise ConflictError(str(exc)) from exc
    return post


@router.post("/{generation_id}/thumbnail", response_model=VideoGenerationRead)
async def generate_thumbnail(
    generation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> VideoGeneration:
    generation = _get_owned_generation(db, user, generation_id)
    try:
        return await video_service.generate_thumbnail(db, generation)
    except VideoProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
