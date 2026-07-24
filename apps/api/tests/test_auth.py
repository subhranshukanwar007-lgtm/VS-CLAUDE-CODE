def test_register_first_user_becomes_owner(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "full_name": "A", "password": "supersecret123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["role"] == "owner"
    assert "access_token" in body["tokens"]


def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "full_name": "A", "password": "supersecret123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "full_name": "B", "password": "supersecret123"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": "b@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user(auth_client):
    resp = auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "owner@example.com"


def test_refresh_token_issues_new_access_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "c@example.com", "full_name": "C", "password": "supersecret123"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "c@example.com", "password": "supersecret123"})
    refresh_token = login.json()["tokens"]["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_second_registered_user_is_member(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "full_name": "First", "password": "supersecret123"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "full_name": "Second", "password": "supersecret123"},
    )
    assert resp.json()["user"]["role"] == "member"
