from datetime import datetime, timedelta, timezone

import pytest

from app.database import get_db
from app.main import app
from app.services.scheduler_service import publish_due_posts


def test_create_draft_post(auth_client):
    resp = auth_client.post("/api/v1/posts", json={"platform": "instagram", "format": "reel", "caption": "Hello world"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


def test_create_scheduled_post_sets_status(auth_client):
    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = auth_client.post(
        "/api/v1/posts",
        json={"platform": "youtube", "format": "video", "caption": "Launch", "scheduled_at": scheduled_at},
    )
    assert resp.json()["status"] == "scheduled"


def test_schedule_endpoint_updates_post(auth_client):
    post = auth_client.post("/api/v1/posts", json={"platform": "linkedin", "format": "post", "caption": "Draft"}).json()
    scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    resp = auth_client.post(f"/api/v1/posts/{post['id']}/schedule", params={"scheduled_at": scheduled_at})
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_publish_due_posts_publishes_and_notifies(auth_client):
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    post = auth_client.post(
        "/api/v1/posts",
        json={"platform": "facebook", "format": "post", "caption": "Due now", "scheduled_at": past},
    ).json()
    assert post["status"] == "scheduled"

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        count = await publish_due_posts(db)
    finally:
        db.close()
    assert count == 1

    fetched = auth_client.get(f"/api/v1/posts/{post['id']}").json()
    assert fetched["status"] == "published"
    assert fetched["external_post_id"] is not None

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "post_published" for n in notifications)
