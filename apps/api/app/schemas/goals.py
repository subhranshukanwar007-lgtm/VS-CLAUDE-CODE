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
    best_goal: PostGoal | None = None
    recommendations: list[GoalRecommendation]
