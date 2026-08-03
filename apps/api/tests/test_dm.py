"""Comment -> auto-DM.

The behaviour worth guarding here is not "does it send" — it is everything
around the send, because Meta permits exactly one private reply per comment and
retries webhooks it thinks failed. A duplicate here is not a duplicate row, it
is a real person getting DM'd twice by a bot.
"""

import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

import app.config as config_module
from app.models.private_reply import PrivateReply, PrivateReplyStatus
from app.services import dm_service
from app.services.dm_service import matches_trigger, render_message, send_pending


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _comment_payload(account_id: str, comment_id: str, text: str, user_id: str = "u1") -> bytes:
    return json.dumps(
        {
            "entry": [
                {
                    "id": account_id,
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": comment_id,
                                "text": text,
                                "from": {"id": user_id, "username": "curious_user"},
                            },
                        }
                    ],
                }
            ]
        }
    ).encode()


@pytest.fixture
def wired(auth_client, monkeypatch):
    """An Instagram account connected, auto-DM on, keyword 'plan'."""

    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@myhandle", "external_account_id": "1784567890"},
    ).json()
    auth_client.patch(
        "/api/v1/automation/settings",
        json={
            "dm_enabled": True,
            "dm_trigger_keywords": "plan, guide",
            "dm_template": "Hey {name}! Yeh raha plan: {link}",
            "dm_link": "https://example.com/plan",
        },
    )
    return account


def _deliver(auth_client, account, comment_id: str, text: str, user_id: str = "u1"):
    body = _comment_payload(account["external_account_id"], comment_id, text, user_id)
    return auth_client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": _sign("shh", body)},
    )


# --- keyword matching ----------------------------------------------------


def test_trigger_matches_word_not_substring():
    """'plan' must catch someone asking for a plan and ignore someone typing
    'planet'. Substring matching is the obvious implementation and it DMs people
    who never asked."""

    assert matches_trigger("PLAN", ["plan"]) is True
    assert matches_trigger("send me the plans bhai", ["plan"]) is True
    assert matches_trigger("Plan?", ["plan"]) is True
    assert matches_trigger("best planet gym", ["plan"]) is False
    assert matches_trigger("nice explanation", ["plan"]) is False


def test_trigger_with_no_keywords_matches_everything():
    """Empty keywords means "DM everyone who comments" — a real choice. The off
    switch is dm_enabled, not an empty list."""

    assert matches_trigger("literally anything", []) is True


def test_trigger_matches_any_of_several_keywords():
    assert matches_trigger("send the guide", ["plan", "guide"]) is True
    assert matches_trigger("send the thing", ["plan", "guide"]) is False


# --- message rendering ---------------------------------------------------


class _Setting:
    def __init__(self, template: str, link: str | None = None):
        self.dm_template = template
        self.dm_link = link


def test_render_fills_name_and_link():
    setting = _Setting("Hi {name}, here: {link}", "https://example.com/x")
    assert render_message(setting, "raj") == "Hi raj, here: https://example.com/x"


def test_render_falls_back_when_username_missing():
    assert render_message(_Setting("Hi {name}"), "") == "Hi there"


def test_render_leaves_unknown_placeholder_literal():
    """A user-written template is not a format string. '{today}' must survive as
    text, not raise KeyError and kill the DM."""

    assert render_message(_Setting("50% off {today}"), "raj") == "50% off {today}"


def test_render_truncates_runaway_template():
    long_link = "https://example.com/" + "a" * 5000
    rendered = render_message(_Setting("{link}", long_link), "raj")
    assert len(rendered) == dm_service.MAX_MESSAGE_LENGTH


# --- queueing at webhook time -------------------------------------------


def test_matching_comment_is_queued_pending(auth_client, wired):
    _deliver(auth_client, wired, "c1", "bhai plan chahiye")

    queue = auth_client.get("/api/v1/automation/dm-queue").json()
    assert len(queue) == 1
    assert queue[0]["status"] == "pending"
    assert queue[0]["comment_id"] == "c1"
    assert queue[0]["recipient_username"] == "curious_user"
    # Rendered at queue time, so editing the template later cannot rewrite history.
    assert queue[0]["message"] == "Hey curious_user! Yeh raha plan: https://example.com/plan"


def test_non_matching_comment_is_recorded_as_skipped(auth_client, wired):
    """Skipped, not absent. Without the row, a redelivery after the user changes
    their keywords would DM someone who commented days ago."""

    _deliver(auth_client, wired, "c1", "nice video")

    queue = auth_client.get("/api/v1/automation/dm-queue").json()
    assert len(queue) == 1
    assert queue[0]["status"] == "skipped"
    assert queue[0]["message"] == ""


