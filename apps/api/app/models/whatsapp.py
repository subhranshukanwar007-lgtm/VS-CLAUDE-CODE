"""WhatsApp Business conversations.

The 24-hour window is the load-bearing constraint here, not a detail. Meta lets
you send free-form messages only within 24 hours of the customer's last message;
outside it, a free-form send is rejected and only a pre-approved template will go
through. So `last_inbound_at` is tracked per conversation and checked *before*
calling the API — failing locally with a clear reason beats a rejection from Meta
that the user has to decode.

Cost, for context on why inbound-only automation is the right shape: replying
inside that window is free. Only business-initiated conversations are billed.
An assistant that answers people who messaged first is therefore effectively free
to run, while one that starts conversations is not.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"
    RECEIVED = "received"


class WhatsAppConversation(BaseModel):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        Index("uq_whatsapp_owner_phone", "owner_id", "wa_phone", unique=True),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    wa_phone: Mapped[str] = mapped_column(String(32), nullable=False, comment="E.164 without '+', as Meta sends it")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_inbound_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start of the 24-hour free-form window. Null means never messaged us.",
    )
    ai_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Turned off automatically once a human takes over, so the AI stops talking over them.",
    )
    handed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhatsAppMessage(BaseModel):
    __tablename__ = "whatsapp_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="wa_direction"), nullable=False
    )
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="wa_message_status"), default=MessageStatus.RECEIVED, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment="Meta's message id, used to ignore redelivered webhooks"
    )
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
