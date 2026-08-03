"""Comment -> auto-DM: catching someone at the second they raise their hand.

The flow, split deliberately across two moments:

1. **At webhook time** (synchronous, no network): decide whether this comment
   should get a DM, render the message, and write a ``PrivateReply`` row. Meta
   retries webhooks it thinks failed, so the endpoint must answer fast — and the
   row's unique constraint on ``comment_id`` is what makes a redelivery harmless.
2. **From Celery** (``send_pending``): actually call Meta. A failure here leaves a
   FAILED row carrying Meta's own words, which the user can see and act on.

Why every comment gets a row, including ones we will not DM: a SKIPPED row is a
decision on the record. Without it, a redelivered webhook after the user flips
``dm_enabled`` on would DM someone who commented days ago, which reads as spam.
"""

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.meta_dm import PrivateReplyError, send_private_reply
from app.models.automation_setting import AutomationSetting
from app.models.lead import Lead
from app.models.notification import NotificationType
from app.models.post import Platform
from app.models.private_reply import (
    PRIVATE_REPLY_WINDOW_DAYS,
    PrivateReply,
    PrivateReplyStatus,
)
from app.models.social_account import SocialAccount
from app.services.automation_settings_service import dm_trigger_keywords, get_or_create
from app.services.notification_service import notify

logger = logging.getLogger("dm")

# Only these two surfaces have a private reply API at all.
DM_CAPABLE_PLATFORMS = {Platform.INSTAGRAM, Platform.FACEBOOK}

# Instagram DMs are capped well below this, but a template with a runaway
# substitution should fail visibly at our boundary rather than at Meta's.
MAX_MESSAGE_LENGTH = 1000


def matches_trigger(text: str, keywords: list[str]) -> bool:
    """Does this comment ask for the thing?

    An empty keyword list means "DM everyone who comments" — that is a real
    choice some creators make, so it is honoured rather than treated as "off"
    (``dm_enabled`` is the off switch).

    Matching is word-boundary based with an optional trailing ``s``, so the
    keyword *plan* catches "PLAN" and "plans" but not "planet" and not the
    "plan" inside "explanation". Substring matching was the obvious first
    implementation and it fires on comments that were never asking for anything.
    """

    if not keywords:
        return True
    for keyword in keywords:
        pattern = rf"\b{re.escape(keyword)}s?\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def render_message(setting: AutomationSetting, name: str) -> str:
    """Fills ``{name}`` and ``{link}`` in the user's template.

    Uses explicit replacement rather than ``str.format`` because the template is
    user-written: a stray brace in "50% off {today}" would raise KeyError and kill
    the DM. Unknown placeholders are left visible instead — the user sees the
    literal ``{today}`` in their own test DM and fixes the template.
    """

    message = setting.dm_template or ""
    message = message.replace("{name}", name or "there")
    message = message.replace("{link}", setting.dm_link or "")
    return message.strip()[:MAX_MESSAGE_LENGTH]


def queue_private_reply(
    db: Session,
    account: SocialAccount,
    comment: dict[str, Any],
    lead: Lead | None,
) -> PrivateReply | None:
    """Records the decision for one comment. Returns the row, or None if this
    comment was already decided (a redelivery) or cannot be replied to at all.

    Commits on its own so a duplicate-key rollback can never take the caller's
    freshly-created lead down with it — lead capture matters more than the DM.
    """

    comment_id = comment.get("id")
    if not comment_id:
        return None
    if account.platform not in DM_CAPABLE_PLATFORMS:
        return None

    from_ = comment.get("from") or {}
    commenter_id = from_.get("id")
    username = from_.get("username")

    # Never DM yourself. Replying to your own comment on your own post is the
    # first thing that happens in testing and it looks broken.
    if commenter_id and account.external_account_id and commenter_id == account.external_account_id:
        return None

    if db.scalar(select(PrivateReply).where(PrivateReply.comment_id == str(comment_id))) is not None:
        return None

    setting = get_or_create(db, account.owner_id)
    text = comment.get("text") or ""

    if not setting.dm_enabled:
        status, message = PrivateReplyStatus.SKIPPED, ""
    elif not matches_trigger(text, dm_trigger_keywords(setting)):
        status, message = PrivateReplyStatus.SKIPPED, ""
    else:
        message = render_message(setting, username or "there")
        status = PrivateReplyStatus.PENDING if message else PrivateReplyStatus.SKIPPED

    row = PrivateReply(
        owner_id=account.owner_id,
        lead_id=lead.id if lead is not None else None,
        platform=account.platform,
        comment_id=str(comment_id),
        recipient_username=username,
        message=message,
        status=status,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Meta redelivered the same comment to another worker first. Theirs wins.
        db.rollback()
        return None
    db.refresh(row)
    return row


def _expired(row: PrivateReply) -> bool:
    created = row.created_at
    if created is None:  # pragma: no cover - set by the DB default on insert
        return False
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return datetime.now(UTC) - created > timedelta(days=PRIVATE_REPLY_WINDOW_DAYS)


async def send_pending(db: Session, limit: int = 25) -> dict[str, int]:
    """Sends queued private replies. Returns counts by outcome.

    Ordered oldest-first because the 7-day window means the oldest are the ones
    about to be lost.
    """

    rows = list(
        db.scalars(
            select(PrivateReply)
            .where(PrivateReply.status == PrivateReplyStatus.PENDING)
            .order_by(PrivateReply.created_at)
            .limit(limit)
        )
    )
    counts = {"sent": 0, "failed": 0, "expired": 0}

    for row in rows:
        if _expired(row):
            row.status = PrivateReplyStatus.FAILED
            row.error = (
                f"Meta only allows a private reply within {PRIVATE_REPLY_WINDOW_DAYS} days "
                "of the comment, and that window has closed."
            )
            counts["expired"] += 1
            continue

        account = db.scalar(
            select(SocialAccount).where(
                SocialAccount.owner_id == row.owner_id,
                SocialAccount.platform == row.platform,
                SocialAccount.is_active.is_(True),
            )
        )
        if account is None:
            row.status = PrivateReplyStatus.FAILED
            row.error = (
                f"No active {row.platform.value} account is connected any more, so this "
                "DM could not be sent."
            )
            counts["failed"] += 1
            continue

        try:
            await send_private_reply(account, row.comment_id, row.message)
        except PrivateReplyError as exc:
            row.status = PrivateReplyStatus.FAILED
            row.error = str(exc)
            counts["failed"] += 1
            logger.warning("private reply to comment %s failed: %s", row.comment_id, exc)
            continue

        row.status = PrivateReplyStatus.SENT
        row.sent_at = datetime.now(UTC)
        row.error = None
        counts["sent"] += 1

    db.commit()

    if counts["failed"] or counts["expired"]:
        _notify_failures(db, rows)
    return counts


def _notify_failures(db: Session, rows: list[PrivateReply]) -> None:
    """One notification per user per batch, not per failed DM.

    A broken token fails every queued DM at once; ten identical alerts would
    train the user to ignore the one that matters.
    """

    by_owner: dict[uuid.UUID, PrivateReply] = {}
    for row in rows:
        if row.status is PrivateReplyStatus.FAILED and row.owner_id not in by_owner:
            by_owner[row.owner_id] = row

    for owner_id, example in by_owner.items():
        notify(
            db,
            owner_id,
            NotificationType.SYSTEM,
            title="Auto-DM could not be sent",
            body=(example.error or "")[:500],
            link="/settings?tab=automation",
        )
