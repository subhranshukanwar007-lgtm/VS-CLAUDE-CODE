import hashlib
import hmac
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.note import Note
from app.models.notification import NotificationType
from app.models.post import Platform, Post
from app.models.social_account import SocialAccount
from app.services.intent_service import score_lead_fast
from app.services.notification_service import notify

logger = logging.getLogger("engagement")

_PLATFORM_TO_SOURCE = {
    Platform.INSTAGRAM: LeadSource.INSTAGRAM,
    Platform.FACEBOOK: LeadSource.FACEBOOK,
}


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verifies Meta's X-Hub-Signature-256 header: sha256=<hex HMAC of the raw
    body, keyed by the app secret>. Per Meta's own webhook docs. Returns False
    (never raises) so callers can uniformly reject on any failure — no secret
    configured, no header, or a mismatch are all just "not verified"."""

    if not settings.meta_app_secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(settings.meta_app_secret.encode(), payload, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


def _find_owner_account(db: Session, external_account_id: str) -> SocialAccount | None:
    return db.scalar(
        select(SocialAccount).where(
            SocialAccount.external_account_id == external_account_id,
            SocialAccount.is_active.is_(True),
        )
    )


def _find_source_post(db: Session, account: SocialAccount, comment: dict[str, Any]) -> Post | None:
    """Match the commented-on media back to the Post we published, so a lead can be
    attributed to the content that earned it.

    Meta nests the media id differently depending on the surface (Instagram sends
    `media.id`, Facebook sends `post_id` on the change value), so several shapes
    are checked. Returns None when the post wasn't published through this app —
    attribution is best-effort and its absence must never block lead capture.
    """

    media = comment.get("media")
    candidates = [
        media.get("id") if isinstance(media, dict) else None,
        comment.get("media_id"),
        comment.get("post_id"),
    ]
    for external_id in candidates:
        if not external_id:
            continue
        post = db.scalar(
            select(Post).where(
                Post.author_id == account.owner_id,
                Post.external_post_id == str(external_id),
            )
        )
        if post is not None:
            return post
    return None


def capture_comment_as_lead(db: Session, account: SocialAccount, comment: dict[str, Any]) -> Lead | None:
    """Given a parsed Meta 'comments' webhook value and the SocialAccount it
    routed to: create a new Lead for a first-time commenter, or add a Note to
    their existing Lead if they've engaged before (deduped on
    external_platform_id, the commenter's platform user id)."""

    from_ = comment.get("from") or {}
    commenter_id = from_.get("id")
    commenter_username = from_.get("username") or "Instagram user"
    text = comment.get("text", "")

    if not commenter_id:
        return None

    source = _PLATFORM_TO_SOURCE.get(account.platform, LeadSource.OTHER)

    existing = db.scalar(
        select(Lead).where(
            Lead.owner_id == account.owner_id,
            Lead.source == source,
            Lead.external_platform_id == commenter_id,
        )
    )

    source_post = _find_source_post(db, account, comment)

    if existing is not None:
        db.add(Note(lead_id=existing.id, author_id=account.owner_id, body=f"New comment: {text}"))
        # Attribute to the first post that earned them; don't rewrite history when
        # they later comment on something else.
        if existing.source_post_id is None and source_post is not None:
            existing.source_post_id = source_post.id
        db.commit()
        # Re-score: a follower who only ever left emojis may have just asked the
        # price, and that's the moment worth interrupting the user for.
        score_lead_fast(db, existing)
        return existing

    lead = Lead(
        owner_id=account.owner_id,
        full_name=commenter_username,
        source=source,
        status=LeadStatus.LEAD,
        external_platform_id=commenter_id,
        source_post_id=source_post.id if source_post else None,
        tags="engagement",
    )
    db.add(lead)
    db.flush()
    db.add(Note(lead_id=lead.id, author_id=account.owner_id, body=f"Commented: {text}"))
    db.commit()
    db.refresh(lead)

    notify(
        db,
        account.owner_id,
        NotificationType.LEAD_CREATED,
        title=f"New lead from a comment: {commenter_username}",
        body=text[:200],
        link=f"/crm?lead={lead.id}",
    )
    # Score immediately so an obvious buying question ("how much?") reaches the
    # user as a hot-lead alert in the same second the comment arrives.
    score_lead_fast(db, lead)
    return lead


def process_webhook_payload(db: Session, payload: dict[str, Any]) -> int:
    """Processes a full Meta webhook payload (possibly several entries/changes
    batched together) and returns how many leads were created or updated.
    Entries for accounts nobody has registered (via /social-accounts) are
    logged and skipped rather than erroring the whole batch."""

    count = 0
    for entry in payload.get("entry", []):
        external_account_id = entry.get("id")
        if not external_account_id:
            continue
        account = _find_owner_account(db, external_account_id)
        if account is None:
            logger.info("no SocialAccount registered for external_account_id=%s, skipping", external_account_id)
            continue

        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            lead = capture_comment_as_lead(db, account, change.get("value", {}))
            if lead is not None:
                count += 1

    return count
