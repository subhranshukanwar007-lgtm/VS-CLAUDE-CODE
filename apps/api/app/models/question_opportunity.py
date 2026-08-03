"""A public question someone asked that you could answer to win attention.

Populated by a Celery beat job that searches configured keywords on the sources
below. Each row is one found post, plus an AI-drafted answer awaiting your
approval — the same "AI drafts, human approves" shape as lead follow-ups.

Source capabilities differ, and the difference is load-bearing rather than
cosmetic:

- THREADS: searchable via Threads' /keyword_search, and replies can be posted
  through the API. Fully automatable end to end.
- REDDIT: searchable on Reddit's free tier, but *posting* a comment needs an
  approved OAuth client (self-service signup is closed; approval takes weeks and
  the free tier is non-commercial). So finding works immediately, replying only
  once the user supplies approved credentials.
- QUORA: has no public API at all. Rows are never created automatically for
  Quora; the source exists so a user can paste in a question they found manually
  and get an AI-drafted answer to copy back. Nothing here scrapes Quora.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class QuestionSource(StrEnum):
    THREADS = "threads"
    REDDIT = "reddit"
    QUORA = "quora"


class QuestionStatus(StrEnum):
    NEW = "new"
    DRAFTED = "drafted"
    REPLIED = "replied"
    SKIPPED = "skipped"
    FAILED = "failed"


class QuestionOpportunity(BaseModel):
    __tablename__ = "question_opportunities"
    __table_args__ = (
        # Dedupe: the search job re-runs on a schedule and will keep seeing the
        # same posts, so the same external post must never become a second row.
        Index(
            "uq_question_owner_source_external",
            "owner_id",
            "source",
            "external_id",
            unique=True,
        ),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source: Mapped[QuestionSource] = mapped_column(Enum(QuestionSource, name="question_source"), nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus, name="question_status"), default=QuestionStatus.NEW, nullable=False
    )

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    matched_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    ai_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_reply_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
