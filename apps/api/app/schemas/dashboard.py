from datetime import date

from pydantic import BaseModel

from app.models.post import Platform


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
