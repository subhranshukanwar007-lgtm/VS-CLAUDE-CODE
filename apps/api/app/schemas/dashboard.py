from datetime import date, datetime

from pydantic import BaseModel

from app.models.lead import LeadIntent
from app.models.post import Platform, PostFormat, PostStatus


class MetricPoint(BaseModel):
    date: date
    value: float


class DashboardSummary(BaseModel):
    followers: float
    views: float
    likes: float
    comments: float
    shares: float
    revenue: float
    conversions: float
    watch_time_seconds: float
    ctr: float
    retention: float
    followers_series: list[MetricPoint]
    views_series: list[MetricPoint]
    revenue_series: list[MetricPoint]


class TopPost(BaseModel):
    post_id: str
    platform: Platform
    caption: str | None
    score: float


class GrowthPrediction(BaseModel):
    """Simple linear trend projection over recent daily metric history. This is a
    transparent statistical estimate, not a claim of ML-grade forecasting — the
    `method` field always says so."""

    metric: str
    method: str = "linear_regression_7d"
    projected_30d: float
    confidence: float


class CrmSummary(BaseModel):
    total_leads: int
    open_deals: int
    won_deals: int
    pipeline_value: float
    won_value: float


class LeadBreakdown(BaseModel):
    """Lead counts grouped by one dimension — which platform they came from, or
    which country they're in. `label` is None for leads with that field unset
    (e.g. a lead whose country was never recorded)."""

    label: str | None
    count: int


class DashboardOverview(BaseModel):
    summary: DashboardSummary
    top_posts: list[TopPost]
    worst_posts: list[TopPost]
    predictions: list[GrowthPrediction]
    crm: CrmSummary
    leads_by_source: list[LeadBreakdown]
    leads_by_country: list[LeadBreakdown]


class HotLead(BaseModel):
    """A lead worth a conversation right now."""

    lead_id: str
    full_name: str
    source: str
    country: str | None
    intent: LeadIntent
    intent_reason: str | None
    scored_at: datetime | None


class PendingPost(BaseModel):
    """A post waiting on the user: either a draft to approve, or one scheduled and
    coming up. `is_overdue` marks a post whose scheduled time has already passed
    while auto-publish was off — those are the ones actually blocking."""

    post_id: str
    platform: Platform
    format: PostFormat
    caption: str | None
    status: PostStatus
    scheduled_at: datetime | None
    is_overdue: bool
    can_publish: bool


class MoneySnapshot(BaseModel):
    revenue_30d: float
    won_deals: int
    won_value: float
    open_deals: int
    open_pipeline_value: float


class CommandCenter(BaseModel):
    """Everything needing attention, on one screen.

    This exists because the same information was spread across six pages, so
    nobody could see the loop running. Every list here is either something to act
    on or a number that answers "is this working".
    """

    hot_leads: list[HotLead]
    needs_approval: list[PendingPost]
    upcoming: list[PendingPost]
    money: MoneySnapshot
    followers: float
    views_30d: float
    unread_notifications: int
    leads_by_source: list[LeadBreakdown]
    leads_by_country: list[LeadBreakdown]
    auto_publish: dict[str, bool]
