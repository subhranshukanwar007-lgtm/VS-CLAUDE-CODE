import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import PublisherError
from app.integrations.registry import get_publisher
from app.models.notification import NotificationType
from app.models.post import Platform, Post, PostStatus
from app.models.social_account import SocialAccount
from app.services.automation_settings_service import is_auto_publish_enabled
from app.services.notification_service import notify

logger = logging.getLogger("scheduler")


def find_account(db: Session, owner_id: uuid.UUID, platform: Platform) -> SocialAccount | None:
    return db.scalar(
        select(SocialAccount)
        .where(
            SocialAccount.owner_id == owner_id,
            SocialAccount.platform == platform,
            SocialAccount.is_active.is_(True),
        )
        .order_by(SocialAccount.created_at)
    )


async def publish_post(db: Session, post: Post, now: datetime | None = None) -> None:
    """Publish a single post through its platform's registered Publisher, updating
    the post's status either way. Used both by the beat task below and by the
    manual "publish now" endpoint, so approval and scheduling share one code path."""

    now = now or datetime.now(timezone.utc)

    post.status = PostStatus.PUBLISHING
    db.commit()

    account = find_account(db, post.author_id, post.platform)
    publisher = get_publisher(post.platform)
    try:
        result = await publisher.publish(post, account=account)
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
        return

    post.status = PostStatus.PUBLISHED
    post.published_at = now
    post.external_post_id = result.external_post_id
    post.failure_reason = None
    db.commit()
    notify(
        db,
        post.author_id,
        NotificationType.POST_PUBLISHED,
        title=f"Post published to {post.platform.value}",
        body=post.caption[:200] if post.caption else None,
        link=result.permalink or f"/calendar?post={post.id}",
    )


async def publish_due_posts(db: Session, now: datetime | None = None) -> int:
    """Find every SCHEDULED post whose scheduled_at has passed and either publish
    it or hold it for approval, depending on the user's per-platform auto-publish
    setting (Settings -> Automation).

    Returns the number of posts published. Called by the Celery beat task on a
    fixed interval (app/workers/tasks.py).

    Holding for approval deliberately moves the post back to DRAFT rather than
    leaving it SCHEDULED, so it isn't re-evaluated on every subsequent beat tick —
    otherwise a user with auto-publish off would get a notification every minute
    forever.
    """

    now = now or datetime.now(timezone.utc)
    due_posts = db.scalars(
        select(Post).where(Post.status == PostStatus.SCHEDULED, Post.scheduled_at <= now)
    ).all()

    published = 0
    for post in due_posts:
        if not is_auto_publish_enabled(db, post.author_id, post.platform):
            post.status = PostStatus.DRAFT
            db.commit()
            notify(
                db,
                post.author_id,
                NotificationType.POST_PUBLISHED,
                title=f"{post.platform.value.title()} post ready for your approval",
                body=(post.caption[:200] if post.caption else None),
                link=f"/calendar?post={post.id}",
            )
            logger.info("post %s held for approval (auto-publish off for %s)", post.id, post.platform.value)
            continue

        await publish_post(db, post, now=now)
        if post.status == PostStatus.PUBLISHED:
            published += 1

    return published
