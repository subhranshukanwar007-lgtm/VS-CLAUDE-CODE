from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.integrations.registry import has_real_publisher
from app.models.automation_setting import AutomationSetting
from app.models.post import Platform
from app.models.user import User
from app.schemas.automation import (
    AutomationSettingRead,
    AutomationSettingUpdate,
    PlatformCapability,
)
from app.services.automation_settings_service import get_or_create

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
