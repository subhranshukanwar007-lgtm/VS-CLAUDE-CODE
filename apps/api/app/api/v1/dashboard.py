from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import get_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(
    window_days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DashboardOverview:
    return get_dashboard_overview(db, user, window_days=window_days)
