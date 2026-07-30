from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import CommandCenter, DashboardOverview
from app.schemas.growth import GrowthTarget
from app.services.dashboard_service import get_command_center, get_dashboard_overview
from app.services.growth_service import get_growth_target

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(
    window_days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DashboardOverview:
    return get_dashboard_overview(db, user, window_days=window_days)


@router.get("/command-center", response_model=CommandCenter)
def command_center(
    window_days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CommandCenter:
    """Everything needing attention on one screen — hot leads, drafts awaiting
    approval, what's scheduled next, and the money numbers."""

    return get_command_center(db, user, window_days=window_days)


@router.get("/growth-target", response_model=GrowthTarget)
def growth_target(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> GrowthTarget:
    """Progress toward your follower goal, converted into levers: how many new
    followers a day the deadline needs, what you're actually getting, and how many
    reels a week that implies. Returns nulls rather than a guess when there isn't
    enough follower history to measure a rate."""

    return get_growth_target(db, user)
