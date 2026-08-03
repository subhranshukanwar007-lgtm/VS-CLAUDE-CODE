def test_create_list_delete_social_account(auth_client):
    created = auth_client.post(
        "/api/v1/social-accounts",
        json={"platform": "instagram", "handle": "@myhandle", "external_account_id": "1784567890"},
    )
    assert created.status_code == 201
    account = created.json()
    assert account["handle"] == "@myhandle"
    assert account["external_account_id"] == "1784567890"

    listed = auth_client.get("/api/v1/social-accounts").json()
    assert any(a["id"] == account["id"] for a in listed)

    assert auth_client.delete(f"/api/v1/social-accounts/{account['id']}").status_code == 204
    listed_after = auth_client.get("/api/v1/social-accounts").json()
    assert not any(a["id"] == account["id"] for a in listed_after)


def test_social_account_requires_auth(client):
    resp = client.get("/api/v1/social-accounts")
    assert resp.status_code == 401
