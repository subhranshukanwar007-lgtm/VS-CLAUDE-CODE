from datetime import datetime, timedelta, timezone

import app.services.followup_service as followup_service
from app.database import get_db
from app.main import app
from app.models.lead import Lead
from app.services.ai.base import AIProvider


class _FakeProvider(AIProvider):
    name = "openai"
    model = "fake-model"

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        return "Hey! Just checking in — still interested in moving forward?"


def _db():
    return next(app.dependency_overrides[get_db]())


def _backdate_lead(lead_id: str, days: int) -> None:
    db = _db()
    try:
        lead = db.get(Lead, lead_id)
        stale_time = datetime.now(timezone.utc) - timedelta(days=days)
        db.query(Lead).filter(Lead.id == lead.id).update({"updated_at": stale_time, "created_at": stale_time})
        db.commit()
    finally:
        db.close()


def test_manual_follow_up_without_provider_returns_503(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Quiet Lead", "source": "manual"}).json()
    resp = auth_client.post(f"/api/v1/leads/{lead['id']}/follow-up")
    assert resp.status_code == 503


def test_manual_follow_up_creates_task_and_notification(auth_client, monkeypatch):
    monkeypatch.setattr(followup_service, "get_provider", lambda kind=None: _FakeProvider())

    lead = auth_client.post("/api/v1/leads", json={"full_name": "Manual Lead", "source": "manual"}).json()
    resp = auth_client.post(f"/api/v1/leads/{lead['id']}/follow-up")
    assert resp.status_code == 200
    body = resp.json()
    assert "checking in" in body["generation"]["result"]
    assert body["task"]["lead_id"] == lead["id"]
    assert body["task"]["title"] == "Follow up with Manual Lead"

    updated_lead = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert updated_lead["last_follow_up_at"] is not None

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "follow_up_suggested" for n in notifications)

    tasks = auth_client.get("/api/v1/tasks").json()
    assert any(t["lead_id"] == lead["id"] for t in tasks)


def test_fresh_lead_is_not_stale(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Brand New Lead", "source": "manual"}).json()
    fetched = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert fetched["is_stale"] is False


def test_quiet_lead_becomes_stale_after_threshold(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Old Lead", "source": "manual"}).json()
    _backdate_lead(lead["id"], days=10)

    fetched = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert fetched["is_stale"] is True


def test_customer_status_lead_never_stale(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Existing Customer", "source": "manual"}).json()
    auth_client.patch(f"/api/v1/leads/{lead['id']}", json={"status": "customer"})
    _backdate_lead(lead["id"], days=30)

    fetched = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert fetched["is_stale"] is False


def test_disabling_follow_up_days_clears_staleness(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Disabled Lead", "source": "manual"}).json()
    _backdate_lead(lead["id"], days=30)
    auth_client.patch("/api/v1/users/me", json={"follow_up_days": 0})

    fetched = auth_client.get(f"/api/v1/leads/{lead['id']}").json()
    assert fetched["is_stale"] is False


async def test_run_follow_up_automation_triggers_and_is_idempotent_within_window(auth_client, monkeypatch):
    monkeypatch.setattr(followup_service, "get_provider", lambda kind=None: _FakeProvider())

    lead = auth_client.post("/api/v1/leads", json={"full_name": "Automation Lead", "source": "manual"}).json()
    _backdate_lead(lead["id"], days=10)

    db = _db()
    try:
        first_run = await followup_service.run_follow_up_automation(db)
        assert first_run == 1

        second_run = await followup_service.run_follow_up_automation(db)
        assert second_run == 0
    finally:
        db.close()

    tasks = auth_client.get("/api/v1/tasks").json()
    matching = [t for t in tasks if t["lead_id"] == lead["id"]]
    assert len(matching) == 1


async def test_run_follow_up_automation_skips_when_provider_unconfigured(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "No Key Lead", "source": "manual"}).json()
    _backdate_lead(lead["id"], days=10)

    db = _db()
    try:
        count = await followup_service.run_follow_up_automation(db)
    finally:
        db.close()
    assert count == 0
