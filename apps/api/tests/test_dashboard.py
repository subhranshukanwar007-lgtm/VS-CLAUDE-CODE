from datetime import date, timedelta

from app.database import get_db
from app.main import app
from app.models.metric import Metric, MetricKind
from app.models.post import Platform


def _seed_metrics(auth_client):
    email = "owner@example.com"
    from app.models.user import User

    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == email).one()
    today = date.today()
    for i in range(10):
        db.add(
            Metric(
                owner_id=user.id,
                platform=Platform.INSTAGRAM,
                kind=MetricKind.VIEWS,
                value=1000 + i * 50,
                recorded_on=today - timedelta(days=9 - i),
            )
        )
        db.add(
            Metric(
                owner_id=user.id,
                platform=Platform.INSTAGRAM,
                kind=MetricKind.FOLLOWERS,
                value=5000 + i * 20,
                recorded_on=today - timedelta(days=9 - i),
            )
        )
    db.commit()
    db.close()


def test_dashboard_overview_empty_account(auth_client):
    resp = auth_client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["followers"] == 0
    assert body["crm"]["total_leads"] == 0


def test_dashboard_overview_with_seeded_metrics(auth_client):
    _seed_metrics(auth_client)
    resp = auth_client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["views"] == sum(1000 + i * 50 for i in range(10))
    assert body["summary"]["followers"] == 5000 + 9 * 20

    views_prediction = next(p for p in body["predictions"] if p["metric"] == "views")
    assert views_prediction["projected_30d"] > 0
