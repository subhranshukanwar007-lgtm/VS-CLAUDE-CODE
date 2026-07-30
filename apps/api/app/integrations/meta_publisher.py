"""Real publishers for Instagram, Facebook Pages and Threads.

Verified against Meta's own developer documentation:

- Instagram: two-step container flow. `POST /{ig-user-id}/media` creates a
  container, `POST /{ig-user-id}/media_publish` publishes it. Images use
  `image_url`, Reels use `media_type=REELS` + `video_url`. Video containers are
  processed asynchronously, so the container's `status_code` must be polled to
  FINISHED before publishing.
- Facebook: `POST /{page-id}/photos` or `/{page-id}/feed` — single call, no
  container step.
- Threads: same two-step shape as Instagram but a different host
  (`graph.threads.net`) and different endpoint names (`/threads` and
  `/threads_publish`). Text posts cap at 500 characters and containers go stale
  after 24 hours.

Every publisher fails loudly with a `PublisherError` carrying the platform's own
error message. Nothing here ever reports a post as published when the API call
did not succeed — a post you think went live but didn't is worse than a visible
failure.
"""

import asyncio
import logging

import httpx

from app.core.token_crypto import decrypt_token
from app.integrations.base import Publisher, PublisherError, PublishResult
from app.models.post import Post, PostFormat
from app.models.social_account import SocialAccount

logger = logging.getLogger("publisher.meta")

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
THREADS_BASE = "https://graph.threads.net/v1.0"

_TIMEOUT = httpx.Timeout(60.0)

# Instagram video containers are transcoded asynchronously; poll status_code until
# FINISHED. Meta gives no guaranteed SLA, so this caps at ~2.5 minutes and then
# fails with a message telling the user it's still processing.
_CONTAINER_POLL_ATTEMPTS = 30
_CONTAINER_POLL_DELAY_SECONDS = 5

THREADS_TEXT_LIMIT = 500


def _require_account(post: Post, account: SocialAccount | None, platform_label: str) -> tuple[str, str]:
    """Returns (external_account_id, access_token) or raises with the exact thing
    the user needs to go fix in the UI."""

    if account is None:
        raise PublisherError(
            f"No connected {platform_label} account. Connect one in Settings "
            f"-> Connected accounts before scheduling {platform_label} posts."
        )
    if not account.external_account_id:
        raise PublisherError(
            f"The connected {platform_label} account has no account ID stored. "
            "Reconnect it in Settings -> Connected accounts."
        )
    token = decrypt_token(account.access_token_encrypted)
    if not token:
        raise PublisherError(
            f"No usable access token for {platform_label}. Reconnect the account in "
            "Settings -> Connected accounts (tokens expire, and they also become "
            "unreadable if SECRET_KEY changed)."
        )
    return account.external_account_id, token


def _caption(post: Post) -> str:
    parts = [post.caption or ""]
    if post.hashtags:
        parts.append(post.hashtags)
    return "\n\n".join(p for p in parts if p).strip()


def _graph_error(response: httpx.Response) -> str:
    """Meta returns errors as {"error": {"message": ..., "code": ...}}. Surface the
    platform's own wording — it's far more actionable than a status code."""

    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:300]}"
    error = payload.get("error") or {}
    message = error.get("message") or response.text[:300]
    code = error.get("code")
    detail = error.get("error_user_msg") or error.get("error_user_title")
    parts = [str(message)]
    if detail and detail != message:
        parts.append(str(detail))
    if code is not None:
        parts.append(f"(Meta error code {code})")
    return " ".join(parts)


