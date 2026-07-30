"""Publisher tests.

These deliberately never hit the network. The valuable, testable behaviour here is
the *guard* logic — refusing to publish without credentials or media, enforcing
platform limits, and turning Meta's error envelope into a readable message. That
logic is where a bug silently marks a post "published" that never went live.
"""

import httpx
import pytest

from app.core.token_crypto import decrypt_token, encrypt_token
from app.integrations.base import PublisherError
from app.integrations.meta_publisher import (
    THREADS_TEXT_LIMIT,
    FacebookPublisher,
    InstagramPublisher,
    ThreadsPublisher,
    _graph_error,
)
from app.models.post import Platform, Post, PostFormat
from app.models.social_account import SocialAccount


def _post(**kwargs) -> Post:
    defaults = {
        "platform": Platform.INSTAGRAM,
        "format": PostFormat.POST,
        "caption": "Hello",
        "hashtags": "#fit",
        "media_url": "https://cdn.example.com/img.jpg",
    }
    return Post(**{**defaults, **kwargs})


def _account(platform=Platform.INSTAGRAM, account_id="123", token="tok") -> SocialAccount:
    return SocialAccount(
        platform=platform,
        handle="@me",
        external_account_id=account_id,
        access_token_encrypted=encrypt_token(token) if token else None,
    )


# --- token crypto ---


def test_token_roundtrip():
    assert decrypt_token(encrypt_token("secret-value")) == "secret-value"


def test_encrypted_token_is_not_plaintext():
    assert "secret-value" not in encrypt_token("secret-value")


def test_decrypt_returns_none_for_missing_or_garbage():
    assert decrypt_token(None) is None
    assert decrypt_token("") is None
    # Simulates a rotated SECRET_KEY: degrade to "reconnect", never raise.
    assert decrypt_token("not-a-fernet-token") is None


# --- guard rails ---


@pytest.mark.asyncio
async def test_instagram_refuses_without_connected_account():
    with pytest.raises(PublisherError, match="No connected Instagram account"):
        await InstagramPublisher().publish(_post(), account=None)


@pytest.mark.asyncio
async def test_instagram_refuses_without_token():
    with pytest.raises(PublisherError, match="No usable access token"):
        await InstagramPublisher().publish(_post(), account=_account(token=None))


@pytest.mark.asyncio
async def test_instagram_refuses_without_account_id():
    with pytest.raises(PublisherError, match="no account ID stored"):
        await InstagramPublisher().publish(_post(), account=_account(account_id=None))


@pytest.mark.asyncio
async def test_instagram_refuses_without_media():
    with pytest.raises(PublisherError, match="requires an image or video"):
        await InstagramPublisher().publish(_post(media_url=None), account=_account())


@pytest.mark.asyncio
async def test_facebook_text_only_post_needs_a_caption():
    with pytest.raises(PublisherError, match="needs either a caption or media"):
        await FacebookPublisher().publish(
            _post(platform=Platform.FACEBOOK, media_url=None, caption=None, hashtags=None),
            account=_account(Platform.FACEBOOK),
        )


@pytest.mark.asyncio
async def test_threads_rejects_stories_because_the_platform_has_none():
    with pytest.raises(PublisherError, match="no Stories"):
        await ThreadsPublisher().publish(
            _post(platform=Platform.THREADS, format=PostFormat.STORY),
            account=_account(Platform.THREADS),
        )


@pytest.mark.asyncio
async def test_threads_enforces_character_limit_including_hashtags():
    long_caption = "x" * (THREADS_TEXT_LIMIT - 5)
    with pytest.raises(PublisherError, match=f"limited to {THREADS_TEXT_LIMIT} characters"):
        await ThreadsPublisher().publish(
            _post(platform=Platform.THREADS, caption=long_caption, hashtags="#some #tags #here", media_url=None),
            account=_account(Platform.THREADS),
        )


@pytest.mark.asyncio
async def test_threads_accepts_text_within_limit(monkeypatch):
    """Confirms the limit check measures caption + hashtags and lets a valid post
    through to the API call (which we stub at the transport layer)."""

    calls: list[str] = []

    async def fake_post(self, url, **kwargs):
        calls.append(url)
        payload = {"id": "container-1"} if url.endswith("/threads") else {"id": "thread-99"}
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    async def fake_get(self, url, **kwargs):
        return httpx.Response(
            200, json={"permalink": "https://threads.net/p/1"}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await ThreadsPublisher().publish(
        _post(platform=Platform.THREADS, caption="Short and sweet", hashtags="#fit", media_url=None),
        account=_account(Platform.THREADS),
    )
    assert result.external_post_id == "thread-99"
    assert result.permalink == "https://threads.net/p/1"
    # Two-step container flow: create then publish.
    assert [c.rsplit("/", 1)[-1] for c in calls] == ["threads", "threads_publish"]


@pytest.mark.asyncio
async def test_publish_failure_surfaces_meta_error_message(monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            400,
            json={"error": {"message": "Media URL is not reachable", "code": 9004}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(PublisherError, match="Media URL is not reachable"):
        await InstagramPublisher().publish(_post(), account=_account())


# --- error formatting ---


def test_graph_error_extracts_message_and_code():
    resp = httpx.Response(
        400,
        json={"error": {"message": "Invalid token", "code": 190}},
        request=httpx.Request("POST", "https://example.com"),
    )
    formatted = _graph_error(resp)
    assert "Invalid token" in formatted
    assert "190" in formatted


def test_graph_error_falls_back_on_non_json_body():
    resp = httpx.Response(502, text="Bad Gateway", request=httpx.Request("POST", "https://example.com"))
    assert "502" in _graph_error(resp)
