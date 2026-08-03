from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.goals import GoalPerformanceReport, GoalRecommendation
from app.services.goal_service import get_goal_performance, recommendations

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/recommendations", response_model=list[GoalRecommendation])
def read_recommendations() -> list[GoalRecommendation]:
    """Which format each content goal is usually best served by. Advisory — shown
    next to the goal picker when scheduling a post."""

    return recommendations()


@router.get("/performance", response_model=GoalPerformanceReport)
def read_performance(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> GoalPerformanceReport:
    """Which of your content goals actually produce leads, hot leads and revenue —
    measured by tracing each lead back to the post that earned it, not by views."""

    return get_goal_performance(db, user)
