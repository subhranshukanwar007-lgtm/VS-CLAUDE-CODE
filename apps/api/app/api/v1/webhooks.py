import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.engagement_service import (
    process_webhook_payload,
    process_whatsapp_payload,
    verify_signature,
)
from app.services.whatsapp_service import WhatsAppError, auto_respond, find_conversation

logger = logging.getLogger("webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/meta")
def verify_meta_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
) -> PlainTextResponse:
    """The handshake Meta sends once when you register the webhook URL in your
    App dashboard — see https://developers.facebook.com/docs/graph-api/webhooks."""

    if (
        hub_mode == "subscribe"
        and settings.meta_webhook_verify_token
        and hub_verify_token == settings.meta_webhook_verify_token
    ):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/meta")
async def receive_meta_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, int]:
    raw_body = await request.body()
    if not verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    payload = await request.json()
    processed = process_webhook_payload(db, payload)

    # WhatsApp arrives on the same endpoint under the `messages` field. Storing is
    # synchronous so Meta gets a fast 200; the AI reply happens after, and a
    # failure there must not make Meta retry the whole delivery.
    replied = 0
    for owner, phone in process_whatsapp_payload(db, payload):
        conversation = find_conversation(db, owner.id, phone)
        if conversation is None:
            continue
        try:
            if await auto_respond(db, owner, conversation) is not None:
                replied += 1
        except WhatsAppError as exc:
            logger.warning("whatsapp auto-reply failed for %s: %s", phone, exc)

    return {"processed": processed, "whatsapp_replies": replied}
