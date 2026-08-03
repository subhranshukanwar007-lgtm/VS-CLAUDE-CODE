"""Tests for buying-intent scoring.

`use_ai=False` throughout: the rule-based layer is what runs on the webhook path
and it must work with no AI key configured, so that's the behaviour worth pinning
down. The AI parser is tested directly rather than through a mocked provider.
"""

import json

import pytest

import app.config as config_module
from app.database import get_db
from app.main import app
from app.models.lead import Lead, LeadIntent
from app.services.intent_service import (
    _parse_ai_verdict,
    _rule_based_intent,
    score_lead,
    score_lead_fast,
)


def _db():
    return next(app.dependency_overrides[get_db]())


# --- rule layer ---


@pytest.mark.parametrize(
    "text",
    [
        "how much is the program?",
        "What's the PRICE?",
        "bhai kitna hai ye",
        "how do i join",
        "send me the link please",
        "I'm interested",
        "are slots available?",
        "what are the fees",
    ],
)
def test_buying_language_scores_hot(text):
    intent, reason = _rule_based_intent(text)
    assert intent == LeadIntent.HOT, f"{text!r} should be hot"
    assert reason


@pytest.mark.parametrize(
    "text",
    [
        "how do i fix my posture",
        "can you help me with my diet",
        "kaise karna hai ye exercise",
        "I'm struggling with sleep",
    ],
)
def test_questions_without_buying_signal_score_warm(text):
    intent, _ = _rule_based_intent(text)
    assert intent == LeadIntent.WARM


@pytest.mark.parametrize("text", ["love this", "great video bro", "🔥🔥🔥", "amazing"])
def test_compliments_score_cold(text):
    intent, _ = _rule_based_intent(text)
    assert intent == LeadIntent.COLD


def test_surprise_does_not_match_price():
    """Word-boundary matching: 'surprise' contains 'prise', not 'price', but this
    guards the class of substring false positive."""

    intent, _ = _rule_based_intent("what a surprise, enterprise level stuff")
    assert intent == LeadIntent.COLD


# --- AI verdict parsing ---


def test_parse_ai_verdict_reads_expected_format():
    parsed = _parse_ai_verdict("INTENT: hot\nREASON: asked what the program costs")
    assert parsed == (LeadIntent.HOT, "asked what the program costs")


def test_parse_ai_verdict_is_case_insensitive():
    parsed = _parse_ai_verdict("intent: WARM\nreason: general question")
    assert parsed is not None
    assert parsed[0] == LeadIntent.WARM


def test_parse_ai_verdict_returns_none_on_garbage():
    """A malformed model reply must not be allowed to downgrade a score."""

    assert _parse_ai_verdict("Sure! I'd be happy to help with that.") is None
    assert _parse_ai_verdict("") is None
    assert _parse_ai_verdict("INTENT: maybe\nREASON: unclear") is None


def test_parse_ai_verdict_tolerates_missing_reason():
    parsed = _parse_ai_verdict("INTENT: cold")
    assert parsed is not None
    assert parsed[0] == LeadIntent.COLD
    assert parsed[1]


# --- end to end through the API ---


def _make_lead_with_comment(auth_client, text: str, name: str = "Priya") -> dict:
    lead = auth_client.post("/api/v1/leads", json={"full_name": name, "source": "instagram"}).json()
    auth_client.post("/api/v1/notes", json={"lead_id": lead["id"], "body": text})
    return lead


