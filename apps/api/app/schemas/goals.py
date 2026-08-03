from pydantic import BaseModel

from app.models.post import PostFormat, PostGoal


class GoalRecommendation(BaseModel):
    goal: PostGoal
    recommended_format: PostFormat
    reason: str


class GoalPerformance(BaseModel):
    goal: PostGoal
    published_posts: int
    leads: int
    hot_leads: int
    won_value: float
    leads_per_post: float


class GoalPerformanceReport(BaseModel):
    performance: list[GoalPerformance]

    unattributed_leads: int
    """Came in on their own, but we can't tell which post earned them. A rising
    number here means the tracking is broken, not that the content is working."""

    outbound_leads: int = 0
    """Sourced by us rather than by them. Counted apart from unattributed, because
    their origin is known — it just isn't a post."""

    best_goal: PostGoal | None = None
    recommendations: list[GoalRecommendation]
