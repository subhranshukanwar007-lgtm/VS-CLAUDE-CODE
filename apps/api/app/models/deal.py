import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DealStatus(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"


class Deal(BaseModel):
    __tablename__ = "deals"

    lead_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    stage_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("pipeline_stages.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus, name="deal_status"), default=DealStatus.OPEN)

    lead: Mapped["Lead"] = relationship(back_populates="deals")  # noqa: F821
    stage: Mapped["PipelineStage | None"] = relationship(back_populates="deals")  # noqa: F821
