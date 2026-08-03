"""Tests for follower-goal tracking.

The property that matters most: when there isn't enough history to measure a
growth rate, the endpoint returns nulls rather than a number. A fabricated ETA is
worse than no ETA, because it gets planned against — someone sees "100K by March"
and stops questioning their hooks.
"""

from datetime import date, timedelta

from app.database import get_db
from app.main import app
from app.models.metric import Metric, MetricKind
from app.models.post import Platform


def _seed_followers(user_id, points: list[tuple[int, float]]) -> None:
    """points: (days_ago, follower_count)."""

    db = next(app.dependency_overrides[get_db]())
    try:
        today = date.today()
        db.add_all(
            Metric(
                owner_id=user_id,
                platform=Platform.INSTAGRAM,
                kind=MetricKind.FOLLOWERS,
                value=value,
                recorded_on=today - timedelta(days=days_ago),
            )
            for days_ago, value in points
        )
        db.commit()
    finally:
        db.close()


def _me(auth_client) -> str:
    return auth_client.get("/api/v1/auth/me").json()["id"]


def _set_goal(auth_client, goal: int = 100000, days_out: int = 365) -> None:
    auth_client.patch(
        "/api/v1/automation/settings",
        json={
            "follower_goal": goal,
            "goal_deadline": (date.today() + timedelta(days=days_out)).isoformat(),
        },
    )


def test_no_goal_set_returns_empty_but_valid(auth_client):
    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["follower_goal"] is None
    assert body["remaining"] is None
    assert body["percent_complete"] is None
    assert body["has_enough_history"] is False


def test_goal_with_no_follower_history_gives_no_eta(auth_client):
    """The important case: a goal is set but nothing has been measured. The app
    must not invent a projection."""

    _set_goal(auth_client)
    body = auth_client.get("/api/v1/dashboard/growth-target").json()

    assert body["follower_goal"] == 100000
    assert body["remaining"] == 100000
    assert body["per_day_required"] is not None  # arithmetic from the deadline is fine
    assert body["per_day_actual"] is None  # measuring a rate is not
    assert body["projected_date"] is None
    assert body["on_pace"] is None
    assert body["has_enough_history"] is False


def test_too_little_history_still_gives_no_rate(auth_client):
    """Three days of data is noise, not a growth rate."""

    _seed_followers(_me(auth_client), [(3, 10000), (0, 10300)])
    _set_goal(auth_client)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["current_followers"] == 10300
    assert body["per_day_actual"] is None
    assert body["has_enough_history"] is False


def test_measured_rate_produces_a_projection(auth_client):
    _seed_followers(_me(auth_client), [(30, 10000), (0, 13000)])
    _set_goal(auth_client)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["current_followers"] == 13000
    assert body["followers_gained_30d"] == 3000
    assert body["per_day_actual"] == 100.0
    assert body["has_enough_history"] is True
    assert body["projected_date"] is not None


def test_on_pace_is_false_when_the_rate_is_short_of_the_deadline(auth_client):
    """100 a day against a 100K-in-a-year goal is roughly a third of what's needed,
    and the app has to say so rather than showing encouraging progress."""

    _seed_followers(_me(auth_client), [(30, 10000), (0, 13000)])
    _set_goal(auth_client, goal=100000, days_out=365)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["per_day_required"] > body["per_day_actual"]
    assert body["on_pace"] is False


def test_on_pace_is_true_when_the_rate_clears_the_bar(auth_client):
    _seed_followers(_me(auth_client), [(30, 10000), (0, 40000)])
    _set_goal(auth_client, goal=100000, days_out=365)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["on_pace"] is True


def test_flat_account_gets_no_projection(auth_client):
    """Zero growth means no honest ETA exists — dividing by it would produce either
    an absurd date or a crash."""

    _seed_followers(_me(auth_client), [(30, 10000), (0, 10000)])
    _set_goal(auth_client)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["per_day_actual"] == 0.0
    assert body["projected_date"] is None


def test_losing_followers_gets_no_projection(auth_client):
    _seed_followers(_me(auth_client), [(30, 12000), (0, 11000)])
    _set_goal(auth_client)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["per_day_actual"] < 0
    assert body["projected_date"] is None


def test_reached_goal_reports_zero_remaining(auth_client):
    _seed_followers(_me(auth_client), [(30, 90000), (0, 105000)])
    _set_goal(auth_client, goal=100000)

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["remaining"] == 0
    assert body["percent_complete"] > 100


def test_only_reels_count_toward_the_weekly_target(auth_client):
    """Reels are the only format Instagram pushes to non-followers, so a follower
    target is a reel target — a carousel doesn't count."""

    for fmt in ("reel", "reel", "carousel", "story"):
        post = auth_client.post(
            "/api/v1/posts", json={"platform": "instagram", "format": fmt, "caption": fmt}
        ).json()
        auth_client.patch(f"/api/v1/posts/{post['id']}", json={"status": "published"})

    body = auth_client.get("/api/v1/dashboard/growth-target").json()
    assert body["reels_this_week"] == 2
    assert body["reels_per_week_target"] == 5


def test_unpublished_reels_do_not_count(auth_client):
    auth_client.post("/api/v1/posts", json={"platform": "instagram", "format": "reel", "caption": "draft"})
    assert auth_client.get("/api/v1/dashboard/growth-target").json()["reels_this_week"] == 0


def test_goal_settings_are_editable(auth_client):
    resp = auth_client.patch(
        "/api/v1/automation/settings",
        json={"follower_goal": 100000, "goal_deadline": "2027-07-30", "reels_per_week_target": 7},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["follower_goal"] == 100000
    assert body["goal_deadline"] == "2027-07-30"
    assert body["reels_per_week_target"] == 7


def test_growth_target_requires_auth(client):
    assert client.get("/api/v1/dashboard/growth-target").status_code == 401