def test_new_lead_starts_unknown(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Nobody"}).json()
    assert lead["intent"] == "unknown"
    assert lead["intent_scored_at"] is None


def test_hot_lead_scoring_notifies_owner(auth_client):
    lead = _make_lead_with_comment(auth_client, "how much does the 12 week program cost?")

    db = _db()
    try:
        score_lead_fast(db, db.get(Lead, lead["id"]))
    finally:
        db.close()

    fetched = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert fetched["intent"] == "hot"
    assert fetched["intent_reason"]
    assert fetched["intent_scored_at"] is not None

    notifications = auth_client.get("/api/v1/notifications").json()
    hot = [n for n in notifications if n["type"] == "hot_lead"]
    assert len(hot) == 1
    assert "Priya" in hot[0]["title"]


def test_hot_notification_fires_once_not_on_every_rescore(auth_client):
    lead = _make_lead_with_comment(auth_client, "whats the price?")

    db = _db()
    try:
        for _ in range(3):
            score_lead_fast(db, db.get(Lead, lead["id"]))
    finally:
        db.close()

    notifications = auth_client.get("/api/v1/notifications").json()
    assert len([n for n in notifications if n["type"] == "hot_lead"]) == 1


def test_score_is_never_downgraded(auth_client):
    """Someone who asked the price yesterday is still worth talking to today, even
    if their newest comment is just an emoji."""

    lead = _make_lead_with_comment(auth_client, "how much?")
    db = _db()
    try:
        score_lead_fast(db, db.get(Lead, lead["id"]))
    finally:
        db.close()
    assert auth_client.get(f"/api/v1/leads/{lead['id']}").json()["intent"] == "hot"

    auth_client.post("/api/v1/notes", json={"lead_id": lead["id"], "body": "🔥"})
    db = _db()
    try:
        score_lead_fast(db, db.get(Lead, lead["id"]))
    finally:
        db.close()
    assert auth_client.get(f"/api/v1/leads/{lead['id']}").json()["intent"] == "hot"


def test_lead_with_no_messages_is_left_unscored(auth_client):
    """Recording a confident "cold" with zero evidence would be worse than saying
    nothing."""

    lead = auth_client.post("/api/v1/leads", json={"full_name": "Silent"}).json()
    db = _db()
    try:
        score_lead_fast(db, db.get(Lead, lead["id"]))
    finally:
        db.close()
    fetched = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert fetched["intent"] == "unknown"
    assert fetched["intent_scored_at"] is None


@pytest.mark.asyncio
async def test_full_scoring_survives_missing_ai_key(auth_client, monkeypatch):
    """No AI key configured must degrade to the rule-based score, not fail."""

    monkeypatch.setattr(config_module.settings, "openai_api_key", "")
    monkeypatch.setattr(config_module.settings, "anthropic_api_key", "")
    monkeypatch.setattr(config_module.settings, "gemini_api_key", "")

    lead = _make_lead_with_comment(auth_client, "how do i join?")
    db = _db()
    try:
        await score_lead(db, db.get(Lead, lead["id"]))
    finally:
        db.close()

    assert auth_client.get(f"/api/v1/leads/{lead['id']}").json()["intent"] == "hot"


def test_leads_can_be_filtered_by_intent(auth_client):
    hot = _make_lead_with_comment(auth_client, "price please", name="Hot Lead")
    _make_lead_with_comment(auth_client, "nice video", name="Cold Lead")

    db = _db()
    try:
        for lead in db.query(Lead).all():
            score_lead_fast(db, lead)
    finally:
        db.close()

    hot_only = auth_client.get("/api/v1/leads", params={"intent": "hot"}).json()
    assert [lead["id"] for lead in hot_only] == [hot["id"]]


def test_score_intent_endpoint_requires_ownership(auth_client, second_auth_client):
    lead = _make_lead_with_comment(auth_client, "how much?")
    resp = second_auth_client.post(f"/api/v1/leads/{lead['id']}/score-intent")
    assert resp.status_code in (403, 404)


def test_webhook_comment_scores_intent_immediately(auth_client, monkeypatch):
    """The whole point: a buying question in a comment must reach the user as a hot
    alert without waiting for a background job."""

    import hashlib
    import hmac

    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@me", "external_account_id": "17841400000000000"},
    ).json()

    payload = {
        "entry": [
            {
                "id": account["external_account_id"],
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "c1",
                            "text": "how much for the program?",
                            "from": {"id": "u1", "username": "buyer_person"},
                        },
                    }
                ],
            }
        ]
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    resp = auth_client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": signature},
    )
    assert resp.status_code == 200

    leads = auth_client.get("/api/v1/leads").json()
    buyer = next(lead for lead in leads if lead["full_name"] == "buyer_person")
    assert buyer["intent"] == "hot"

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "hot_lead" and "buyer_person" in n["title"] for n in notifications)
