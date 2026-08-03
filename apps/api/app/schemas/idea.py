from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.content_idea import IdeaSource
from app.models.post import PostFormat, PostGoal


class ContentIdeaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    problem: str
    angle: str | None
    suggested_goal: PostGoal
    suggested_format: PostFormat
    source: IdeaSource
    times_used: int
    last_used_at: datetime | None
    is_active: bool


class ContentIdeaCreate(BaseModel):
    problem: str = Field(min_length=5, max_length=2000)
    angle: str | None = Field(default=None, max_length=2000)
    suggested_goal: PostGoal = PostGoal.REACH
    suggested_format: PostFormat | None = None


class ContentIdeaUpdate(BaseModel):
    problem: str | None = Field(default=None, min_length=5, max_length=2000)
    angle: str | None = Field(default=None, max_length=2000)
    suggested_goal: PostGoal | None = None
    suggested_format: PostFormat | None = None
    is_active: bool | None = None


class TodaysIdea(BaseModel):
    """What to make today.

    `idea` is None only when the user has no active ideas at all — the bank is
    seeded on first read, so that means they deliberately cleared it.
    """

    model_config = ConfigDict(from_attributes=True)

    idea: ContentIdeaRead | None
    reason: str | None
    total_active: int
