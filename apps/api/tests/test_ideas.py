"""Tests for the daily content idea.

The two properties that make this a plan rather than a slot machine: the pick is
stable within a day, and used ideas rotate to the back instead of resurfacing
while fresh ones sit untouched.
"""

from datetime import date, datetime, timedelta, timezone

from app.database import get_db
from app.main import app
from app.models.content_idea import ContentIdea
from app.services.idea_service import get_todays_idea


def _db():
    return next(app.dependency_overrides[get_db]())


def _me(auth_client) -> str:
    return auth_client.get("/api/v1/auth/me").json()["id"]


def test_bank_is_seeded_on_first_read(auth_client):
    ideas = auth_client.get("/api/v1/content-ideas").json()
    assert len(ideas) >= 10
    assert all(idea["source"] == "seed" for idea in ideas)
    # Specific lived problems, not categories.
    assert any("nine hours" in idea["problem"] for idea in ideas)


def test_seeding_happens_only_once(auth_client):
    first = auth_client.get("/api/v1/content-ideas").json()
    second = auth_client.get("/api/v1/content-ideas").json()
    assert len(first) == len(second)


def test_todays_idea_is_returned_with_a_reason(auth_client):
    body = auth_client.get("/api/v1/content-ideas/today").json()
    assert body["idea"] is not None
    assert body["idea"]["problem"]
    assert body["reason"]
    assert body["total_active"] >= 10


def test_todays_idea_is_stable_across_calls(auth_client):
    """A suggestion that changes every refresh isn't a plan."""

    first = auth_client.get("/api/v1/content-ideas/today").json()["idea"]["id"]
    for _ in range(4):
        assert auth_client.get("/api/v1/content-ideas/today").json()["idea"]["id"] == first


def test_different_days_can_give_different_ideas(auth_client):
    """Same bank, different date — the rotation must actually move."""

    user_id = _me(auth_client)
    db = _db()
    try:
        from app.models.user import User

        user = db.get(User, user_id)
        picks = {get_todays_idea(db, user, today=date(2026, 1, 1) + timedelta(days=n)).idea.id for n in range(10)}
    finally:
        db.close()
    assert len(picks) > 1


def test_marking_used_increments_and_timestamps(auth_client):
    idea = auth_client.get("/api/v1/content-ideas/today").json()["idea"]
    assert idea["times_used"] == 0

    used = auth_client.post(f"/api/v1/content-ideas/{idea['id']}/used").json()
    assert used["times_used"] == 1
    assert used["last_used_at"] is not None


def test_recently_used_ideas_drop_out_of_the_rotation(auth_client):
    """A topic covered yesterday shouldn't come back while a dozen untouched ones
    are waiting."""

    ideas = auth_client.get("/api/v1/content-ideas").json()
    for idea in ideas[:5]:
        auth_client.post(f"/api/v1/content-ideas/{idea['id']}/used")

    used_ids = {idea["id"] for idea in ideas[:5]}
    today = auth_client.get("/api/v1/content-ideas/today").json()["idea"]["id"]
    assert today not in used_ids


def test_everything_used_still_returns_a_suggestion(auth_client):
    """A stale suggestion beats no suggestion — the page must never be empty."""

    auth_client.get("/api/v1/content-ideas")  # seed the bank before mutating it

    db = _db()
    try:
        recently = datetime.now(timezone.utc) - timedelta(days=1)
        for idea in db.query(ContentIdea).all():
            idea.times_used = 3
            idea.last_used_at = recently
        db.commit()
    finally:
        db.close()

    body = auth_client.get("/api/v1/content-ideas/today").json()
    assert body["idea"] is not None
    assert "last used" in body["reason"].lower()


def test_deactivated_ideas_are_never_suggested(auth_client):
    ideas = auth_client.get("/api/v1/content-ideas").json()
    for idea in ideas[1:]:
        auth_client.patch(f"/api/v1/content-ideas/{idea['id']}", json={"is_active": False})

    body = auth_client.get("/api/v1/content-ideas/today").json()
    assert body["idea"]["id"] == ideas[0]["id"]
    assert body["total_active"] == 1


def test_no_active_ideas_returns_none_not_an_error(auth_client):
    for idea in auth_client.get("/api/v1/content-ideas").json():
        auth_client.patch(f"/api/v1/content-ideas/{idea['id']}", json={"is_active": False})

    body = auth_client.get("/api/v1/content-ideas/today").json()
    assert body["idea"] is None
    assert body["total_active"] == 0
    assert "Add one" in body["reason"]


def test_custom_idea_gets_the_format_matching_its_goal(auth_client):
    """Leads want Stories — the app fills that in so the user doesn't have to
    remember the mapping."""

    created = auth_client.post(
        "/api/v1/content-ideas",
        json={"problem": "Cannot stop snacking during work calls", "suggested_goal": "leads"},
    ).json()
    assert created["suggested_format"] == "story"
    assert created["source"] == "custom"


def test_explicit_format_is_respected(auth_client):
    created = auth_client.post(
        "/api/v1/content-ideas",
        json={"problem": "A problem I want as a carousel", "suggested_goal": "leads", "suggested_format": "carousel"},
    ).json()
    assert created["suggested_format"] == "carousel"


def test_idea_can_be_deleted(auth_client):
    idea = auth_client.get("/api/v1/content-ideas").json()[0]
    assert auth_client.delete(f"/api/v1/content-ideas/{idea['id']}").status_code == 204
    assert all(i["id"] != idea["id"] for i in auth_client.get("/api/v1/content-ideas").json())


def test_ideas_are_private_to_their_owner(auth_client, second_auth_client):
    idea = auth_client.get("/api/v1/content-ideas").json()[0]
    assert second_auth_client.patch(
        f"/api/v1/content-ideas/{idea['id']}", json={"is_active": False}
    ).status_code == 403


def test_command_center_carries_todays_idea(auth_client):
    body = auth_client.get("/api/v1/dashboard/command-center").json()
    assert body["todays_idea"]["idea"] is not None
    assert body["todays_idea"]["idea"]["problem"]


def test_ideas_require_auth(client):
    assert client.get("/api/v1/content-ideas/today").status_code == 401
