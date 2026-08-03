from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.whatsapp import MessageDirection, MessageStatus


class WhatsAppMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    direction: MessageDirection
    status: MessageStatus
    body: str
    is_ai_generated: bool
    error: str | None
    created_at: datetime


class WhatsAppConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    wa_phone: str
    display_name: str | None
    last_inbound_at: datetime | None
    ai_enabled: bool
    handed_off_at: datetime | None

    window_open: bool = False
    window_expires_at: datetime | None = None


class WhatsAppThread(WhatsAppConversationRead):
    messages: list[WhatsAppMessageRead] = []


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class DraftReply(BaseModel):
    """A suggested reply, not a sent one. Returned so the user can edit before
    sending — the AI drafts, the human decides."""

    body: str