class InstagramPublisher(Publisher):
    """Instagram Business/Creator publishing via the Graph API container flow."""

    platform = "instagram"

    async def publish(self, post: Post, account: SocialAccount | None) -> PublishResult:
        ig_user_id, token = _require_account(post, account, "Instagram")

        if not post.media_url:
            raise PublisherError(
                "Instagram requires an image or video. Add a media URL to this post "
                "(the AI Video Studio's 'create post from this video' action does "
                "this for you)."
            )

        is_video = post.format in (PostFormat.REEL, PostFormat.VIDEO, PostFormat.STORY)
        container_params: dict[str, str] = {"access_token": token, "caption": _caption(post)}
        if is_video:
            # STORY and REELS are distinct media_types; everything else video-shaped
            # goes out as a Reel, which is what Instagram now serves feed video as.
            container_params["media_type"] = "STORIES" if post.format == PostFormat.STORY else "REELS"
            container_params["video_url"] = post.media_url
        else:
            container_params["image_url"] = post.media_url

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            created = await client.post(f"{GRAPH_BASE}/{ig_user_id}/media", data=container_params)
            if created.status_code >= 400:
                raise PublisherError(f"Instagram container creation failed: {_graph_error(created)}")
            container_id = created.json().get("id")
            if not container_id:
                raise PublisherError(f"Instagram returned no container id: {created.text[:300]}")

            if is_video:
                await self._await_container_ready(client, container_id, token)

            published = await client.post(
                f"{GRAPH_BASE}/{ig_user_id}/media_publish",
                data={"creation_id": container_id, "access_token": token},
            )
            if published.status_code >= 400:
                raise PublisherError(f"Instagram publish failed: {_graph_error(published)}")

            media_id = published.json().get("id")
            if not media_id:
                raise PublisherError(f"Instagram returned no media id: {published.text[:300]}")

            permalink = await self._fetch_permalink(client, media_id, token)

        logger.info("published post %s to instagram -> %s", post.id, media_id)
        return PublishResult(external_post_id=str(media_id), permalink=permalink)

    async def _await_container_ready(self, client: httpx.AsyncClient, container_id: str, token: str) -> None:
        for _ in range(_CONTAINER_POLL_ATTEMPTS):
            status = await client.get(
                f"{GRAPH_BASE}/{container_id}",
                params={"fields": "status_code,status", "access_token": token},
            )
            if status.status_code >= 400:
                raise PublisherError(f"Instagram container status check failed: {_graph_error(status)}")
            body = status.json()
            code = body.get("status_code")
            if code == "FINISHED":
                return
            if code == "ERROR":
                raise PublisherError(
                    f"Instagram rejected the video while processing: {body.get('status') or 'no detail given'}"
                )
            await asyncio.sleep(_CONTAINER_POLL_DELAY_SECONDS)

        raise PublisherError(
            "Instagram was still processing the video after "
            f"{_CONTAINER_POLL_ATTEMPTS * _CONTAINER_POLL_DELAY_SECONDS}s. "
            "The post was not published; try again, or use a shorter/smaller video."
        )

    async def _fetch_permalink(self, client: httpx.AsyncClient, media_id: str, token: str) -> str | None:
        """Best-effort: the post is already live, so a failure here must not fail
        the publish."""

        try:
            resp = await client.get(
                f"{GRAPH_BASE}/{media_id}", params={"fields": "permalink", "access_token": token}
            )
            if resp.status_code < 400:
                return resp.json().get("permalink")
        except httpx.HTTPError:
            logger.debug("permalink lookup failed for %s", media_id, exc_info=True)
        return None


