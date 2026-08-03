def test_settings_created_lazily_with_safe_defaults(auth_client):
    resp = auth_client.get("/api/v1/automation/settings")
    assert resp.status_code == 200
    body = resp.json()
    # Silence must mean "ask me", never "post it".
    assert body["auto_publish"] == {}
    assert body["dm_enabled"] is False
    assert body["threads_monitor_enabled"] is False
    assert body["reply_language"] == "english"
    assert "{link}" in body["dm_template"]


def test_settings_are_editable(auth_client):
    resp = auth_client.patch(
        "/api/v1/automation/settings",
        json={
            "auto_publish": {"instagram": True, "threads": False},
            "dm_enabled": True,
            "dm_trigger_keywords": "PLAN, guide ,START",
            "dm_link": "https://example.com/plan",
            "reply_language": "hinglish",
            "threads_keywords": "fat loss, protein",
            "posts_per_day": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["auto_publish"] == {"instagram": True, "threads": False}
    assert body["dm_enabled"] is True
    assert body["reply_language"] == "hinglish"
    assert body["posts_per_day"] == 3

    # Persisted, not just echoed back.
    assert auth_client.get("/api/v1/automation/settings").json()["reply_language"] == "hinglish"


def test_partial_update_leaves_other_fields_alone(auth_client):
    auth_client.patch("/api/v1/automation/settings", json={"posts_per_day": 5, "dm_enabled": True})
    auth_client.patch("/api/v1/automation/settings", json={"posts_per_day": 2})
    body = auth_client.get("/api/v1/automation/settings").json()
    assert body["posts_per_day"] == 2
    assert body["dm_enabled"] is True


def test_unknown_platform_key_is_rejected(auth_client):
    resp = auth_client.patch("/api/v1/automation/settings", json={"auto_publish": {"myspace": True}})
    assert resp.status_code == 422


def test_posts_per_day_bounds_enforced(auth_client):
    assert auth_client.patch("/api/v1/automation/settings", json={"posts_per_day": -1}).status_code == 422
    assert auth_client.patch("/api/v1/automation/settings", json={"posts_per_day": 999}).status_code == 422


def test_settings_require_auth(client):
    assert client.get("/api/v1/automation/settings").status_code == 401


def test_capabilities_report_what_actually_works(auth_client):
    caps = {c["platform"]: c for c in auth_client.get("/api/v1/automation/capabilities").json()}

    # Implemented publishers.
    assert caps["instagram"]["can_publish"] is True
    assert caps["facebook"]["can_publish"] is True
    assert caps["threads"]["can_publish"] is True

    # Not wired up — the UI must not offer these as working.
    assert caps["x"]["can_publish"] is False
    assert caps["tiktok"]["can_publish"] is False

    # Stories exist on Meta's photo/video surfaces but not on Threads.
    assert caps["instagram"]["supports_stories"] is True
    assert caps["facebook"]["supports_stories"] is True
    assert caps["threads"]["supports_stories"] is False
    assert "Stories" in caps["threads"]["note"]


def test_settings_are_per_user(auth_client, second_auth_client):
    auth_client.patch("/api/v1/automation/settings", json={"posts_per_day": 7})
    assert second_auth_client.get("/api/v1/automation/settings").json()["posts_per_day"] == 1
