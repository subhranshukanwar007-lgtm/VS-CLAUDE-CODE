import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.notification import NotificationType
from app.models.post import Post, PostStatus
from app.models.user import User
from app.services.dm_service import send_pending
from app.services.followup_service import run_follow_up_automation
from app.services.notification_service import notify
from app.services.scheduler_service import publish_due_posts
from app.services.video_service import poll_all_pending

logger = logging.getLogger("workers")


@celery_app.task(name="app.workers.tasks.publish_due_posts_task")
def publish_due_posts_task() -> int:
    db = SessionLocal()
    try:
        count = asyncio.run(publish_due_posts(db))
        if count:
            logger.info("published %d due posts", count)
        return count
    finally:
        db.close()


def _period_summary(db, user_id, since: datetime) -> str:
    published = (
        db.scalar(
            select(func.count())
            .select_from(Post)
            .where(Post.author_id == user_id, Post.status == PostStatus.PUBLISHED, Post.published_at >= since)
        )
        or 0
    )
    return f"{published} post(s) published"


def _send_summaries(period_label: str, since: datetime, notification_type: NotificationType) -> int:
    db = SessionLocal()
    try:
        user_ids = db.scalars(select(User.id).where(User.is_active.is_(True))).all()
        for user_id in user_ids:
            summary = _period_summary(db, user_id, since)
            notify(
                db,
                user_id,
                notification_type,
                title=f"Your {period_label} summary",
                body=summary,
                link="/dashboard",
            )
        return len(user_ids)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.send_daily_summaries_task")
def send_daily_summaries_task() -> int:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    return _send_summaries("daily", since, NotificationType.SYSTEM)


@celery_app.task(name="app.workers.tasks.send_weekly_summaries_task")
def send_weekly_summaries_task() -> int:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    return _send_summaries("weekly", since, NotificationType.SYSTEM)


@celery_app.task(name="app.workers.tasks.send_monthly_summaries_task")
def send_monthly_summaries_task() -> int:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    return _send_summaries("monthly", since, NotificationType.SYSTEM)


@celery_app.task(name="app.workers.tasks.run_follow_up_automation_task")
def run_follow_up_automation_task() -> int:
    db = SessionLocal()
    try:
        count = asyncio.run(run_follow_up_automation(db))
        if count:
            logger.info("triggered %d lead follow-ups", count)
        return count
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.send_pending_dms_task")
def send_pending_dms_task() -> int:
    """Flush the auto-DM queue. Runs often because the value of this DM decays
    fast — someone who commented "PLAN" two hours ago has moved on."""

    db = SessionLocal()
    try:
        counts = asyncio.run(send_pending(db))
        if any(counts.values()):
            logger.info("auto-DM queue: %s", counts)
        return counts["sent"]
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.poll_video_generations_task")
def poll_video_generations_task() -> int:
    db = SessionLocal()
    try:
        count = asyncio.run(poll_all_pending(db))
        if count:
            logger.info("%d video generation(s) changed status", count)
        return count
    finally:
        db.close()
