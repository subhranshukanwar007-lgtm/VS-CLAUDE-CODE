from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PipelineStageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    order: int = 0
    color: str = "#6366f1"
    is_won_stage: bool = False
    is_lost_stage: bool = False


class PipelineStageUpdate(BaseModel):
    name: str | None = None
    order: int | None = None
    color: str | None = None
    is_won_stage: bool | None = None
    is_lost_stage: bool | None = None


class PipelineStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    order: int
    color: str
    is_won_stage: bool
    is_lost_stage: bool
