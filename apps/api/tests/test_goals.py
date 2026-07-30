"""Tests for content goals and lead attribution.

The question this feature answers is "which of my content actually produces
leads", so the tests pin down the attribution chain (comment webhook -> matched
post -> that post's goal) and the deliberate choices around it: attribution is
best-effort, unattributed leads are reported separately rather than hidden, and
the "best goal" is leads-per-post rather than raw lead count.
"""

import hashlib
import hmac
import json

import app.config as config_module


def _sign(body: bytes, secret: str = "shh") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _connect_account(auth_client) -> dict:
    return auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@me", "external_account_id": "17841400000000000"},
    ).json()


def _published_post(auth_client, goal: str, external_post_id: str, caption: str = "Post") -> dict:
    post = auth_client.post(
        "/api/v1/posts", json={"platform": "instagram", "format": "reel", "caption": caption, "goal": goal}
    ).json()
    auth_client.patch(
        f"/api/v1/posts/{post['id']}", json={"status": "published", "external_post_id": external_post_id}
    )
    return post


def _comment_webhook(auth_client, account: dict, media_id: str | None, user_id: str, text: str):
    value = {"id": f"c-{user_id}", "text": text, "from": {"id": user_id, "username": f"user_{user_id}"}}
    if media_id is not None:
        value["media"] = {"id": media_id}
    payload = {"entry": [{"id": account["external_account_id"], "changes": [{"field": "comments", "value": value}]}]}
    body = json.dumps(payload).encode()
    return auth_client.post(
        "/api/v1/webhooks/meta",
        content=body,
        headers={"content-type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )


# --- goal on posts ---


def test_post_defaults_to_reach_goal(auth_client):
    post = auth_client.post("/api/v1/posts", json={"platform": "instagram", "format": "reel"}).json()
    assert post["goal"] == "reach"


def test_post_goal_can_be_set_and_changed(auth_client):
    post = auth_client.post(
        "/api/v1/posts", json={"platform": "instagram", "format": "story", "goal": "leads"}
    ).json()
    assert post["goal"] == "leads"
    updated = auth_client.patch(f"/api/v1/posts/{post['id']}", json={"goal": "sales"}).json()
    assert updated["goal"] == "sales"


def test_recommendations_cover_every_goal(auth_client):
    recs = auth_client.get("/api/v1/goals/recommendations").json()
    assert {r["goal"] for r in recs} == {"reach", "leads", "sales", "trust", "saves"}
    by_goal = {r["goal"]: r for r in recs}
    # The mapping that makes this feature worth having: reach wants reels, leads
    # want stories.
    assert by_goal["reach"]["recommended_format"] == "reel"
    assert by_goal["leads"]["recommended_format"] == "story"
    assert by_goal["saves"]["recommended_format"] == "carousel"
    assert all(r["reason"] for r in recs)


# --- attribution ---


def test_comment_attributes_lead_to_the_post_that_earned_it(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)
    post = _published_post(auth_client, "leads", "ig-media-1")

    assert _comment_webhook(auth_client, account, "ig-media-1", "u1", "how much?").status_code == 200

    lead = next(lead for lead in auth_client.get("/api/v1/leads").json() if lead["full_name"] == "user_u1")
    assert lead["source_post_id"] == post["id"]


def test_comment_on_unknown_media_still_captures_the_lead(auth_client, monkeypatch):
    """Attribution is best-effort — failing to match a post must never cost you the
    lead itself."""

    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)

    assert _comment_webhook(auth_client, account, "media-we-never-published", "u2", "nice").status_code == 200

    lead = next(lead for lead in auth_client.get("/api/v1/leads").json() if lead["full_name"] == "user_u2")
    assert lead["source_post_id"] is None


def test_comment_without_media_field_still_captures_the_lead(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)

    assert _comment_webhook(auth_client, account, None, "u3", "love it").status_code == 200
    assert any(lead["full_name"] == "user_u3" for lead in auth_client.get("/api/v1/leads").json())


def test_attribution_is_not_rewritten_by_a_later_comment(auth_client, monkeypatch):
    """Credit goes to the post that first earned them, not the most recent one they
    happened to comment on."""

    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)
    first = _published_post(auth_client, "leads", "ig-media-1", caption="First")
    _published_post(auth_client, "reach", "ig-media-2", caption="Second")

    _comment_webhook(auth_client, account, "ig-media-1", "u1", "interesting")
    _comment_webhook(auth_client, account, "ig-media-2", "u1", "how much?")

    leads = [lead for lead in auth_client.get("/api/v1/leads").json() if lead["full_name"] == "user_u1"]
    assert len(leads) == 1
    assert leads[0]["source_post_id"] == first["id"]