def test_comment_is_skipped_while_automation_is_off(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@myhandle", "external_account_id": "1784567890"},
    ).json()

    _deliver(auth_client, account, "c1", "plan bhejo")

    queue = auth_client.get("/api/v1/automation/dm-queue").json()
    assert [row["status"] for row in queue] == ["skipped"]


def test_redelivered_webhook_does_not_queue_twice(auth_client, wired):
    """Meta retries deliveries it thinks failed. The unique constraint on
    comment_id is what stops that from becoming a second DM."""

    _deliver(auth_client, wired, "c1", "plan chahiye")
    _deliver(auth_client, wired, "c1", "plan chahiye")

    queue = auth_client.get("/api/v1/automation/dm-queue").json()
    assert len(queue) == 1


def test_own_comment_is_never_queued(auth_client, wired):
    """Replying to yourself on your own post is the first thing that happens in
    testing, and it looks broken."""

    _deliver(auth_client, wired, "c1", "plan", user_id=wired["external_account_id"])

    assert auth_client.get("/api/v1/automation/dm-queue").json() == []


def test_lead_capture_still_works_when_dm_is_queued(auth_client, wired):
    _deliver(auth_client, wired, "c1", "plan chahiye")

    leads = auth_client.get("/api/v1/leads").json()
    assert [lead["full_name"] for lead in leads] == ["curious_user"]
    assert auth_client.get("/api/v1/automation/dm-queue").json()[0]["lead_id"] == leads[0]["id"]


# --- sending -------------------------------------------------------------


def test_send_marks_row_sent(auth_client, wired, db_session, monkeypatch):
    sent: list[tuple[str, str]] = []

    async def fake_send(account, comment_id, message):
        sent.append((comment_id, message))
        return "mid_1"

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    _deliver(auth_client, wired, "c1", "plan chahiye")

    counts = asyncio.run(send_pending(db_session))
    assert counts["sent"] == 1
    assert sent == [("c1", "Hey curious_user! Yeh raha plan: https://example.com/plan")]

    row = auth_client.get("/api/v1/automation/dm-queue").json()[0]
    assert row["status"] == "sent"
    assert row["sent_at"] is not None


def test_send_failure_keeps_metas_own_words(auth_client, wired, db_session, monkeypatch):
    async def fake_send(account, comment_id, message):
        raise dm_service.PrivateReplyError("(#10) Application does not have permission")

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    _deliver(auth_client, wired, "c1", "plan chahiye")

    counts = asyncio.run(send_pending(db_session))
    assert counts["failed"] == 1

    row = auth_client.get("/api/v1/automation/dm-queue").json()[0]
    assert row["status"] == "failed"
    assert "does not have permission" in row["error"]


def test_one_notification_per_batch_not_per_failure(auth_client, wired, db_session, monkeypatch):
    """A dead token fails every queued DM at once. Ten identical alerts would
    train the user to ignore the one that matters."""

    async def fake_send(account, comment_id, message):
        raise dm_service.PrivateReplyError("Error validating access token")

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    for i in range(3):
        _deliver(auth_client, wired, f"c{i}", "plan chahiye", user_id=f"u{i}")

    asyncio.run(send_pending(db_session))

    notifications = auth_client.get("/api/v1/notifications").json()
    dm_alerts = [n for n in notifications if n["title"] == "Auto-DM could not be sent"]
    assert len(dm_alerts) == 1


def test_expired_comment_is_failed_with_an_explanation(auth_client, wired, db_session, monkeypatch):
    async def fake_send(account, comment_id, message):  # pragma: no cover - must not run
        raise AssertionError("expired rows must not reach Meta")

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    _deliver(auth_client, wired, "c1", "plan chahiye")

    row = db_session.scalar(select(PrivateReply))
    row.created_at = datetime.now(UTC) - timedelta(days=8)
    db_session.commit()

    counts = asyncio.run(send_pending(db_session))
    assert counts["expired"] == 1

    refreshed = auth_client.get("/api/v1/automation/dm-queue").json()[0]
    assert refreshed["status"] == "failed"
    assert "7 days" in refreshed["error"]


def test_disconnected_account_fails_the_row_rather_than_hanging(auth_client, wired, db_session):
    _deliver(auth_client, wired, "c1", "plan chahiye")
    auth_client.delete(f"/api/v1/social-accounts/{wired['id']}")

    counts = asyncio.run(send_pending(db_session))
    assert counts["failed"] == 1

    row = auth_client.get("/api/v1/automation/dm-queue").json()[0]
    assert row["status"] == "failed"
    assert "instagram" in row["error"]


