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


def _create_due_post(auth_client, platform: str = "youtube") -> dict:
    """Uses a platform that falls back to LogPublisher on purpose: Instagram,
    Facebook and Threads now make real network calls, which must never happen in
    the test suite."""

    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    post = auth_client.post(
        "/api/v1/posts",
        json={"platform": platform, "format": "post", "caption": "Due now", "scheduled_at": past},
    ).json()
    assert post["status"] == "scheduled"
    return post


@pytest.mark.asyncio
async def test_due_post_is_held_for_approval_by_default(auth_client):
    """Auto-publish defaults to off, so a due post must drop back to DRAFT and wait
    for a human rather than going out on its own."""

    post = _create_due_post(auth_client)

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        published = await publish_due_posts(db)
    finally:
        db.close()
    assert published == 0

    fetched = auth_client.get(f"/api/v1/posts/{post['id']}").json()
    assert fetched["status"] == "draft"
    assert fetched["external_post_id"] is None

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any("approval" in n["title"] for n in notifications)


@pytest.mark.asyncio
async def test_due_post_publishes_when_auto_publish_enabled(auth_client):
    auth_client.patch("/api/v1/automation/settings", json={"auto_publish": {"youtube": True}})
    post = _create_due_post(auth_client)

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        published = await publish_due_posts(db)
    finally:
        db.close()
    assert published == 1

    fetched = auth_client.get(f"/api/v1/posts/{post['id']}").json()
    assert fetched["status"] == "published"
    assert fetched["external_post_id"] is not None

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "post_published" for n in notifications)


def test_publish_now_endpoint_publishes_a_draft(auth_client):
    """The approval button: publishes immediately regardless of the auto-publish
    setting, because the human just said yes."""

    post = auth_client.post(
        "/api/v1/posts", json={"platform": "youtube", "format": "post", "caption": "Approve me"}
    ).json()
    assert post["status"] == "draft"

    resp = auth_client.post(f"/api/v1/posts/{post['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"
    assert resp.json()["external_post_id"] is not None


def test_publish_now_rejects_already_published_post(auth_client):
    post = auth_client.post(
        "/api/v1/posts", json={"platform": "youtube", "format": "post", "caption": "Once only"}
    ).json()
    auth_client.post(f"/api/v1/posts/{post['id']}/publish")
    again = auth_client.post(f"/api/v1/posts/{post['id']}/publish")
    assert again.status_code == 409
