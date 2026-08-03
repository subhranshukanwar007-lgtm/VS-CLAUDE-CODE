import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class LeadSource(StrEnum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    PINTEREST = "pinterest"
    WHATSAPP = "whatsapp"
    WEBSITE = "website"
    REFERRAL = "referral"
    MANUAL = "manual"
    # Sourced by us rather than by them — an Apollo search, a list, a cold
    # approach. Kept separate from the inbound sources on purpose: goal
    # performance measures leads *per post*, and outbound leads never came from
    # a post. Filing them as OTHER would quietly inflate the count of leads the
    # content failed to attribute, which is the one number that tells the user
    # their tracking is broken.
    OUTBOUND = "outbound"
    OTHER = "other"


class LeadStatus(StrEnum):
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    CHURNED = "churned"


class LeadIntent(StrEnum):
    """How close this lead looks to buying, judged by AI from what they actually
    said (their comments, DM replies and notes).

    HOT means they showed a real buying signal — asked the price, asked how to
    join, asked about availability. That's the moment worth a human conversation,
    so it triggers a notification. WARM is genuine interest without a buying
    signal. COLD is a compliment or a generic reaction. UNKNOWN means not scored
    yet, which is different from scored-and-found-cold.
    """

    UNKNOWN = "unknown"
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class Lead(BaseModel):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_owner_source_external_id", "owner_id", "source", "external_platform_id"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    stage_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("pipeline_stages.id"), nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[LeadSource] = mapped_column(Enum(LeadSource, name="lead_source"), default=LeadSource.MANUAL)
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus, name="lead_status"), default=LeadStatus.LEAD)
    estimated_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment=(
            "ISO 3166-1 alpha-2, e.g. 'US', 'IN', 'GB'. Set manually or from ad "
            "targeting: Meta's comment webhook does not include the commenter's "
            "country, so this is never auto-detected from engagement."
        ),
    )
    intent: Mapped[LeadIntent] = mapped_column(
        Enum(LeadIntent, name="lead_intent"), default=LeadIntent.UNKNOWN, nullable=False, index=True
    )
    intent_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="The AI's one-line justification, shown to the user so the score is auditable"
    )
    intent_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_platform_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Commenter/sender ID from the source platform, for dedupe on repeat engagement"
    )
    source_post_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment=(
            "The post this lead engaged with, when engagement capture could match the "
            "webhook's media id to a published post. ON DELETE SET NULL: deleting a post "
            "must not delete the leads it earned."
        ),
    )

    owner: Mapped["User"] = relationship(back_populates="leads")  # noqa: F821
    stage: Mapped["PipelineStage | None"] = relationship(back_populates="leads")  # noqa: F821
    deals: Mapped[list["Deal"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa: F821
    notes: Mapped[list["Note"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa: F821
