"""Tests for the WhatsApp assistant.

Three properties carry the feature, and each has a test that would fail loudly if
it broke:

1. The 24-hour window is enforced *before* calling Meta, so an expired window is a
   readable local error rather than a decoded API rejection.
2. Redelivered webhooks don't produce a second reply — Meta retries, and a
   double-reply is visible to the customer.
3. The AI stands down the moment someone is ready to buy, instead of negotiating.
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import app.config as config_module
from app.database import get_db
from app.main import app
from app.models.lead import Lead
from app.models.whatsapp import WhatsAppConversation
from app.services.ai.base import AIProvider
from app.services.whatsapp_service import (
    WhatsAppError,
    WindowExpiredError,
    extract_messages,
    find_conversation,
    send_message,
    window_open,
)

PHONE_ID = "1234567890"


class StubAI(AIProvider):
    name = "openai"
    model = "stub"

    def __init__(self, reply="Sure — three sets of ten works well. Let me know how it goes."):
        self.reply = reply
        self.last_system = None

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        self.last_system = system
        return self.reply


def _db():
    return next(app.dependency_overrides[get_db]())


def _configure(monkeypatch, ai: StubAI | None = None):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    monkeypatch.setattr(config_module.settings, "whatsapp_phone_number_id", PHONE_ID)
    monkeypatch.setattr(config_module.settings, "whatsapp_access_token", "tok")
    if ai is not None:
        monkeypatch.setattr("app.services.whatsapp_service.get_provider", lambda kind=None: ai)


def _inbound_payload(text: str, phone="919812345678", msg_id="wamid.1", name="Priya"):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": PHONE_ID},
                            "contacts": [{"wa_id": phone, "profile": {"name": name}}],
                            "messages": [
                                {"from": phone, "id": msg_id, "type": "text", "text": {"body": text}}
                            ],
                        },
                    }
                ]
            }
        ]
    }


def _post_webhook(auth_client, payload, monkeypatch=None):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    return auth_client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": sig},
    )


def _stub_send_ok(monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={"messages": [{"id": "wamid.out.1"}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)


# --- parsing ---


def test_extract_messages_pulls_text_and_name():
    value = _inbound_payload("hello")["entry"][0]["changes"][0]["value"]
    parsed = extract_messages(value)
    assert parsed == [
        {"phone": "919812345678", "name": "Priya", "body": "hello", "external_id": "wamid.1"}
    ]


def test_non_text_messages_are_skipped():
    """An assistant replying to a photo it never saw is worse than one that stays
    quiet and lets the human look."""

    value = {
        "metadata": {"phone_number_id": PHONE_ID},
        "messages": [{"from": "91981", "id": "w1", "type": "image", "image": {"id": "i1"}}],
    }
    assert extract_messages(value) == []


# --- inbound ---


def test_inbound_message_creates_a_lead_and_conversation(auth_client, monkeypatch):
    _configure(monkeypatch)
    assert _post_webhook(auth_client, _inbound_payload("hi, how does coaching work?")).status_code == 200

    leads = auth_client.get("/api/v1/leads").json()
    assert any(lead["full_name"] == "Priya" and lead["source"] == "whatsapp" for lead in leads)

    conversations = auth_client.get("/api/v1/whatsapp/conversations").json()
    assert len(conversations) == 1
    assert conversations[0]["wa_phone"] == "919812345678"
    assert conversations[0]["window_open"] is True


def test_second_message_reuses_the_same_lead(auth_client, monkeypatch):
    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("first", msg_id="wamid.1"))
    _post_webhook(auth_client, _inbound_payload("second", msg_id="wamid.2"))

    assert len([lead for lead in auth_client.get("/api/v1/leads").json() if lead["source"] == "whatsapp"]) == 1
    assert len(auth_client.get("/api/v1/whatsapp/conversations").json()) == 1


def test_redelivered_webhook_is_ignored(auth_client, monkeypatch):
    """Meta retries. A duplicate would double-reply, which the customer sees."""

    _configure(monkeypatch)
    payload = _inbound_payload("hello", msg_id="wamid.same")
    _post_webhook(auth_client, payload)
    _post_webhook(auth_client, payload)

    conversation = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    thread = auth_client.get(f"/api/v1/whatsapp/conversations/{conversation['id']}").json()
    assert len([m for m in thread["messages"] if m["direction"] == "inbound"]) == 1


def test_webhook_for_another_number_is_ignored(auth_client, monkeypatch):
    """A mismatched phone_number_id is somebody else's webhook."""

    _configure(monkeypatch)
    payload = _inbound_payload("hello")
    payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] = "999"
    _post_webhook(auth_client, payload)

    assert auth_client.get("/api/v1/whatsapp/conversations").json() == []


