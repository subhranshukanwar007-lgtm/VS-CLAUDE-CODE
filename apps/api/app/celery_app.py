from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery("social_os", broker=settings.celery_broker, backend=settings.celery_backend)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "publish-due-posts": {
        "task": "app.workers.tasks.publish_due_posts_task",
        "schedule": 60.0,
    },
    "daily-summary": {
        "task": "app.workers.tasks.send_daily_summaries_task",
        "schedule": crontab(hour=8, minute=0),
    },
    "weekly-summary": {
        "task": "app.workers.tasks.send_weekly_summaries_task",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    "monthly-summary": {
        "task": "app.workers.tasks.send_monthly_summaries_task",
        "schedule": crontab(hour=8, minute=0, day_of_month=1),
    },
    "lead-follow-up-automation": {
        "task": "app.workers.tasks.run_follow_up_automation_task",
        "schedule": crontab(hour=9, minute=0),
    },
    "send-pending-dms": {
        "task": "app.workers.tasks.send_pending_dms_task",
        "schedule": 30.0,
    },
    "poll-video-generations": {
        "task": "app.workers.tasks.poll_video_generations_task",
        "schedule": 30.0,
    },
}

celery_app.autodiscover_tasks(["app.workers"])
