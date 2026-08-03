"""Picks what to make today.

Two properties matter more than the selection cleverness:

1. **Stable across the day.** Today's pick is derived from the date, so
   refreshing the page doesn't reshuffle the plan. A suggestion that changes
   every time you look at it isn't a plan, it's a slot machine.

2. **Rotation by least-recently-used.** An idea used yesterday shouldn't
   resurface while a dozen untouched ones sit waiting. Never-used ideas come
   first, then oldest-used.

The goal bias is deliberately weak. If the goal-performance data says Stories
tagged `leads` are outperforming, today's pick tilts that way — but only when
there is genuinely enough data to say so. With four published posts there isn't,
and pretending otherwise would lock the creator into a pattern read from noise.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content_idea import SEED_IDEAS, ContentIdea, IdeaSource
from app.models.post import RECOMMENDED_FORMATS, PostFormat
from app.models.user import User
from app.schemas.idea import TodaysIdea

# Below this many published posts, per-goal performance is noise, so today's pick
# is not biased by it.
_MIN_POSTS_FOR_GOAL_BIAS = 10

# An idea used within this window is held back while fresher ones exist.
_COOLDOWN_DAYS = 30


def ensure_seeded(db: Session, owner_id: uuid.UUID) -> None:
    """Give a new account a starting bank. Seeded once — if the user deletes them
    all, that's a choice, and they don't come back."""

    existing = db.scalar(select(func.count()).select_from(ContentIdea).where(ContentIdea.owner_id == owner_id))
    if existing:
        return
    db.add_all(
        ContentIdea(
            owner_id=owner_id,
            problem=seed["problem"],
            angle=seed["angle"],
            suggested_goal=seed["suggested_goal"],
            suggested_format=RECOMMENDED_FORMATS[seed["suggested_goal"]][0],
            source=IdeaSource.SEED,
        )
        for seed in SEED_IDEAS
    )
    db.commit()


def _preferred_goal(db: Session, user: User):
    """The goal currently earning the most leads per post, or None when there
    isn't enough published history for that to mean anything."""

    from app.services.goal_service import get_goal_performance

    report = get_goal_performance(db, user)
    total_posts = sum(row.published_posts for row in report.performance)
    if total_posts < _MIN_POSTS_FOR_GOAL_BIAS:
        return None
    return report.best_goal


def get_todays_idea(db: Session, user: User, today: date | None = None) -> TodaysIdea:
    today = today or date.today()
    ensure_seeded(db, user.id)

    ideas = list(
        db.scalars(
            select(ContentIdea).where(ContentIdea.owner_id == user.id, ContentIdea.is_active.is_(True))
        )
    )
    if not ideas:
        return TodaysIdea(idea=None, reason="No active ideas. Add one in the Content Studio.", total_active=0)

    cutoff = datetime.now(timezone.utc) - timedelta(days=_COOLDOWN_DAYS)
    fresh = [i for i in ideas if i.last_used_at is None or i.last_used_at < cutoff]
    # If everything is inside the cooldown, fall back to the whole list rather than
    # returning nothing — a stale suggestion beats no suggestion.
    pool = fresh or ideas

    preferred = _preferred_goal(db, user)
    reason_parts = []
    if preferred is not None:
        on_goal = [i for i in pool if i.suggested_goal == preferred]
        if on_goal:
            pool = on_goal
            reason_parts.append(f"'{preferred.value}' posts are earning you the most leads per post")

    # Never-used first, then least recently used. Ties broken by id so the order is
    # deterministic rather than dependent on row order.
    pool.sort(key=lambda i: (i.last_used_at or datetime.min.replace(tzinfo=timezone.utc), str(i.id)))

    # Stable within a day: the same date always lands on the same index.
    chosen = pool[today.toordinal() % len(pool)]

    if chosen.times_used == 0:
        reason_parts.append("you haven't covered this one yet")
    else:
        reason_parts.append(f"last used {chosen.last_used_at.date().isoformat()}")

    return TodaysIdea(
        idea=chosen,
        reason=" — ".join(reason_parts).capitalize() if reason_parts else None,
        total_active=len(ideas),
    )


def mark_used(db: Session, idea: ContentIdea) -> ContentIdea:
    idea.times_used += 1
    idea.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(idea)
    return idea


def format_for(goal) -> PostFormat:
    return RECOMMENDED_FORMATS[goal][0]
