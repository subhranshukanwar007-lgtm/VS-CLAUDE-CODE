import hashlib
import hmac
import json

import app.config as config_module


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_verification_success(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_webhook_verify_token", "my-verify-token")
    resp = client.get(
        "/api/v1/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.challenge": "12345", "hub.verify_token": "my-verify-token"},
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_verification_wrong_token_rejected(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_webhook_verify_token", "my-verify-token")
    resp = client.get(
        "/api/v1/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.challenge": "12345", "hub.verify_token": "wrong"},
    )
    assert resp.status_code == 403


def test_webhook_post_invalid_signature_rejected(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    body = json.dumps({"entry": []}).encode()
    resp = client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert resp.status_code == 403


def test_webhook_post_no_matching_account_is_noop(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    payload = {
        "entry": [
            {
                "id": "999999",
                "changes": [
                    {
                        "field": "comments",
                        "value": {"id": "c1", "text": "hi", "from": {"id": "u1", "username": "someone"}},
                    }
                ],
            }
        ]
    }
    body = json.dumps(payload).encode()
    resp = auth_client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": _sign("shh", body)},
    )
    assert resp.status_code == 200
    assert resp.json()["processed"] == 0


def test_webhook_comment_creates_lead(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")

    account = auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@myhandle", "external_account_id": "1784567890"},
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
                            "text": "How do I join?",
                            "from": {"id": "u1", "username": "curious_user"},
                        },
                    }
                ],
            }
        ]
    }
    body = json.dumps(payload).encode()
    resp = auth_client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": _sign("shh", body)},
    )
    assert resp.status_code == 200
    assert resp.json()["processed"] == 1

    leads = auth_client.get("/api/v1/leads").json()
    matching = [lead for lead in leads if lead["full_name"] == "curious_user"]
    assert len(matching) == 1
    assert matching[0]["source"] == "instagram"
    assert matching[0]["tags"] == "engagement"

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "lead_created" and "curious_user" in n["title"] for n in notifications)


def test_webhook_repeat_comment_deduped_to_same_lead(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")

    account = auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@myhandle", "external_account_id": "1784567890"},
    ).json()

    def make_payload(comment_id: str, text: str) -> bytes:
        payload = {
            "entry": [
                {
                    "id": account["external_account_id"],
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": comment_id,
                                "text": text,
                                "from": {"id": "u1", "username": "curious_user"},
                            },
                        }
                    ],
                }
            ]
        }
        return json.dumps(payload).encode()

    body1 = make_payload("c1", "First comment")
    auth_client.post(
        "/api/v1/webhooks/meta",
        content=body1,
        headers={"content-type": "application/json", "X-Hub-Signature-256": _sign("shh", body1)},
    )
    body2 = make_payload("c2", "Second comment")
    auth_client.post(
        "/api/v1/webhooks/meta",
        content=body2,
        headers={"content-type": "application/json", "X-Hub-Signature-256": _sign("shh", body2)},
    )

    leads = auth_client.get("/api/v1/leads").json()
    matching = [lead for lead in leads if lead["full_name"] == "curious_user"]
    assert len(matching) == 1

    notes = auth_client.get("/api/v1/notes", params={"lead_id": matching[0]["id"]}).json()
    assert len(notes) == 2
