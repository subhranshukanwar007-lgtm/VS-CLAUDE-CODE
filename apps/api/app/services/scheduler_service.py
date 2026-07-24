import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import PublisherError
from app.integrations.registry import get_publisher
from app.models.notification import NotificationType
from app.models.post import Post, PostStatus
from app.services.notification_service import notify

logger = logging.getLogger("scheduler")


async def publish_due_posts(db: Session, now: datetime | None = None) -> int:
    """Find every SCHEDULED post whose scheduled_at has passed and publish it via
    the platform's registered Publisher (see app/integrations/registry.py). Returns
    the number of posts processed. Called by the Celery beat task on a fixed
    interval (app/workers/tasks.py)."""

    now = now or datetime.now(timezone.utc)
    due_posts = db.scalars(
        select(Post).where(Post.status == PostStatus.SCHEDULED, Post.scheduled_at <= now)
    ).all()

    for post in due_posts:
        post.status = PostStatus.PUBLISHING
        db.commit()

        publisher = get_publisher(post.platform)
        try:
            result = await publisher.publish(post, account=None)
        except PublisherError as exc:
            post.status = PostStatus.FAILED
            post.failure_reason = str(exc)
            db.commit()
            notify(
                db,
                post.author_id,
                NotificationType.POST_FAILED,
                title=f"Post to {post.platform.value} failed",
                body=str(exc),
                link=f"/calendar?post={post.id}",
            )
            logger.warning("post %s failed to publish: %s", post.id, exc)
            continue

        post.status = PostStatus.PUBLISHED
        post.published_at = now
        post.external_post_id = result.external_post_id
        db.commit()
        notify(
            db,
            post.author_id,
            NotificationType.POST_PUBLISHED,
            title=f"Post published to {post.platform.value}",
            body=post.caption[:200] if post.caption else None,
            link=f"/calendar?post={post.id}",
        )

    return len(due_posts)
