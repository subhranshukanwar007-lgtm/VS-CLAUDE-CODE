"""Progress toward a follower goal, and whether the current rate will reach it.

A follower count is an outcome, not a lever — nobody can "do a follower". So this
module's job is to convert the goal into the things that *are* levers: how many
new followers per day the deadline demands, what the account is actually
managing, and how many reels a week that implies.

Reels specifically, because Instagram only pushes Reels to people who don't
already follow you. Stories and feed posts mostly reach existing followers, so a
follower target is a reel target.

The projection is deliberately plain arithmetic over real recorded history — no
model, no claim of prediction. When there isn't enough history to measure a rate,
this returns nulls rather than a confident-looking number, because an invented
ETA is worse than no ETA: it gets planned against.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.metric import Metric, MetricKind
from app.models.post import Post, PostFormat, PostStatus
from app.models.user import User
from app.schemas.growth import GrowthTarget
from app.services.automation_settings_service import get_or_create

# Below this many days of follower history, a daily rate is noise rather than a
# measurement, so no ETA is offered.
_MIN_DAYS_FOR_RATE = 7
_WINDOW_DAYS = 30


def _followers_on_or_before(db: Session, user_id, cutoff: date) -> tuple[date, float] | None:
    row = db.execute(
        select(Metric.recorded_on, Metric.value)
        .where(
            Metric.owner_id == user_id,
            Metric.kind == MetricKind.FOLLOWERS,
            Metric.recorded_on <= cutoff,
        )
        .order_by(Metric.recorded_on.desc())
        .limit(1)
    ).first()
    return (row[0], float(row[1])) if row else None


def _reels_since(db: Session, user_id, since: date) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Post)
            .where(
                Post.author_id == user_id,
                Post.format == PostFormat.REEL,
                Post.status == PostStatus.PUBLISHED,
                Post.published_at >= since,
            )
        )
        or 0
    )


def get_growth_target(db: Session, user: User, today: date | None = None) -> GrowthTarget:
    today = today or date.today()
    setting = get_or_create(db, user.id)

    latest = _followers_on_or_before(db, user.id, today)
    current = latest[1] if latest else 0.0

    earlier = _followers_on_or_before(db, user.id, today - timedelta(days=_WINDOW_DAYS))
    followers_gained = None
    per_day_actual = None
    if latest and earlier and earlier[0] < latest[0]:
        elapsed = (latest[0] - earlier[0]).days
        if elapsed >= _MIN_DAYS_FOR_RATE:
            followers_gained = latest[1] - earlier[1]
            per_day_actual = followers_gained / elapsed

    goal = setting.follower_goal
    deadline = setting.goal_deadline
    remaining = max(0.0, goal - current) if goal else None

    days_left = (deadline - today).days if deadline else None
    per_day_required = None
    if remaining is not None and days_left is not None and days_left > 0:
        per_day_required = remaining / days_left

    # Only project when a rate was actually measured and it's positive; a flat or
    # falling account has no honest ETA.
    projected_date = None
    on_pace = None
    if remaining is not None and per_day_actual is not None and per_day_actual > 0:
        days_needed = remaining / per_day_actual
        if days_needed < 365 * 50:  # guard against absurd dates from a near-zero rate
            projected_date = today + timedelta(days=int(days_needed))
        if per_day_required is not None:
            on_pace = per_day_actual >= per_day_required

    reels_this_week = _reels_since(db, user.id, today - timedelta(days=7))

    return GrowthTarget(
        follower_goal=goal,
        goal_deadline=deadline,
        current_followers=current,
        remaining=remaining,
        percent_complete=round(current / goal * 100, 1) if goal else None,
        followers_gained_30d=followers_gained,
        per_day_actual=round(per_day_actual, 1) if per_day_actual is not None else None,
        per_day_required=round(per_day_required, 1) if per_day_required is not None else None,
        days_left=days_left,
        projected_date=projected_date,
        on_pace=on_pace,
        reels_this_week=reels_this_week,
        reels_per_week_target=setting.reels_per_week_target,
        has_enough_history=per_day_actual is not None,
    )
