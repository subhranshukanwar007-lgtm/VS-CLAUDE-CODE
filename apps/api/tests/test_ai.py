import app.services.agents.runner as agents_runner
import app.services.content_service as content_service
from app.services.ai.base import AIProvider, AIProviderError


class _FakeProvider(AIProvider):
    name = "openai"
    model = "fake-model"

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        return f"FAKE_RESPONSE for: {prompt[:40]}"


class _FailingProvider(AIProvider):
    name = "openai"
    model = "fake-model"

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        raise AIProviderError("OPENAI_API_KEY is not configured")


def test_caption_generation_without_configured_key_returns_503(auth_client, monkeypatch):
    resp = auth_client.post("/api/v1/ai/caption", json={"topic": "new coaching program launch"})
    assert resp.status_code == 503


def test_caption_generation_with_mocked_provider(auth_client, monkeypatch):
    monkeypatch.setattr(content_service, "get_provider", lambda kind=None: _FakeProvider())
    resp = auth_client.post("/api/v1/ai/caption", json={"topic": "new coaching program launch"})
    assert resp.status_code == 200
    assert "FAKE_RESPONSE" in resp.json()["result"]


def test_hashtag_generation_with_mocked_provider(auth_client, monkeypatch):
    monkeypatch.setattr(content_service, "get_provider", lambda kind=None: _FakeProvider())
    resp = auth_client.post("/api/v1/ai/hashtags", json={"topic": "fitness reels", "count": 10})
    assert resp.status_code == 200


def test_agent_chat_unknown_agent_rejected(auth_client):
    resp = auth_client.post("/api/v1/ai/agents/chat", json={"agent": "not-a-real-agent", "message": "hi"})
    assert resp.status_code == 403


def test_agent_chat_crm_agent_grounds_with_real_data(auth_client, monkeypatch):
    captured = {}

    class _CapturingProvider(_FakeProvider):
        async def generate(self, prompt, system=None, max_tokens=1024):
            captured["system"] = system
            return "agent reply"

    monkeypatch.setattr(agents_runner, "get_provider", lambda kind=None: _CapturingProvider())

    auth_client.post("/api/v1/leads", json={"full_name": "Grounding Lead", "source": "manual"})

    resp = auth_client.post("/api/v1/ai/agents/chat", json={"agent": "crm", "message": "how's my pipeline?"})
    assert resp.status_code == 200
    assert "1 total leads" in captured["system"]


def test_list_agents_returns_the_curated_set(auth_client):
    """Asserts the exact roster rather than a count, so trimming or adding an agent
    is a deliberate edit here instead of a number quietly drifting."""

    resp = auth_client.get("/api/v1/ai/agents")
    assert resp.status_code == 200
    assert set(resp.json()) == {"content", "crm", "sales", "analytics", "money", "support"}
