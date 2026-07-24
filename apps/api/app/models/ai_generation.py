import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AIGenerationKind(StrEnum):
    CAPTION = "caption"
    HASHTAGS = "hashtags"
    SCRIPT = "script"
    AGENT_CHAT = "agent_chat"


class AIProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class AIGeneration(BaseModel):
    """Audit trail of every AI generation request: who asked, what provider/model
    answered, the prompt and result. Powers cost tracking and lets users revisit
    past generations."""

    __tablename__ = "ai_generations"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kind: Mapped[AIGenerationKind] = mapped_column(Enum(AIGenerationKind, name="ai_generation_kind"), nullable=False)
    provider: Mapped[AIProvider] = mapped_column(Enum(AIProvider, name="ai_provider"), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(String(8000), nullable=False)
    result: Mapped[str] = mapped_column(String(16000), nullable=False)
