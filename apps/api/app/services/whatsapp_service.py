"""WhatsApp Business: receive, understand, answer, and know when to stop.

Shape of the automation, and why:

**Inbound only.** Replying inside the 24-hour customer-service window is free;
starting a conversation is billed and requires an approved template. So this
answers people who messaged first and never initiates. That's also the version
that doesn't feel like spam.

**The AI answers questions and then gets out of the way.** The moment someone
shows real buying intent, the conversation is handed to the human and the AI
stops replying — `ai_enabled` flips off. Automating the close is where this kind
of system starts costing sales rather than making them, and the user said
plainly they want to have that conversation themselves.

**The window is checked before the API call, not after.** Meta rejects free-form
sends outside 24 hours, and the resulting error is not something a user should
have to decode. Failing locally with "they last messaged 3 days ago, so only an
approved template can be sent" is a usable message.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.automation_setting import LANGUAGE_INSTRUCTIONS
from app.models.lead import Lead, LeadIntent, LeadSource, LeadStatus
from app.models.notification import NotificationType
from app.models.user import User
from app.models.whatsapp import (
    MessageDirection,
    MessageStatus,
    WhatsAppConversation,
    WhatsAppMessage,
)
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_provider
from app.services.automation_settings_service import get_or_create
from app.services.intent_service import score_lead_fast
from app.services.notification_service import notify

logger = logging.getLogger("whatsapp")

GRAPH_VERSION = "v21.0"
WINDOW_HOURS = 24
_TIMEOUT = httpx.Timeout(30.0)
_MAX_HISTORY = 12


class WhatsAppError(Exception):
    """Raised for anything the user needs to act on: missing credentials, an
    expired window, or a rejection from Meta."""


class WindowExpiredError(WhatsAppError):
    pass


def is_configured() -> bool:
    return bool(settings.whatsapp_phone_number_id and settings.whatsapp_access_token)


def window_open(conversation: WhatsAppConversation, now: datetime | None = None) -> bool:
    if conversation.last_inbound_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    return now - conversation.last_inbound_at < timedelta(hours=WINDOW_HOURS)


def window_expires_at(conversation: WhatsAppConversation) -> datetime | None:
    if conversation.last_inbound_at is None:
        return None
    return conversation.last_inbound_at + timedelta(hours=WINDOW_HOURS)


def find_conversation(db: Session, owner_id: uuid.UUID, phone: str) -> WhatsAppConversation | None:
    return db.scalar(
        select(WhatsAppConversation).where(
            WhatsAppConversation.owner_id == owner_id, WhatsAppConversation.wa_phone == phone
        )
    )


# --- inbound ---


def _find_or_create_lead(db: Session, owner_id: uuid.UUID, phone: str, name: str | None) -> Lead:
    existing = db.scalar(
        select(Lead).where(
            Lead.owner_id == owner_id,
            Lead.source == LeadSource.WHATSAPP,
            Lead.external_platform_id == phone,
        )
    )
    if existing:
        return existing

    lead = Lead(
        owner_id=owner_id,
        full_name=name or f"WhatsApp {phone[-4:]}",
        phone=f"+{phone}",
        source=LeadSource.WHATSAPP,
        status=LeadStatus.LEAD,
        external_platform_id=phone,
        tags="whatsapp",
    )
    db.add(lead)
    db.flush()
    notify(
        db,
        owner_id,
        NotificationType.LEAD_CREATED,
        title=f"New WhatsApp lead: {lead.full_name}",
        link=f"/crm?lead={lead.id}",
    )
    return lead


def record_inbound(
    db: Session, owner: User, phone: str, body: str, external_id: str | None, name: str | None = None
) -> WhatsAppMessage | None:
    """Store an incoming message and open the reply window.

    Returns None when this is a redelivery of a message already stored — Meta
    retries webhooks, and a duplicate would otherwise double-reply.
    """

    if external_id:
        seen = db.scalar(select(WhatsAppMessage).where(WhatsAppMessage.external_id == external_id))
        if seen is not None:
            logger.info("ignoring redelivered whatsapp message %s", external_id)
            return None

    conversation = db.scalar(
        select(WhatsAppConversation).where(
            WhatsAppConversation.owner_id == owner.id, WhatsAppConversation.wa_phone == phone
        )
    )
    if conversation is None:
        lead = _find_or_create_lead(db, owner.id, phone, name)
        conversation = WhatsAppConversation(
            owner_id=owner.id, lead_id=lead.id, wa_phone=phone, display_name=name
        )
        db.add(conversation)
        db.flush()
    elif name and not conversation.display_name:
        conversation.display_name = name

    conversation.last_inbound_at = datetime.now(timezone.utc)

    message = WhatsAppMessage(
        conversation_id=conversation.id,
        direction=MessageDirection.INBOUND,
        status=MessageStatus.RECEIVED,
        body=body,
        external_id=external_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Score from what they actually said, same as comments — a WhatsApp "kitna
    # hai" is the strongest buying signal in this whole system.
    if conversation.lead_id:
        lead = db.get(Lead, conversation.lead_id)
        if lead is not None:
            _score_from_conversation(db, lead, conversation)

    return message


def _score_from_conversation(db: Session, lead: Lead, conversation: WhatsAppConversation) -> None:
    """Intent scoring reads a lead's notes, so mirror inbound WhatsApp text there.
    Keeps one scoring path rather than two that can disagree."""

    from app.models.note import Note

    latest = db.scalar(
        select(WhatsAppMessage)
        .where(
            WhatsAppMessage.conversation_id == conversation.id,
            WhatsAppMessage.direction == MessageDirection.INBOUND,
        )
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(1)
    )
    if latest is None:
        return
    db.add(Note(lead_id=lead.id, author_id=lead.owner_id, body=f"WhatsApp: {latest.body}"))
    db.commit()
    score_lead_fast(db, lead)


# --- outbound ---


async def send_message(db: Session, conversation: WhatsAppConversation, body: str, ai: bool = False) -> WhatsAppMessage:
    if not is_configured():
        raise WhatsAppError(
            "WhatsApp isn't configured. Add WHATSAPP_PHONE_NUMBER_ID and "
            "WHATSAPP_ACCESS_TOKEN to your .env."
        )
    if not window_open(conversation):
        last = conversation.last_inbound_at
        when = last.strftime("%Y-%m-%d %H:%M UTC") if last else "never"
        raise WindowExpiredError(
            f"The 24-hour reply window has closed (they last messaged {when}). "
            "Only a pre-approved template message can be sent now, and that is billed."
        )

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": conversation.wa_phone,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    message = WhatsAppMessage(
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND,
        status=MessageStatus.DRAFT,
        body=body,
        is_ai_generated=ai,
    )
    db.add(message)
    db.commit()

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        detail = _graph_error(resp)
        message.status = MessageStatus.FAILED
        message.error = detail
        db.commit()
        raise WhatsAppError(f"WhatsApp rejected the message: {detail}")

    body_json = resp.json()
    sent = (body_json.get("messages") or [{}])[0]
    message.status = MessageStatus.SENT
    message.external_id = sent.get("id")
    db.commit()
    db.refresh(message)
    return message


def _graph_error(response: httpx.Response) -> str:
    try:
        error = response.json().get("error") or {}
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:300]}"
    parts = [str(error.get("message") or response.text[:300])]
    if error.get("error_user_msg"):
        parts.append(str(error["error_user_msg"]))
    if error.get("code") is not None:
        parts.append(f"(Meta error code {error['code']})")
    return " ".join(parts)


# --- the AI reply ---

_SYSTEM = """You are answering WhatsApp messages on behalf of a health and fitness coach.

