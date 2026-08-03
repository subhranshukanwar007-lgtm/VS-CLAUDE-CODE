import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.integrations.registry import has_real_publisher
from app.models.automation_setting import AutomationSetting
from app.models.post import Platform
from app.models.private_reply import PrivateReply, PrivateReplyStatus
from app.models.user import User
from app.schemas.automation import (
    AutomationSettingRead,
    AutomationSettingUpdate,
    DMPreviewRequest,
    DMPreviewResponse,
    DMQueueSummary,
    PlatformCapability,
    PrivateReplyRead,
)
from app.services.automation_settings_service import get_or_create
from app.services.dm_service import matches_trigger, render_message

router = APIRouter(prefix="/automation", tags=["automation"])

# Stories are only publishable where the platform's API actually supports them:
# Instagram (media_type=STORIES) and Facebook Pages (/photo_stories, /video_stories).
# Threads has no Stories at all.
_STORY_PLATFORMS = {Platform.INSTAGRAM, Platform.FACEBOOK}

_PLATFORM_NOTES: dict[Platform, str] = {
    Platform.THREADS: "Threads has no Stories and no DM API. Text posts cap at 500 characters.",
    Platform.X: (
        "Not wired up: X removed its free API tier for new developers on 2026-02-06. "
        "Posting now costs roughly $0.015 per post, or $0.20 with a link."
    ),
    Platform.YOUTUBE: "Not wired up yet — needs YouTube Data API OAuth.",
    Platform.LINKEDIN: "Not wired up yet — needs LinkedIn Marketing API access.",
    Platform.TIKTOK: "Not wired up yet — needs TikTok Content Posting API approval.",
    Platform.PINTEREST: "Not wired up yet — needs Pinterest API access.",
}


@router.get("/settings", response_model=AutomationSettingRead)
def read_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AutomationSetting:
    return get_or_create(db, user.id)


@router.patch("/settings", response_model=AutomationSettingRead)
def update_settings(
    payload: AutomationSettingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AutomationSetting:
    setting = get_or_create(db, user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)
    db.commit()
    db.refresh(setting)
    return setting


@router.post("/dm-preview", response_model=DMPreviewResponse)
def preview_dm(
    payload: DMPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DMPreviewResponse:
    """Dry-run the auto-DM against a comment you type in. Sends nothing.

    Exists because Meta allows exactly one private reply per comment: there is no
    way to test this on a real comment and then fix the wording. You get one
    shot, so the rehearsal has to happen somewhere safe.
    """

    setting = get_or_create(db, user.id)
    keywords = [kw.strip().lower() for kw in (setting.dm_trigger_keywords or "").split(",") if kw.strip()]

    if not setting.dm_enabled:
        return DMPreviewResponse(
            would_send=False,
            reason="Auto-DM is switched off, so nothing would be sent.",
            message=None,
        )
    if not matches_trigger(payload.comment, keywords):
        return DMPreviewResponse(
            would_send=False,
            reason=(
                "This comment matches none of your trigger keywords "
                f"({', '.join(keywords)}), so it would be left alone."
            ),
            message=None,
        )

    message = render_message(setting, payload.username)
    if not message:
        return DMPreviewResponse(
            would_send=False,
            reason="Your DM template is empty, so there is nothing to send.",
            message=None,
        )
    reason = (
        "Matched. This exact message would be sent as a private reply."
        if keywords
        else "No keywords set, so every comment gets this reply."
    )
    return DMPreviewResponse(would_send=True, reason=reason, message=message)


@router.get("/dm-queue", response_model=list[PrivateReplyRead])
def read_dm_queue(
    status: PrivateReplyStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PrivateReply]:
    query = select(PrivateReply).where(PrivateReply.owner_id == user.id)
    if status is not None:
        query = query.where(PrivateReply.status == status)
    return list(db.scalars(query.order_by(PrivateReply.created_at.desc()).limit(limit)))


@router.get("/dm-queue/summary", response_model=DMQueueSummary)
def read_dm_queue_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DMQueueSummary:
    rows = db.execute(
        select(PrivateReply.status, func.count())
        .where(PrivateReply.owner_id == user.id)
        .group_by(PrivateReply.status)
    ).all()
    counts = {status.value: 0 for status in PrivateReplyStatus}
    for status, count in rows:
        counts[status.value] = count
    return DMQueueSummary(**counts)


@router.post("/dm-queue/{reply_id}/retry", response_model=PrivateReplyRead)
def retry_dm(
    reply_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PrivateReply:
    """Put a failed DM back in the queue.

    Only FAILED rows can be retried. A SENT row is never retried, because Meta
    permits one private reply per comment and a second attempt would fail anyway
    — worse, it would look to the user like the DM was sent twice.
    """

    row = db.scalar(
        select(PrivateReply).where(PrivateReply.id == reply_id, PrivateReply.owner_id == user.id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="DM not found")
    if row.status is not PrivateReplyStatus.FAILED:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Only failed DMs can be retried; this one is {row.status.value}. "
                "Meta allows one private reply per comment, so a sent DM cannot be resent."
            ),
        )
    row.status = PrivateReplyStatus.PENDING
    row.error = None
    db.commit()
    db.refresh(row)
    return row


@router.get("/capabilities", response_model=list[PlatformCapability])
def read_capabilities() -> list[PlatformCapability]:
    """What this app can genuinely do per platform. The Settings UI reads this so
    it only offers an auto-publish toggle where publishing actually works."""

    return [
        PlatformCapability(
            platform=platform,
            can_publish=has_real_publisher(platform),
            supports_stories=platform in _STORY_PLATFORMS,
            note=_PLATFORM_NOTES.get(platform),
        )
        for platform in Platform
    ]
