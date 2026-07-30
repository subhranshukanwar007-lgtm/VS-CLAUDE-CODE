from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.main import app
from app.models.lead import Lead
from app.services.intent_service import score_lead_fast


def _score_all():
    db = next(app.dependency_overrides[get_db]())
    try:
        for lead in db.query(Lead).all():
            score_lead_fast(db, lead)
    finally:
        db.close()


def test_command_center_is_empty_but_valid_for_a_new_account(auth_client):
    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["hot_leads"] == []
    assert body["needs_approval"] == []
    assert body["upcoming"] == []
    assert body["money"]["won_deals"] == 0
    assert body["auto_publish"] == {}


def test_hot_leads_appear_ranked_above_warm(auth_client):
    warm = auth_client.post("/api/v1/leads", json={"full_name": "Warm Person"}).json()
    hot = auth_client.post("/api/v1/leads", json={"full_name": "Hot Person"}).json()
    auth_client.post("/api/v1/notes", json={"lead_id": warm["id"], "body": "how do i stretch my back"})
    auth_client.post("/api/v1/notes", json={"lead_id": hot["id"], "body": "whats the price of the program"})
    _score_all()

    body = auth_client.get("/api/v1/dashboard/command-center").json()
    names = [lead["full_name"] for lead in body["hot_leads"]]
    assert names == ["Hot Person", "Warm Person"]
    assert body["hot_leads"][0]["intent"] == "hot"
    assert body["hot_leads"][0]["intent_reason"]


def test_cold_leads_are_not_surfaced(auth_client):
    cold = auth_client.post("/api/v1/leads", json={"full_name": "Cold Person"}).json()
    auth_client.post("/api/v1/notes", json={"lead_id": cold["id"], "body": "nice one bro"})
    _score_all()

    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["hot_leads"] == []


def test_drafts_show_up_as_needing_approval(auth_client):
    auth_client.post("/api/v1/posts", json={"platform": "instagram", "format": "reel", "caption": "A draft"})
    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert len(body["needs_approval"]) == 1
    assert body["needs_approval"][0]["caption"] == "A draft"
    assert body["needs_approval"][0]["is_overdue"] is False
    # Instagram has a real publisher, so the UI can offer a working Publish button.
    assert body["needs_approval"][0]["can_publish"] is True


def test_overdue_draft_is_flagged(auth_client):
    """A post whose time passed while auto-publish was off is the one actually
    blocking, so it's marked distinctly from a draft with no date."""

    past = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    post = auth_client.post(
        "/api/v1/posts", json={"platform": "instagram", "format": "reel", "caption": "Late", "scheduled_at": past}
    ).json()
    auth_client.patch(f"/api/v1/posts/{post['id']}", json={"status": "draft"})

    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["needs_approval"][0]["is_overdue"] is True


def test_platform_without_a_real_publisher_is_marked(auth_client):
    """X isn't wired up, so the UI must not offer a Publish button that would
    silently only log it."""

    auth_client.post("/api/v1/posts", json={"platform": "x", "format": "post", "caption": "Tweet"})
    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["needs_approval"][0]["can_publish"] is False


def test_scheduled_posts_appear_as_upcoming(auth_client):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    auth_client.post(
        "/api/v1/posts",
        json={"platform": "threads", "format": "post", "caption": "Tomorrow", "scheduled_at": future},
    )
    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert len(body["upcoming"]) == 1
    assert body["upcoming"][0]["status"] == "scheduled"
    assert body["needs_approval"] == []


def test_money_reflects_real_deals(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Payer"}).json()
    won = auth_client.post(
        "/api/v1/deals", json={"lead_id": lead["id"], "title": "Program", "value": 25000, "currency": "INR"}
    ).json()
    auth_client.patch(f"/api/v1/deals/{won['id']}", json={"status": "won"})
    auth_client.post(
        "/api/v1/deals", json={"lead_id": lead["id"], "title": "Upsell", "value": 5000, "currency": "INR"}
    )

    money = auth_client.get("/api/v1/dashboard/command-center").json()["money"]
    assert money["won_deals"] == 1
    assert money["won_value"] == 25000
    assert money["open_deals"] == 1
    assert money["open_pipeline_value"] == 5000


def test_breakdowns_group_by_source_and_country(auth_client):
    auth_client.post("/api/v1/leads", json={"full_name": "A", "source": "instagram", "country": "US"})
    auth_client.post("/api/v1/leads", json={"full_name": "B", "source": "instagram", "country": "IN"})
    auth_client.post("/api/v1/leads", json={"full_name": "C", "source": "threads", "country": "US"})

    body = auth_client.get("/api/v1/dashboard/command-center").json()
    by_source = {row["label"]: row["count"] for row in body["leads_by_source"]}
    by_country = {row["label"]: row["count"] for row in body["leads_by_country"]}
    assert by_source == {"instagram": 2, "threads": 1}
    assert by_country == {"US": 2, "IN": 1}


def test_unread_notification_count_is_reported(auth_client):
    auth_client.post("/api/v1/leads", json={"full_name": "Triggers a notification"})
    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["unread_notifications"] >= 1


def test_command_center_requires_auth(client):
    assert client.get("/api/v1/dashboard/command-center").status_code == 401


def test_command_center_is_scoped_to_the_owner(auth_client, second_auth_client):
    auth_client.post("/api/v1/posts", json={"platform": "instagram", "format": "reel", "caption": "Mine"})
    body = second_auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["needs_approval"] == []
