from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ai_generation import AIProvider


class CaptionRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    platform: str = "instagram"
    tone: str = "engaging"
    brand_voice: str | None = None
    provider: AIProvider | None = None


class HashtagRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    count: int = Field(default=15, ge=1, le=30)
    provider: AIProvider | None = None


class ScriptRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    format: str = "reel"
    duration_seconds: int = Field(default=30, ge=5, le=600)
    brand_voice: str | None = None
    provider: AIProvider | None = None


class AgentChatRequest(BaseModel):
    agent: str = Field(description="One of: ceo, marketing, content, designer, editor, analytics, sales, crm, research, trend, support, scheduler")
    message: str = Field(min_length=1, max_length=4000)
    provider: AIProvider | None = None


class AIGenerationResult(BaseModel):
    id: UUID
    provider: AIProvider
    model: str
    result: str
