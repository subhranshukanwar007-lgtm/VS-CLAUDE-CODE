import logging
import uuid

from app.integrations.base import Publisher, PublishResult
from app.models.post import Post
from app.models.social_account import SocialAccount

logger = logging.getLogger("publisher")


class LogPublisher(Publisher):
    """Default publisher used when no platform-specific integration is registered.
    Marks the post published and logs it — a real, working no-op that lets the
    scheduling engine be exercised end-to-end without external credentials."""

    platform = "*"

    async def publish(self, post: Post, account: SocialAccount | None) -> PublishResult:
        external_id = f"log-{uuid.uuid4().hex[:12]}"
        logger.info(
            "publishing post %s to %s (format=%s) -> external_id=%s",
            post.id,
            post.platform.value,
            post.format.value,
            external_id,
        )
        return PublishResult(external_post_id=external_id, permalink=None)
