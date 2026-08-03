from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.automation_setting import ReplyLanguage
from app.models.post import Platform
from app.models.private_reply import PrivateReplyStatus


class AutomationSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    auto_publish: dict[str, bool]
    dm_enabled: bool
    dm_trigger_keywords: str | None
    dm_template: str
    dm_link: str | None
    whatsapp_ai_enabled: bool
    threads_monitor_enabled: bool
    threads_keywords: str | None
    threads_max_per_day: int
    posts_per_day: int
    follower_goal: int | None
    goal_deadline: date | None
    reels_per_week_target: int
    reply_language: ReplyLanguage


class AutomationSettingUpdate(BaseModel):
    auto_publish: dict[str, bool] | None = None
    dm_enabled: bool | None = None
    dm_trigger_keywords: str | None = Field(default=None, max_length=1000)
    dm_template: str | None = Field(default=None, min_length=1, max_length=4000)
    dm_link: str | None = Field(default=None, max_length=1024)
    whatsapp_ai_enabled: bool | None = None
    threads_monitor_enabled: bool | None = None
    threads_keywords: str | None = Field(default=None, max_length=1000)
    threads_max_per_day: int | None = Field(default=None, ge=0, le=200)
    posts_per_day: int | None = Field(default=None, ge=0, le=50)
    follower_goal: int | None = Field(default=None, ge=0, le=1_000_000_000)
    goal_deadline: date | None = None
    reels_per_week_target: int | None = Field(default=None, ge=0, le=100)
    reply_language: ReplyLanguage | None = None

    @field_validator("auto_publish")
    @classmethod
    def validate_platforms(cls, value: dict[str, bool] | None) -> dict[str, bool] | None:
        """Reject unknown platform keys rather than silently storing a typo that
        would then never match a real platform at publish time."""

        if value is None:
            return value
        valid = {p.value for p in Platform}
        unknown = set(value) - valid
        if unknown:
            raise ValueError(f"unknown platform(s): {', '.join(sorted(unknown))}")
        return value


class PrivateReplyRead(BaseModel):
    """One row of the auto-DM queue, as the Settings screen shows it.

    ``message`` is included deliberately: when a DM goes wrong the user's first
    question is "what did it actually say to them?", and the stored copy is the
    only honest answer once the template has been edited.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    platform: Platform
    comment_id: str
    recipient_username: str | None
    message: str
    status: PrivateReplyStatus
    error: str | None
    sent_at: datetime | None
    created_at: datetime


class DMPreviewRequest(BaseModel):
    """Dry-run one comment against the current settings. Sends nothing."""

    comment: str = Field(min_length=1, max_length=2200)
    username: str = Field(default="there", max_length=255)


class DMPreviewResponse(BaseModel):
    would_send: bool
    reason: str
    message: str | None


class DMQueueSummary(BaseModel):
    pending: int
    sent: int
    failed: int
    skipped: int


class PlatformCapability(BaseModel):
    """What the app can actually do per platform, so the UI can grey out promises
    it cannot keep instead of offering a toggle that does nothing."""

    platform: Platform
    can_publish: bool
    supports_stories: bool
    note: str | None = None
