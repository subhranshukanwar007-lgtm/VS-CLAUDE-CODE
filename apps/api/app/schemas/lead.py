from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead import LeadSource, LeadStatus


class LeadCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: LeadSource = LeadSource.MANUAL
    status: LeadStatus = LeadStatus.LEAD
    stage_id: UUID | None = None
    estimated_value: float | None = None
    tags: str | None = None


class LeadUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: LeadSource | None = None
    status: LeadStatus | None = None
    stage_id: UUID | None = None
    estimated_value: float | None = None
    tags: str | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    stage_id: UUID | None
    full_name: str
    email: str | None
    phone: str | None
    company: str | None
    source: LeadSource
    status: LeadStatus
    estimated_value: float | None
    tags: str | None