def test_skipped_rows_are_never_sent(auth_client, wired, db_session, monkeypatch):
    async def fake_send(account, comment_id, message):  # pragma: no cover - must not run
        raise AssertionError("skipped rows must not reach Meta")

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    _deliver(auth_client, wired, "c1", "nice video")

    assert asyncio.run(send_pending(db_session)) == {"sent": 0, "failed": 0, "expired": 0}


# --- preview -------------------------------------------------------------


def test_preview_sends_nothing_and_shows_the_exact_message(auth_client, wired):
    """Meta allows one private reply per comment, so there is no way to test on a
    real comment and then fix the wording. The rehearsal has to happen here."""

    resp = auth_client.post(
        "/api/v1/automation/dm-preview",
        json={"comment": "bhai plan chahiye", "username": "raj"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["would_send"] is True
    assert body["message"] == "Hey raj! Yeh raha plan: https://example.com/plan"

    assert auth_client.get("/api/v1/automation/dm-queue").json() == []


def test_preview_explains_why_it_would_not_send(auth_client, wired):
    body = auth_client.post(
        "/api/v1/automation/dm-preview", json={"comment": "great video", "username": "raj"}
    ).json()
    assert body["would_send"] is False
    assert "plan" in body["reason"]
    assert body["message"] is None


def test_preview_says_so_when_automation_is_off(auth_client):
    body = auth_client.post("/api/v1/automation/dm-preview", json={"comment": "plan"}).json()
    assert body["would_send"] is False
    assert "switched off" in body["reason"]


# --- queue API -----------------------------------------------------------


def test_queue_can_be_filtered_by_status(auth_client, wired):
    _deliver(auth_client, wired, "c1", "plan chahiye")
    _deliver(auth_client, wired, "c2", "nice video", user_id="u2")

    pending = auth_client.get("/api/v1/automation/dm-queue", params={"status": "pending"}).json()
    assert [row["comment_id"] for row in pending] == ["c1"]


def test_queue_summary_counts_by_status(auth_client, wired):
    _deliver(auth_client, wired, "c1", "plan chahiye")
    _deliver(auth_client, wired, "c2", "nice video", user_id="u2")

    summary = auth_client.get("/api/v1/automation/dm-queue/summary").json()
    assert summary == {"pending": 1, "sent": 0, "failed": 0, "skipped": 1}


def test_queue_is_per_user(auth_client, wired, second_auth_client):
    _deliver(auth_client, wired, "c1", "plan chahiye")
    assert second_auth_client.get("/api/v1/automation/dm-queue").json() == []


# --- retry ---------------------------------------------------------------


def test_failed_dm_can_be_retried(auth_client, wired, db_session, monkeypatch):
    async def fake_send(account, comment_id, message):
        raise dm_service.PrivateReplyError("temporary Meta outage")

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    _deliver(auth_client, wired, "c1", "plan chahiye")
    asyncio.run(send_pending(db_session))

    row_id = auth_client.get("/api/v1/automation/dm-queue").json()[0]["id"]
    resp = auth_client.post(f"/api/v1/automation/dm-queue/{row_id}/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["error"] is None


def test_sent_dm_cannot_be_retried(auth_client, wired, db_session, monkeypatch):
    """Meta permits one private reply per comment. A retry would fail anyway —
    worse, it would read to the user as a double-send."""

    async def fake_send(account, comment_id, message):
        return "mid_1"

    monkeypatch.setattr(dm_service, "send_private_reply", fake_send)
    _deliver(auth_client, wired, "c1", "plan chahiye")
    asyncio.run(send_pending(db_session))

    row_id = auth_client.get("/api/v1/automation/dm-queue").json()[0]["id"]
    resp = auth_client.post(f"/api/v1/automation/dm-queue/{row_id}/retry")
    assert resp.status_code == 409
    assert "one private reply per comment" in resp.json()["detail"]


def test_retry_of_another_users_dm_is_not_found(auth_client, wired, second_auth_client):
    _deliver(auth_client, wired, "c1", "plan chahiye")
    row_id = auth_client.get("/api/v1/automation/dm-queue").json()[0]["id"]

    assert second_auth_client.post(f"/api/v1/automation/dm-queue/{row_id}/retry").status_code == 404


def test_queue_requires_auth(client):
    assert client.get("/api/v1/automation/dm-queue").status_code == 401