def test_buying_question_on_whatsapp_scores_hot_and_alerts(auth_client, monkeypatch):
    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("bhai kitna hai ye program?"))

    lead = next(lead for lead in auth_client.get("/api/v1/leads").json() if lead["source"] == "whatsapp")
    assert lead["intent"] == "hot"

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "hot_lead" for n in notifications)


# --- the 24-hour window ---


@pytest.mark.asyncio
async def test_sending_outside_the_window_fails_locally(auth_client, monkeypatch):
    """Checked before the API call, so the message explains the actual rule rather
    than relaying a Meta error code."""

    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("hello"))

    db = _db()
    try:
        conversation = db.query(WhatsAppConversation).one()
        conversation.last_inbound_at = datetime.now(timezone.utc) - timedelta(hours=30)
        db.commit()

        assert window_open(conversation) is False
        with pytest.raises(WindowExpiredError, match="24-hour reply window has closed"):
            await send_message(db, conversation, "too late")
    finally:
        db.close()


def test_window_state_is_reported_to_the_ui(auth_client, monkeypatch):
    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("hello"))

    db = _db()
    try:
        conversation = db.query(WhatsAppConversation).one()
        conversation.last_inbound_at = datetime.now(timezone.utc) - timedelta(hours=30)
        db.commit()
    finally:
        db.close()

    listed = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    assert listed["window_open"] is False
    assert listed["window_expires_at"] is not None


@pytest.mark.asyncio
async def test_sending_without_credentials_fails_clearly(auth_client, monkeypatch):
    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("hello"))
    monkeypatch.setattr(config_module.settings, "whatsapp_access_token", "")

    db = _db()
    try:
        conversation = db.query(WhatsAppConversation).one()
        with pytest.raises(WhatsAppError, match="isn't configured"):
            await send_message(db, conversation, "hi")
    finally:
        db.close()


# --- auto reply ---


def test_ai_replies_when_enabled(auth_client, monkeypatch):
    ai = StubAI()
    _configure(monkeypatch, ai)
    _stub_send_ok(monkeypatch)
    auth_client.patch("/api/v1/automation/settings", json={"whatsapp_ai_enabled": True})

    resp = _post_webhook(auth_client, _inbound_payload("how many sets should i do?"))
    assert resp.json()["whatsapp_replies"] == 1

    conversation = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    thread = auth_client.get(f"/api/v1/whatsapp/conversations/{conversation['id']}").json()
    outbound = [m for m in thread["messages"] if m["direction"] == "outbound"]
    assert len(outbound) == 1
    assert outbound[0]["is_ai_generated"] is True
    assert outbound[0]["status"] == "sent"


def test_ai_stays_silent_when_disabled(auth_client, monkeypatch):
    """Default is off, matching the approval gate everywhere else in this app."""

    _configure(monkeypatch, StubAI())
    _stub_send_ok(monkeypatch)

    resp = _post_webhook(auth_client, _inbound_payload("how many sets?"))
    assert resp.json()["whatsapp_replies"] == 0


def test_ai_hands_off_instead_of_closing_the_sale(auth_client, monkeypatch):
    """The moment someone asks to buy, the bot stops and the human is alerted.
    Automating the close is where this starts costing sales."""

    _configure(monkeypatch, StubAI())
    _stub_send_ok(monkeypatch)
    auth_client.patch("/api/v1/automation/settings", json={"whatsapp_ai_enabled": True})

    resp = _post_webhook(auth_client, _inbound_payload("what is the price? i want to join"))
    assert resp.json()["whatsapp_replies"] == 0

    conversation = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    assert conversation["ai_enabled"] is False
    assert conversation["handed_off_at"] is not None

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any("WhatsApp" in n["title"] for n in notifications if n["type"] == "hot_lead")


