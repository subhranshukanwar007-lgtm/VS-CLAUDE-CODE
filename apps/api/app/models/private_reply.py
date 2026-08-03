"""One row per comment we have offered to auto-DM.

This table exists because of a hard rule in Meta's API rather than a design
preference: **a private reply may be sent only once per comment, ever.** Meta
enforces it server-side, so a retry after a network blip does not silently
double-message someone — it fails. That makes "did we already handle this
comment?" a question that must survive a crash, a redeploy and a webhook
redelivery (Meta retries deliveries it thinks failed).

So the row is written inside the webhook's transaction, before any network call,
with a unique constraint on the comment id. The unique constraint *is* the
deduplication — not an in-memory set, not a check-then-act, both of which lose
the race when Meta redelivers the same event to two workers at once.

Sending happens afterwards, from a Celery task reading PENDING rows. A failed
send therefore leaves a visible FAILED row carrying Meta's own error text,
instead of vanishing into a log line.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.post import Platform

# Meta's private reply window: a comment can be replied to privately for 7 days
# after it was posted. Past that the API rejects it, so the queue gives up rather
# than retrying forever.
PRIVATE_REPLY_WINDOW_DAYS = 7


class PrivateReplyStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    # Matched no trigger keyword, or automation was off — recorded anyway so the
    # comment is never reconsidered if the same webhook is redelivered.
    SKIPPED = "skipped"


class PrivateReply(BaseModel):
    __tablename__ = "private_replies"
    __table_args__ = (
        Index("ix_private_replies_status_created", "status", "created_at"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )

    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="post_platform"), nullable=False)

    # The commenter's comment id, from the webhook. Unique because Meta allows
    # exactly one private reply per comment.
    comment_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    recipient_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Rendered at queue time, not send time, so what was sent is what is stored
    # even if the template is edited later.
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[PrivateReplyStatus] = mapped_column(
        Enum(PrivateReplyStatus, name="private_reply_status"),
        default=PrivateReplyStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
