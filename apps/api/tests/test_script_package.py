"""Tests for the content package generator.

The AI provider is stubbed throughout: what's worth pinning down is the parsing
and the failure behaviour, not that a live model produces good copy. The
important property is that a malformed reply fails loudly — a half-built package
(beats with no captions, a script that stops at 8 seconds) is worse than an
error, because the user only finds out mid-shoot.
"""

import json

import pytest

import app.config as config_module
from app.services.ai.base import AIProvider


class StubProvider(AIProvider):
    name = "openai"
    model = "stub-model"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.last_system: str | None = None
        self.last_prompt: str | None = None

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        self.last_prompt = prompt
        self.last_system = system
        return self.reply


def _valid_payload() -> dict:
    return {
        "hooks": [
            "Your 3pm crash isn't tiredness.",
            "Stop blaming your sleep.",
            "This one habit fixed my energy.",
        ],
        "beats": [
            {
                "start_seconds": 0,
                "end_seconds": 3,
                "spoken": "Your 3pm crash isn't tiredness.",
                "caption": "3PM crash? Not sleep.",
                "broll": "Close-up of a clock hitting 3:00.",
            },
            {
                "start_seconds": 3,
                "end_seconds": 15,
                "spoken": "It's what you ate at noon.",
                "caption": "It's your lunch",
                "broll": "Overhead shot of a heavy rice plate.",
            },
        ],
        "higgsfield_prompt": "Handheld medium close-up, slow push in, window light, energetic delivery.",
        "broll_notes": "Shoot everything on a phone in daylight near a window.",
        "post_caption": "The real reason you crash at 3pm.",
        "cta": "Comment PLAN and I'll send you the fix.",
        "hashtags": "#fitness #energy #healthcoach #nutrition #india",
    }


def _install(monkeypatch, reply: str) -> StubProvider:
    provider = StubProvider(reply)
    monkeypatch.setattr("app.services.script_service.get_provider", lambda kind=None: provider)
    return provider


def _request(**overrides) -> dict:
    return {"topic": "why you crash at 3pm", "duration_seconds": 30, **overrides}


# --- happy path ---


def test_returns_a_complete_package(auth_client, monkeypatch):
    _install(monkeypatch, json.dumps(_valid_payload()))
    resp = auth_client.post("/api/v1/video/script-package", json=_request())
    assert resp.status_code == 200

    body = resp.json()
    assert len(body["hooks"]) == 3
    assert len(body["beats"]) == 2
    assert body["beats"][0]["spoken"]
    assert body["beats"][0]["caption"]
    assert body["beats"][0]["broll"]
    assert body["higgsfield_prompt"]
    assert body["cta"]
    assert body["hashtags"]
    assert body["generation_id"]
    assert body["model"] == "stub-model"


def test_package_returns_the_saved_generation_id(auth_client, monkeypatch):
    """The raw model output is persisted as an AIGeneration so a package can be
    traced back to exactly what the model returned."""

    _install(monkeypatch, json.dumps(_valid_payload()))
    body = auth_client.post("/api/v1/video/script-package", json=_request()).json()
    assert body["generation_id"]
    assert body["provider"] == "openai"


def test_json_wrapped_in_a_code_fence_is_parsed(auth_client, monkeypatch):
    """Models fence JSON often enough that stripping it is worth doing."""

    _install(monkeypatch, f"Here you go!\n```json\n{json.dumps(_valid_payload())}\n```\nHope that helps.")
    resp = auth_client.post("/api/v1/video/script-package", json=_request())
    assert resp.status_code == 200
    assert len(resp.json()["beats"]) == 2


def test_json_surrounded_by_prose_is_parsed(auth_client, monkeypatch):
    _install(monkeypatch, f"Sure thing. {json.dumps(_valid_payload())} Let me know if you want changes.")
    assert auth_client.post("/api/v1/video/script-package", json=_request()).status_code == 200


# --- language ---