def test_ai_prompt_forbids_inventing_claims(auth_client, monkeypatch):
    ai = StubAI()
    _configure(monkeypatch, ai)
    _stub_send_ok(monkeypatch)
    auth_client.patch("/api/v1/automation/settings", json={"whatsapp_ai_enabled": True})

    _post_webhook(auth_client, _inbound_payload("is creatine safe?"))
    assert "NEVER invent a statistic" in ai.last_system
    assert "NEVER diagnose" in ai.last_system


def test_hinglish_setting_reaches_the_whatsapp_prompt(auth_client, monkeypatch):
    ai = StubAI()
    _configure(monkeypatch, ai)
    _stub_send_ok(monkeypatch)
    auth_client.patch(
        "/api/v1/automation/settings", json={"whatsapp_ai_enabled": True, "reply_language": "hinglish"}
    )

    _post_webhook(auth_client, _inbound_payload("kaise start karu?"))
    assert "Roman" in ai.last_system


def test_missing_ai_key_leaves_the_message_unanswered_not_broken(auth_client, monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(config_module.settings, "openai_api_key", "")
    monkeypatch.setattr(config_module.settings, "anthropic_api_key", "")
    monkeypatch.setattr(config_module.settings, "gemini_api_key", "")
    auth_client.patch("/api/v1/automation/settings", json={"whatsapp_ai_enabled": True})

    resp = _post_webhook(auth_client, _inbound_payload("hello there"))
    assert resp.status_code == 200
    assert resp.json()["whatsapp_replies"] == 0
    # The message is still captured — only the reply is missing.
    assert len(auth_client.get("/api/v1/whatsapp/conversations").json()) == 1


# --- manual control ---


def test_replying_by_hand_hands_the_conversation_off(auth_client, monkeypatch):
    _configure(monkeypatch)
    _stub_send_ok(monkeypatch)
    auth_client.patch("/api/v1/automation/settings", json={"whatsapp_ai_enabled": True})
    _post_webhook(auth_client, _inbound_payload("hello"))

    conversation = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    sent = auth_client.post(
        f"/api/v1/whatsapp/conversations/{conversation['id']}/send", json={"body": "Hi Priya!"}
    )
    assert sent.status_code == 200
    assert sent.json()["is_ai_generated"] is False

    after = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    assert after["ai_enabled"] is False


def test_draft_returns_a_suggestion_without_sending(auth_client, monkeypatch):
    _configure(monkeypatch, StubAI("Try three sets of ten."))
    _post_webhook(auth_client, _inbound_payload("how many sets?"))

    conversation = auth_client.get("/api/v1/whatsapp/conversations").json()[0]
    draft = auth_client.post(f"/api/v1/whatsapp/conversations/{conversation['id']}/draft")
    assert draft.status_code == 200
    assert draft.json()["body"] == "Try three sets of ten."

    thread = auth_client.get(f"/api/v1/whatsapp/conversations/{conversation['id']}").json()
    assert not [m for m in thread["messages"] if m["direction"] == "outbound"]


def test_conversations_are_private(auth_client, second_auth_client, monkeypatch):
    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("hello"))
    conversation = auth_client.get("/api/v1/whatsapp/conversations").json()[0]

    assert second_auth_client.get("/api/v1/whatsapp/conversations").json() == []
    assert second_auth_client.get(f"/api/v1/whatsapp/conversations/{conversation['id']}").status_code == 403


def test_whatsapp_endpoints_require_auth(client):
    assert client.get("/api/v1/whatsapp/conversations").status_code == 401


def test_lead_survives_conversation_lookup(auth_client, monkeypatch):
    """The conversation points at a lead so the CRM and the inbox agree on who
    this person is."""

    _configure(monkeypatch)
    _post_webhook(auth_client, _inbound_payload("hello"))

    db = _db()
    try:
        conversation = find_conversation(db, db.query(Lead).one().owner_id, "919812345678")
        assert conversation is not None
        assert conversation.lead_id == db.query(Lead).one().id
    finally:
        db.close()
