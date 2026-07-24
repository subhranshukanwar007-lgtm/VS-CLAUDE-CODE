import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost:5432/social_os_test"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

_engine = create_engine(os.environ["DATABASE_URL"], future=True)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, future=True)


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


def _override_get_db():
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "full_name": "Owner User", "password": "supersecret123"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "supersecret123"})
    token = resp.json()["tokens"]["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
