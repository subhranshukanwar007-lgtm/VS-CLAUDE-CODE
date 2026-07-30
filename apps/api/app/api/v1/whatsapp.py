from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.whatsapp import (
    DraftReply,
    SendMessageRequest,
    WhatsAppConversationRead,
    WhatsAppMessageRead,
    WhatsAppThread,
)
from app.services.ai.base import AIProviderError
from app.services.whatsapp_service import (
    WhatsAppError,
    conversation_history,
    draft_reply,
    handoff,
    send_message,
    window_expires_at,
    window_open,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _owned(db: Session, user: User, conversation_id: UUID) -> WhatsAppConversation:
    conversation = db.get(WhatsAppConversation, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation")
    if conversation.owner_id != user.id:
        raise ForbiddenError()
    return conversation


def _to_read(conversation: WhatsAppConversation) -> WhatsAppConversationRead:
    return WhatsAppConversationRead.model_validate(conversation).model_copy(
        update={
            "window_open": window_open(conversation),
            "window_expires_at": window_expires_at(conversation),
        }
    )


@router.get("/conversations", response_model=list[WhatsAppConversationRead])
def list_conversations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[WhatsAppConversationRead]:
    conversations = db.scalars(
        select(WhatsAppConversation)
        .where(WhatsAppConversation.owner_id == user.id)
        .order_by(WhatsAppConversation.last_inbound_at.desc().nulls_last())
    ).all()
    return [_to_read(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=WhatsAppThread)
def read_conversation(
    conversation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WhatsAppThread:
    conversation = _owned(db, user, conversation_id)
    messages = conversation_history(db, conversation)
    return WhatsAppThread(
        **_to_read(conversation).model_dump(),
        messages=[WhatsAppMessageRead.model_validate(m) for m in messages],
    )


@router.post("/conversations/{conversation_id}/draft", response_model=DraftReply)
async def draft(
    conversation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DraftReply:
    """Suggest a reply without sending it, so it can be edited first."""

    conversation = _owned(db, user, conversation_id)
    try:
        return DraftReply(body=await draft_reply(db, user, conversation))
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    except WhatsAppError as exc:
        raise BadRequestError(str(exc)) from exc


@router.post("/conversations/{conversation_id}/send", response_model=WhatsAppMessageRead)
async def send(
    conversation_id: UUID,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WhatsAppMessage:
    """Send a message. Sending by hand also hands the conversation off, so the AI
    stops replying over you."""

    conversation = _owned(db, user, conversation_id)
    try:
        message = await send_message(db, conversation, payload.body)
    except WhatsAppError as exc:
        raise BadRequestError(str(exc)) from exc
    handoff(db, conversation)
    return message


@router.post("/conversations/{conversation_id}/handoff", response_model=WhatsAppConversationRead)
def take_over(
    conversation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WhatsAppConversationRead:
    """Stop the AI on this conversation."""

    return _to_read(handoff(db, _owned(db, user, conversation_id)))