class FacebookPublisher(Publisher):
    """Facebook Page publishing. Unlike Instagram this is a single call."""

    platform = "facebook"

    async def publish(self, post: Post, account: SocialAccount | None) -> PublishResult:
        page_id, token = _require_account(post, account, "Facebook")
        message = _caption(post)

        if post.format == PostFormat.STORY:
            if not post.media_url:
                raise PublisherError("A Facebook Story needs an image or video.")
            # Page Stories are their own endpoints, not /videos or /photos. Note
            # Facebook ignores captions on Stories.
            is_video_story = post.media_url.lower().endswith((".mp4", ".mov", ".m4v"))
            endpoint = f"{GRAPH_BASE}/{page_id}/{'video_stories' if is_video_story else 'photo_stories'}"
            payload = {"file_url" if is_video_story else "photo_url": post.media_url, "access_token": token}
        elif post.media_url and post.format in (PostFormat.REEL, PostFormat.VIDEO):
            endpoint = f"{GRAPH_BASE}/{page_id}/videos"
            payload = {"file_url": post.media_url, "description": message, "access_token": token}
        elif post.media_url:
            endpoint = f"{GRAPH_BASE}/{page_id}/photos"
            payload = {"url": post.media_url, "message": message, "access_token": token}
        else:
            if not message:
                raise PublisherError("A Facebook post needs either a caption or media.")
            endpoint = f"{GRAPH_BASE}/{page_id}/feed"
            payload = {"message": message, "access_token": token}

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(endpoint, data=payload)
        if resp.status_code >= 400:
            raise PublisherError(f"Facebook publish failed: {_graph_error(resp)}")

        body = resp.json()
        # /feed returns post_id, /photos and /videos return id.
        external_id = body.get("post_id") or body.get("id")
        if not external_id:
            raise PublisherError(f"Facebook returned no post id: {resp.text[:300]}")

        logger.info("published post %s to facebook -> %s", post.id, external_id)
        return PublishResult(
            external_post_id=str(external_id),
            permalink=f"https://www.facebook.com/{external_id}",
        )


class ThreadsPublisher(Publisher):
    """Threads publishing. Same two-step container shape as Instagram, but a
    different host, different endpoint names, and a 500-character text cap."""

    platform = "threads"

    async def publish(self, post: Post, account: SocialAccount | None) -> PublishResult:
        threads_user_id, token = _require_account(post, account, "Threads")
        text = _caption(post)

        if post.format == PostFormat.STORY:
            raise PublisherError(
                "Threads has no Stories, and its API does not support them. Post "
                "this as a text, image or video Thread instead — or schedule the "
                "Story to Instagram, which does support it."
            )

        if len(text) > THREADS_TEXT_LIMIT:
            raise PublisherError(
                f"Threads posts are limited to {THREADS_TEXT_LIMIT} characters; this one is "
                f"{len(text)}. Shorten the caption (hashtags count toward the limit)."
            )

        params: dict[str, str] = {"access_token": token}
        if post.media_url and post.format in (PostFormat.REEL, PostFormat.VIDEO):
            params["media_type"] = "VIDEO"
            params["video_url"] = post.media_url
        elif post.media_url:
            params["media_type"] = "IMAGE"
            params["image_url"] = post.media_url
        else:
            if not text:
                raise PublisherError("A Threads post needs either text or media.")
            params["media_type"] = "TEXT"
        if text:
            params["text"] = text

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            created = await client.post(f"{THREADS_BASE}/{threads_user_id}/threads", data=params)
            if created.status_code >= 400:
                raise PublisherError(f"Threads container creation failed: {_graph_error(created)}")
            container_id = created.json().get("id")
            if not container_id:
                raise PublisherError(f"Threads returned no container id: {created.text[:300]}")

            published = await client.post(
                f"{THREADS_BASE}/{threads_user_id}/threads_publish",
                data={"creation_id": container_id, "access_token": token},
            )
            if published.status_code >= 400:
                raise PublisherError(f"Threads publish failed: {_graph_error(published)}")

            thread_id = published.json().get("id")
            if not thread_id:
                raise PublisherError(f"Threads returned no post id: {published.text[:300]}")

            permalink = await self._fetch_permalink(client, thread_id, token)

        logger.info("published post %s to threads -> %s", post.id, thread_id)
        return PublishResult(external_post_id=str(thread_id), permalink=permalink)

    async def _fetch_permalink(self, client: httpx.AsyncClient, thread_id: str, token: str) -> str | None:
        try:
            resp = await client.get(
                f"{THREADS_BASE}/{thread_id}", params={"fields": "permalink", "access_token": token}
            )
            if resp.status_code < 400:
                return resp.json().get("permalink")
        except httpx.HTTPError:
            logger.debug("threads permalink lookup failed for %s", thread_id, exc_info=True)
        return None
