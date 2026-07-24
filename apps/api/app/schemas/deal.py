from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.deal import DealStatus


class DealCreate(BaseModel):
    lead_id: UUID
    stage_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    value: float = 0
    currency: str = "USD"
    status: DealStatus = DealStatus.OPEN


class DealUpdate(BaseModel):
    stage_id: UUID | None = None
    title: str | None = None
    value: float | None = None
    currency: str | None = None
    status: DealStatus | None = None


class DealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    stage_id: UUID | None
    title: str
    value: float
    currency: str
    status: DealStatus
