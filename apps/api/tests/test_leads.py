def test_create_and_list_lead(auth_client):
    resp = auth_client.post("/api/v1/leads", json={"full_name": "Jane Doe", "source": "instagram"})
    assert resp.status_code == 201
    lead_id = resp.json()["id"]

    resp = auth_client.get("/api/v1/leads")
    assert resp.status_code == 200
    assert any(lead["id"] == lead_id for lead in resp.json())


def test_update_lead_status(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Prospect", "source": "manual"}).json()

    resp = auth_client.patch(f"/api/v1/leads/{lead['id']}", json={"status": "customer"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "customer"


def test_delete_lead(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "ToDelete", "source": "manual"}).json()
    assert auth_client.delete(f"/api/v1/leads/{lead['id']}").status_code == 204
    assert auth_client.get(f"/api/v1/leads/{lead['id']}").status_code == 404


def test_lead_creation_triggers_notification(auth_client):
    auth_client.post("/api/v1/leads", json={"full_name": "Notify Me", "source": "manual"})
    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "lead_created" for n in notifications)


def test_pipeline_stage_and_deal_flow(auth_client):
    stage = auth_client.post("/api/v1/pipeline-stages", json={"name": "Qualified", "order": 1}).json()
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Deal Lead", "source": "manual"}).json()

    deal = auth_client.post(
        "/api/v1/deals",
        json={"lead_id": lead["id"], "stage_id": stage["id"], "title": "Coaching package", "value": 999},
    ).json()
    assert deal["status"] == "open"

    won = auth_client.patch(f"/api/v1/deals/{deal['id']}", json={"status": "won"})
    assert won.status_code == 200
    assert won.json()["status"] == "won"

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "deal_won" for n in notifications)


def test_notes_on_lead(auth_client):
    lead = auth_client.post("/api/v1/leads", json={"full_name": "Note Lead", "source": "manual"}).json()
    note = auth_client.post("/api/v1/notes", json={"lead_id": lead["id"], "body": "Called, follow up next week"})
    assert note.status_code == 201

    notes = auth_client.get("/api/v1/notes", params={"lead_id": lead["id"]}).json()
    assert len(notes) == 1


def test_tasks_crud(auth_client):
    created = auth_client.post("/api/v1/tasks", json={"title": "Follow up call", "priority": "high"})
    assert created.status_code == 201
    task_id = created.json()["id"]

    updated = auth_client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert updated.json()["status"] == "done"

    assert auth_client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
