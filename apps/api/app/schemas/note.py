from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    lead_id: UUID
    body: str = Field(min_length=1, max_length=4000)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