def test_deleting_a_post_does_not_delete_the_leads_it_earned(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)
    post = _published_post(auth_client, "leads", "ig-media-1")
    _comment_webhook(auth_client, account, "ig-media-1", "u1", "how much?")

    assert auth_client.delete(f"/api/v1/posts/{post['id']}").status_code == 204

    lead = next(lead for lead in auth_client.get("/api/v1/leads").json() if lead["full_name"] == "user_u1")
    assert lead["source_post_id"] is None


# --- performance report ---


def test_performance_reports_every_goal_even_with_no_data(auth_client):
    report = auth_client.get("/api/v1/goals/performance").json()
    assert {row["goal"] for row in report["performance"]} == {"reach", "leads", "sales", "trust", "saves"}
    assert all(row["leads"] == 0 for row in report["performance"])
    assert report["best_goal"] is None


def test_performance_attributes_leads_to_the_right_goal(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)
    _published_post(auth_client, "leads", "story-1", caption="Story")
    _published_post(auth_client, "reach", "reel-1", caption="Reel")

    _comment_webhook(auth_client, account, "story-1", "u1", "how much?")
    _comment_webhook(auth_client, account, "story-1", "u2", "how do i join")
    _comment_webhook(auth_client, account, "reel-1", "u3", "nice video")

    report = auth_client.get("/api/v1/goals/performance").json()
    by_goal = {row["goal"]: row for row in report["performance"]}

    assert by_goal["leads"]["leads"] == 2
    assert by_goal["leads"]["hot_leads"] == 2
    assert by_goal["reach"]["leads"] == 1
    assert by_goal["reach"]["hot_leads"] == 0
    assert report["best_goal"] == "leads"


def test_best_goal_uses_leads_per_post_not_raw_count(auth_client, monkeypatch):
    """Otherwise whichever goal you simply posted most often always wins, which
    would be a measurement bug dressed up as insight."""

    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)

    # 3 reach posts -> 3 leads total (1.0 per post)
    for i in range(3):
        _published_post(auth_client, "reach", f"reel-{i}", caption=f"Reel {i}")
        _comment_webhook(auth_client, account, f"reel-{i}", f"r{i}", "nice")

    # 1 leads post -> 2 leads (2.0 per post)
    _published_post(auth_client, "leads", "story-1", caption="Story")
    _comment_webhook(auth_client, account, "story-1", "s1", "how much?")
    _comment_webhook(auth_client, account, "story-1", "s2", "price?")

    report = auth_client.get("/api/v1/goals/performance").json()
    by_goal = {row["goal"]: row for row in report["performance"]}
    assert by_goal["reach"]["leads"] == 3
    assert by_goal["leads"]["leads"] == 2
    assert by_goal["reach"]["leads_per_post"] == 1.0
    assert by_goal["leads"]["leads_per_post"] == 2.0
    # Fewer total leads, but better content.
    assert report["best_goal"] == "leads"


def test_manually_added_leads_are_reported_as_unattributed(auth_client):
    """Not hidden and not spread across goals — a lead with no source post is
    counted separately so the goal numbers stay honest."""

    auth_client.post("/api/v1/leads", json={"full_name": "Walked in"})
    report = auth_client.get("/api/v1/goals/performance").json()
    assert report["unattributed_leads"] == 1
    assert all(row["leads"] == 0 for row in report["performance"])


def test_won_deal_value_is_credited_to_the_goal(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "meta_app_secret", "shh")
    account = _connect_account(auth_client)
    _published_post(auth_client, "sales", "sales-1", caption="Sales post")
    _comment_webhook(auth_client, account, "sales-1", "u1", "how much?")

    lead = next(lead for lead in auth_client.get("/api/v1/leads").json() if lead["full_name"] == "user_u1")
    deal = auth_client.post(
        "/api/v1/deals", json={"lead_id": lead["id"], "title": "Program", "value": 25000, "currency": "INR"}
    ).json()
    auth_client.patch(f"/api/v1/deals/{deal['id']}", json={"status": "won"})

    report = auth_client.get("/api/v1/goals/performance").json()
    by_goal = {row["goal"]: row for row in report["performance"]}
    assert by_goal["sales"]["won_value"] == 25000
    assert by_goal["reach"]["won_value"] == 0


def test_unpublished_posts_are_not_counted(auth_client):
    """A draft hasn't had the chance to earn anything, so counting it would
    understate the goal's real leads-per-post."""

    auth_client.post("/api/v1/posts", json={"platform": "instagram", "format": "story", "goal": "leads"})
    report = auth_client.get("/api/v1/goals/performance").json()
    by_goal = {row["goal"]: row for row in report["performance"]}
    assert by_goal["leads"]["published_posts"] == 0


def test_goals_endpoints_require_auth(client):
    assert client.get("/api/v1/goals/performance").status_code == 401
