"""Content-goal performance: which kind of content actually produces leads.

Views are not the point. A reel with 40,000 views that produced no leads lost to
a story with 900 views that produced seven. This module answers that by joining
leads back to the post that earned them (`Lead.source_post_id`, set by engagement
capture) and grouping by the post's goal.

Honest limits, stated because they change how the numbers should be read:

- Attribution only covers leads captured through the Meta comment webhook. Someone
  who DMs you directly, or who you add by hand, has no source post — those are
  reported separately as unattributed rather than silently spread across goals.
- A post published outside this app has no `external_post_id` to match on, so its
  leads land in unattributed too.
- Deal value is credited to the goal of the post that produced the lead. If a lead
  came from several posts, only the first is credited (engagement capture does not
  rewrite attribution on later comments).
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealStatus
from app.models.lead import Lead, LeadIntent, LeadSource
from app.models.post import RECOMMENDED_FORMATS, Post, PostGoal, PostStatus
from app.models.user import User
from app.schemas.goals import GoalPerformance, GoalPerformanceReport, GoalRecommendation


def recommendations() -> list[GoalRecommendation]:
    """The format each goal is usually best served by. Advisory: the app suggests,
    the user decides."""

    return [
        GoalRecommendation(goal=goal, recommended_format=fmt, reason=reason)
        for goal, (fmt, reason) in RECOMMENDED_FORMATS.items()
    ]


def get_goal_performance(db: Session, user: User) -> GoalPerformanceReport:
    rows = db.execute(
        select(
            Post.goal,
            func.count(func.distinct(Post.id)),
            func.count(func.distinct(Lead.id)),
            # count(distinct ...) FILTER is not valid syntax; count a CASE instead.
            func.count(
                func.distinct(case((Lead.intent == LeadIntent.HOT, Lead.id), else_=None))
            ),
        )
        .select_from(Post)
        .outerjoin(Lead, Lead.source_post_id == Post.id)
        .where(Post.author_id == user.id, Post.status == PostStatus.PUBLISHED)
        .group_by(Post.goal)
    ).all()

    counts = {row[0]: (int(row[1]), int(row[2]), int(row[3])) for row in rows}

    # Won deal value per goal, traced lead -> source post -> goal.
    value_rows = db.execute(
        select(Post.goal, func.coalesce(func.sum(Deal.value), 0))
        .select_from(Deal)
        .join(Lead, Deal.lead_id == Lead.id)
        .join(Post, Lead.source_post_id == Post.id)
        .where(Lead.owner_id == user.id, Deal.status == DealStatus.WON)
        .group_by(Post.goal)
    ).all()
    won_value = {row[0]: float(row[1]) for row in value_rows}

    performance = []
    for goal in PostGoal:
        posts, leads, hot = counts.get(goal, (0, 0, 0))
        performance.append(
            GoalPerformance(
                goal=goal,
                published_posts=posts,
                leads=leads,
                hot_leads=hot,
                won_value=won_value.get(goal, 0.0),
                leads_per_post=round(leads / posts, 2) if posts else 0.0,
            )
        )

    # Outbound leads are excluded rather than counted as unattributed. They have a
    # known origin that simply isn't a post, so counting them here would make the
    # one number that says "your attribution is broken" go up every time outbound
    # works.
    unattributed = int(
        db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.owner_id == user.id,
                Lead.source_post_id.is_(None),
                Lead.source != LeadSource.OUTBOUND,
            )
        )
        or 0
    )

    outbound = int(
        db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.owner_id == user.id, Lead.source == LeadSource.OUTBOUND
            )
        )
        or 0
    )

    # "Best" means leads per post, not raw leads — otherwise whichever goal you
    # posted most often always wins. Requires at least one post and one lead, so a
    # goal with no data is never declared the winner.
    scored = [p for p in performance if p.published_posts > 0 and p.leads > 0]
    best = max(scored, key=lambda p: p.leads_per_post).goal if scored else None

    return GoalPerformanceReport(
        performance=performance,
        unattributed_leads=unattributed,
        outbound_leads=outbound,
        best_goal=best,
        recommendations=recommendations(),
    )