You are their assistant, not the coach. Be warm, brief and genuinely useful.

Hard rules:
- WhatsApp, not email. Two or three short sentences. No greetings like "Dear", no \
sign-offs, no bullet lists unless they asked for a list.
- Answer what they actually asked. Do not pivot to a pitch.
- NEVER invent a statistic, study or medical claim. If a number would strengthen \
a line, write the line without it.
- NEVER promise a result ("you'll lose 10kg"). You may say what a programme \
involves.
- NEVER diagnose. Suggest getting tested if something sounds medical.
- If you don't know something specific to this coach — exact prices, start dates, \
what's included — say the coach will confirm shortly. Do not guess.

If they show real buying intent — ask the price, ask how to join, say they want \
to start — answer briefly and say the coach will message them personally. Do not \
try to close the sale yourself."""


def conversation_history(db: Session, conversation: WhatsAppConversation) -> list[WhatsAppMessage]:
    messages = db.scalars(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conversation.id)
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(_MAX_HISTORY)
    ).all()
    return list(reversed(messages))


async def draft_reply(db: Session, owner: User, conversation: WhatsAppConversation) -> str:
    history = conversation_history(db, conversation)
    if not history:
        raise WhatsAppError("There's nothing to reply to yet.")

    setting = get_or_create(db, owner.id)
    transcript = "\n".join(
        f"{'Them' if m.direction == MessageDirection.INBOUND else 'You'}: {m.body}" for m in history
    )

    system = _SYSTEM + f"\n\n{LANGUAGE_INSTRUCTIONS[setting.reply_language]}"
    if owner.brand_voice:
        system += f"\n\nThe coach's voice, match it: {owner.brand_voice.strip()}"

    provider = get_provider()
    reply = await provider.generate(
        f"Conversation so far:\n{transcript}\n\nWrite the next reply.", system=system, max_tokens=300
    )
    return reply.strip()


async def auto_respond(db: Session, owner: User, conversation: WhatsAppConversation) -> WhatsAppMessage | None:
    """Draft and send a reply, unless a human should take this one.

    Returns None when the AI deliberately stayed quiet — the caller should treat
    that as normal, not as a failure.
    """

    setting = get_or_create(db, owner.id)
    if not setting.whatsapp_ai_enabled or not conversation.ai_enabled:
        return None

    lead = db.get(Lead, conversation.lead_id) if conversation.lead_id else None
    if lead is not None and lead.intent == LeadIntent.HOT:
        # They're ready to buy. Hand over rather than letting a bot negotiate.
        handoff(db, conversation)
        notify(
            db,
            owner.id,
            NotificationType.HOT_LEAD,
            title=f"\U0001f525 {lead.full_name} is asking to buy on WhatsApp",
            body=lead.intent_reason,
            link=f"/crm?lead={lead.id}",
        )
        return None

    try:
        reply = await draft_reply(db, owner, conversation)
    except AIProviderError as exc:
        logger.info("whatsapp auto-reply unavailable: %s", exc)
        return None

    return await send_message(db, conversation, reply, ai=True)


def handoff(db: Session, conversation: WhatsAppConversation) -> WhatsAppConversation:
    """Stop the AI on this conversation so it doesn't talk over the human."""

    conversation.ai_enabled = False
    conversation.handed_off_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    return conversation


# --- webhook parsing ---


def extract_messages(value: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull (phone, name, text, id) out of a WhatsApp `messages` webhook value.

    Non-text messages (image, audio, sticker) are skipped rather than guessed at —
    an assistant replying to a photo it never saw is worse than one that stays
    quiet and lets the human look.
    """

    contacts = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts", [])}
    out = []
    for message in value.get("messages", []):
        if message.get("type") != "text":
            continue
        phone = message.get("from")
        text = (message.get("text") or {}).get("body", "")
        if not phone or not text:
            continue
        out.append(
            {"phone": phone, "name": contacts.get(phone), "body": text, "external_id": message.get("id")}
        )
    return out
