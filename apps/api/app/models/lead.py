import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
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
    OTHER = "other"


class LeadStatus(StrEnum):
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    CHURNED = "churned"


class Lead(BaseModel):
    __tablename__ = "leads"

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
    last_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="leads")  # noqa: F821
    stage: Mapped["PipelineStage | None"] = relationship(back_populates="leads")  # noqa: F821
    deals: Mapped[list["Deal"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa: F821
    notes: Mapped[list["Note"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa: F821