def test_hinglish_setting_reaches_the_prompt(auth_client, monkeypatch):
    """The whole point of the Hinglish option: the instruction has to actually be
    sent to the model, not just stored in settings."""

    auth_client.patch("/api/v1/automation/settings", json={"reply_language": "hinglish"})
    provider = _install(monkeypatch, json.dumps(_valid_payload()))

    resp = auth_client.post("/api/v1/video/script-package", json=_request())
    assert resp.json()["language"] == "hinglish"
    assert "Roman" in provider.last_prompt
    assert "Devanagari" in provider.last_prompt


def test_request_language_overrides_the_setting(auth_client, monkeypatch):
    auth_client.patch("/api/v1/automation/settings", json={"reply_language": "hinglish"})
    _install(monkeypatch, json.dumps(_valid_payload()))

    resp = auth_client.post("/api/v1/video/script-package", json=_request(language="english"))
    assert resp.json()["language"] == "english"


def test_brand_voice_is_included_when_set(auth_client, monkeypatch):
    auth_client.patch("/api/v1/users/me", json={"brand_voice": "blunt, no fluff, gym-bro energy"})
    provider = _install(monkeypatch, json.dumps(_valid_payload()))

    auth_client.post("/api/v1/video/script-package", json=_request())
    assert "gym-bro energy" in provider.last_prompt


# --- the avatar constraint ---


def test_system_prompt_forbids_describing_a_face(auth_client, monkeypatch):
    """The creator's own trained avatar supplies the face. A Higgsfield prompt that
    also describes a person fights it, so the instruction must be explicit."""

    provider = _install(monkeypatch, json.dumps(_valid_payload()))
    auth_client.post("/api/v1/video/script-package", json=_request())

    system = provider.last_system
    assert "NEVER describe the person's face" in system
    assert "avatar" in system


# --- failure behaviour ---


def test_unparseable_reply_fails_loudly(auth_client, monkeypatch):
    _install(monkeypatch, "Sorry, I can't help with that request.")
    resp = auth_client.post("/api/v1/video/script-package", json=_request())
    assert resp.status_code == 503
    assert "content package" in resp.json()["detail"]


def test_reply_with_no_beats_fails_rather_than_returning_an_empty_script(auth_client, monkeypatch):
    payload = _valid_payload()
    payload["beats"] = []
    _install(monkeypatch, json.dumps(payload))

    resp = auth_client.post("/api/v1/video/script-package", json=_request())
    assert resp.status_code == 503


def test_beats_missing_spoken_lines_are_dropped_not_kept_blank(auth_client, monkeypatch):
    payload = _valid_payload()
    payload["beats"].append({"start_seconds": 15, "end_seconds": 20, "caption": "orphan", "broll": "x"})
    _install(monkeypatch, json.dumps(payload))

    body = auth_client.post("/api/v1/video/script-package", json=_request()).json()
    assert len(body["beats"]) == 2
    assert all(beat["spoken"] for beat in body["beats"])


def test_missing_hooks_fall_back_to_the_opening_line(auth_client, monkeypatch):
    """The first spoken line *is* the hook, so this fallback is real rather than
    invented."""

    payload = _valid_payload()
    del payload["hooks"]
    _install(monkeypatch, json.dumps(payload))

    body = auth_client.post("/api/v1/video/script-package", json=_request()).json()
    assert body["hooks"] == ["Your 3pm crash isn't tiredness."]


def test_missing_ai_key_returns_503_not_a_fake_script(auth_client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "openai_api_key", "")
    monkeypatch.setattr(config_module.settings, "anthropic_api_key", "")
    monkeypatch.setattr(config_module.settings, "gemini_api_key", "")

    resp = auth_client.post("/api/v1/video/script-package", json=_request())
    assert resp.status_code == 503


# --- validation ---


@pytest.mark.parametrize(
    "payload",
    [
        {"topic": "hi"},
        {"topic": "a valid topic", "duration_seconds": 5},
        {"topic": "a valid topic", "duration_seconds": 500},
    ],
)
def test_invalid_requests_are_rejected(auth_client, payload):
    assert auth_client.post("/api/v1/video/script-package", json=payload).status_code == 422


def test_requires_auth(client):
    assert client.post("/api/v1/video/script-package", json=_request()).status_code == 401
