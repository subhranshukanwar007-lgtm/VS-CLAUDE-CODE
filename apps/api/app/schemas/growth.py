from datetime import date

from pydantic import BaseModel


class GrowthTarget(BaseModel):
    """Progress toward a follower goal, expressed as levers rather than wishes.

    Every optional field is None when it cannot be computed honestly — most often
    because there isn't enough recorded follower history to measure a rate.
    `has_enough_history` says which case you're in, so the UI can show "keep
    posting, not enough data yet" instead of a fabricated ETA.
    """

    follower_goal: int | None
    goal_deadline: date | None
    current_followers: float
    remaining: float | None
    percent_complete: float | None

    followers_gained_30d: float | None
    per_day_actual: float | None
    per_day_required: float | None
    days_left: int | None
    projected_date: date | None
    on_pace: bool | None

    reels_this_week: int
    reels_per_week_target: int
    has_enough_history: bool
