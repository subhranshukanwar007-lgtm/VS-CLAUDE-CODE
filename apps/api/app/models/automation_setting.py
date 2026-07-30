"""Per-user automation configuration, editable from the Settings UI.

Everything here is deliberately runtime-editable rather than an environment
variable, because these are the knobs a user wants to turn day to day: whether a
platform auto-publishes, what the auto-DM says, which keywords trigger it.
Secrets (API keys) stay in the environment — see app/config.py.

One row per user, created lazily on first read (see
app/services/automation_settings_service.py) so existing users don't need a
backfill.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ReplyLanguage(StrEnum):
    """Language and script the AI writes replies, DMs and answers in.

    HINGLISH is Hindi written in Roman/Latin script ("bhai ye kaise karna hai") —
    the way most Indian users actually type on Instagram and Threads. It is a
    distinct option from HINDI (Devanagari script) because the audience that reads
    one often won't read the other.
    """

    ENGLISH = "english"
    HINGLISH = "hinglish"
    HINDI = "hindi"


# Instruction appended to every AI prompt that produces user-facing copy.
LANGUAGE_INSTRUCTIONS: dict[ReplyLanguage, str] = {
    ReplyLanguage.ENGLISH: "Write in natural, conversational English.",
    ReplyLanguage.HINGLISH: (
        "Write in Hinglish: Hindi mixed with English, written entirely in Roman "
        "(Latin) script. Never use Devanagari characters. Keep it casual and "
        "friendly, the way people actually text on Instagram — for example "
        "'bhai ye bahut easy hai, main batata hoon'."
    ),
    ReplyLanguage.HINDI: "Write in Hindi using Devanagari script.",
}

DEFAULT_DM_TEMPLATE = (
    "Hey {name}! Thanks for commenting \U0001f64f\n\n"
    "Here's the free guide I mentioned: {link}\n\n"
    "Reply here if you have any questions — happy to help."
)


class AutomationSetting(BaseModel):
    __tablename__ = "automation_settings"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    # --- Publishing ---
    # Per-platform auto-publish. Absent platform == False == require approval.
    # Kept as JSONB rather than a column per platform so adding a platform to the
    # Platform enum needs no migration here.
    auto_publish: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # --- Instagram comment -> DM (Meta "private replies") ---
    dm_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dm_trigger_keywords: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="Comma-separated. Empty means reply to every comment."
    )
    dm_template: Mapped[str] = mapped_column(Text, default=DEFAULT_DM_TEMPLATE, nullable=False)
    dm_link: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="Substituted into {link}")

    # --- Threads keyword monitoring ---
    threads_monitor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    threads_keywords: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="Comma-separated keywords to search public Threads posts for"
    )
    threads_max_per_day: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # --- Content cadence ---
    posts_per_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # --- Voice ---
    # Applies to every AI-written reply: DMs, question answers, lead follow-ups.
    reply_language: Mapped[ReplyLanguage] = mapped_column(
        Enum(ReplyLanguage, name="reply_language"), default=ReplyLanguage.ENGLISH, nullable=False
    )
