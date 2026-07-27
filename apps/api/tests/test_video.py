import app.services.video_service as video_service
from app.database import get_db
from app.main import app
from app.models.video_generation import VideoGenerationStatus
from app.services.video.base import VideoPollResult, VideoProvider


class _FakeProvider(VideoProvider):
    name = "replicate"

    def __init__(self, poll_result: VideoPollResult | None = None) -> None:
        self._poll_result = poll_result or VideoPollResult(status=VideoGenerationStatus.PROCESSING)

    async def submit(self, prompt, model, extra_params) -> str:
        return "fake-job-123"

    async def poll(self, external_job_id) -> VideoPollResult:
        return self._poll_result


def _db():
    return next(app.dependency_overrides[get_db]())


def test_generate_without_token_returns_503(auth_client):
    resp = auth_client.post("/api/v1/video/generate", json={"prompt": "a golden retriever surfing"})
    assert resp.status_code == 503


def test_generate_creates_processing_generation(auth_client, monkeypatch):
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider())

    resp = auth_client.post("/api/v1/video/generate", json={"prompt": "a golden retriever surfing"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "processing"
    assert body["model"]

    listed = auth_client.get("/api/v1/video").json()
    assert any(g["id"] == body["id"] for g in listed)


def test_get_generation_polls_and_updates_to_succeeded(auth_client, monkeypatch):
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider())
    created = auth_client.post("/api/v1/video/generate", json={"prompt": "a golden retriever surfing"}).json()

    succeeded = VideoPollResult(status=VideoGenerationStatus.SUCCEEDED, video_url="https://cdn.example/video.mp4")
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider(succeeded))

    resp = auth_client.get(f"/api/v1/video/{created['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["video_url"] == "https://cdn.example/video.mp4"

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "video_ready" for n in notifications)


def test_get_generation_polls_and_updates_to_failed(auth_client, monkeypatch):
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider())
    created = auth_client.post("/api/v1/video/generate", json={"prompt": "a golden retriever surfing"}).json()

    failed = VideoPollResult(status=VideoGenerationStatus.FAILED, error="model overloaded")
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider(failed))

    resp = auth_client.get(f"/api/v1/video/{created['id']}")
    assert resp.json()["status"] == "failed"

    notifications = auth_client.get("/api/v1/notifications").json()
    assert any(n["type"] == "video_failed" for n in notifications)


def test_attach_to_post_before_ready_returns_409(auth_client, monkeypatch):
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider())
    created = auth_client.post("/api/v1/video/generate", json={"prompt": "a golden retriever surfing"}).json()

    resp = auth_client.post(f"/api/v1/video/{created['id']}/attach-to-post", json={"platform": "instagram"})
    assert resp.status_code == 409


def test_attach_to_post_after_ready_creates_post(auth_client, monkeypatch):
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider())
    created = auth_client.post("/api/v1/video/generate", json={"prompt": "a golden retriever surfing"}).json()

    succeeded = VideoPollResult(status=VideoGenerationStatus.SUCCEEDED, video_url="https://cdn.example/video.mp4")
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider(succeeded))
    auth_client.get(f"/api/v1/video/{created['id']}")

    resp = auth_client.post(
        f"/api/v1/video/{created['id']}/attach-to-post",
        json={"platform": "instagram", "format": "reel", "caption": "Check this out"},
    )
    assert resp.status_code == 201
    post = resp.json()
    assert post["media_url"] == "https://cdn.example/video.mp4"
    assert post["format"] == "reel"

    generation = auth_client.get(f"/api/v1/video/{created['id']}").json()
    assert generation["post_id"] == post["id"]


async def test_poll_all_pending_is_idempotent(auth_client, monkeypatch):
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider())
    auth_client.post("/api/v1/video/generate", json={"prompt": "a cat riding a skateboard"})

    succeeded = VideoPollResult(status=VideoGenerationStatus.SUCCEEDED, video_url="https://cdn.example/cat.mp4")
    monkeypatch.setattr(video_service, "get_video_provider", lambda kind=None: _FakeProvider(succeeded))

    db = _db()
    try:
        first = await video_service.poll_all_pending(db)
        assert first == 1
        second = await video_service.poll_all_pending(db)
        assert second == 0
    finally:
        db.close()
