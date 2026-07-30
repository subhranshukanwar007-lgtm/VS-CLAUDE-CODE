from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealStatus
from app.models.lead import Lead
from app.models.metric import Metric, MetricKind
from app.models.post import Post
from app.models.user import User
from app.schemas.dashboard import (
    CrmSummary,
    DashboardOverview,
    DashboardSummary,
    GrowthPrediction,
    LeadBreakdown,
    MetricPoint,
    TopPost,
)

_SUM_KINDS = {
    MetricKind.VIEWS,
    MetricKind.LIKES,
    MetricKind.COMMENTS,
    MetricKind.SHARES,
    MetricKind.REVENUE,
    MetricKind.CONVERSIONS,
    MetricKind.WATCH_TIME_SECONDS,
}
_AVG_KINDS = {MetricKind.CTR, MetricKind.RETENTION}
_LATEST_KINDS = {MetricKind.FOLLOWERS}


def _kind_total(db: Session, user_id, kind: MetricKind, since: date) -> float:
    query = select(func.coalesce(func.sum(Metric.value), 0)).where(
        Metric.owner_id == user_id, Metric.kind == kind, Metric.recorded_on >= since
    )
    return float(db.scalar(query) or 0)


def _kind_avg(db: Session, user_id, kind: MetricKind, since: date) -> float:
    query = select(func.coalesce(func.avg(Metric.value), 0)).where(
        Metric.owner_id == user_id, Metric.kind == kind, Metric.recorded_on >= since
    )
    return float(db.scalar(query) or 0)


def _kind_latest(db: Session, user_id, kind: MetricKind) -> float:
    query = (
        select(Metric.value)
        .where(Metric.owner_id == user_id, Metric.kind == kind)
        .order_by(Metric.recorded_on.desc())
        .limit(1)
    )
    return float(db.scalar(query) or 0)


def _series(db: Session, user_id, kind: MetricKind, since: date) -> list[MetricPoint]:
    rows = db.execute(
        select(Metric.recorded_on, func.sum(Metric.value))
        .where(Metric.owner_id == user_id, Metric.kind == kind, Metric.recorded_on >= since)
        .group_by(Metric.recorded_on)
        .order_by(Metric.recorded_on)
    ).all()
    return [MetricPoint(date=row[0], value=float(row[1])) for row in rows]


def _linear_projection(series: list[MetricPoint], days_ahead: int = 30) -> tuple[float, float]:
    """Ordinary least squares fit over (day_index, value); returns (projected value
    `days_ahead` past the last point, R^2 as a naive confidence signal). Returns
    (0, 0) when there isn't enough data to fit a line."""

    n = len(series)
    if n < 2:
        return 0.0, 0.0

    xs = list(range(n))
    ys = [p.value for p in series]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0:
        return ys[-1], 0.0

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x

    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0:
        r_squared = 1.0
    else:
        predicted = [intercept + slope * x for x in xs]
        ss_res = sum((y - p) ** 2 for y, p in zip(ys, predicted, strict=True))
        r_squared = max(0.0, 1 - ss_res / ss_tot)

    projected_x = (n - 1) + days_ahead
    projected_value = intercept + slope * projected_x
    return max(0.0, projected_value), round(r_squared, 3)


def _top_posts(db: Session, user_id, since: date, limit: int, ascending: bool) -> list[TopPost]:
    engagement_kinds = (MetricKind.LIKES, MetricKind.COMMENTS, MetricKind.SHARES, MetricKind.VIEWS)
    score_col = func.sum(Metric.value)
    query = (
        select(Post.id, Post.platform, Post.caption, score_col)
        .join(Metric, Metric.post_id == Post.id)
        .where(Post.author_id == user_id, Metric.kind.in_(engagement_kinds), Metric.recorded_on >= since)
        .group_by(Post.id, Post.platform, Post.caption)
        .order_by(score_col.asc() if ascending else score_col.desc())
        .limit(limit)
    )
    rows = db.execute(query).all()
    return [
        TopPost(post_id=str(row[0]), platform=row[1], caption=row[2], score=float(row[3]))
        for row in rows
    ]


def _lead_breakdown(db: Session, user_id, column) -> list[LeadBreakdown]:
    """Group this user's leads by `column`, biggest group first. Used for the
    "where are my leads coming from" and "which countries" panels."""

    rows = db.execute(
        select(column, func.count())
        .where(Lead.owner_id == user_id)
        .group_by(column)
        .order_by(func.count().desc())
    ).all()
    return [
        LeadBreakdown(label=row[0].value if hasattr(row[0], "value") else row[0], count=int(row[1]))
        for row in rows
    ]


def get_dashboard_overview(db: Session, user: User, window_days: int = 30) -> DashboardOverview:
    since = date.today() - timedelta(days=window_days)

    summary = DashboardSummary(
        followers=_kind_latest(db, user.id, MetricKind.FOLLOWERS),
        views=_kind_total(db, user.id, MetricKind.VIEWS, since),
        likes=_kind_total(db, user.id, MetricKind.LIKES, since),
        comments=_kind_total(db, user.id, MetricKind.COMMENTS, since),
        shares=_kind_total(db, user.id, MetricKind.SHARES, since),
        revenue=_kind_total(db, user.id, MetricKind.REVENUE, since),
        conversions=_kind_total(db, user.id, MetricKind.CONVERSIONS, since),
        watch_time_seconds=_kind_total(db, user.id, MetricKind.WATCH_TIME_SECONDS, since),
        ctr=_kind_avg(db, user.id, MetricKind.CTR, since),
        retention=_kind_avg(db, user.id, MetricKind.RETENTION, since),
        followers_series=_series(db, user.id, MetricKind.FOLLOWERS, since),
        views_series=_series(db, user.id, MetricKind.VIEWS, since),
        revenue_series=_series(db, user.id, MetricKind.REVENUE, since),
    )

    predictions = []
    for kind, series in (
        ("followers", summary.followers_series),
        ("views", summary.views_series),
        ("revenue", summary.revenue_series),
    ):
        projected, confidence = _linear_projection(series)
        predictions.append(GrowthPrediction(metric=kind, projected_30d=projected, confidence=confidence))

    total_leads = int(db.scalar(select(func.count()).select_from(Lead).where(Lead.owner_id == user.id)) or 0)
    open_deals = int(
        db.scalar(
            select(func.count())
            .select_from(Deal)
            .join(Lead, Deal.lead_id == Lead.id)
            .where(Lead.owner_id == user.id, Deal.status == DealStatus.OPEN)
        )
        or 0
    )
    won_deals = int(
        db.scalar(
            select(func.count())
            .select_from(Deal)
            .join(Lead, Deal.lead_id == Lead.id)
            .where(Lead.owner_id == user.id, Deal.status == DealStatus.WON)
        )
        or 0
    )
    pipeline_value = float(
        db.scalar(
            select(func.coalesce(func.sum(Deal.value), 0))
            .join(Lead, Deal.lead_id == Lead.id)
            .where(Lead.owner_id == user.id, Deal.status == DealStatus.OPEN)
        )
        or 0
    )
    won_value = float(
        db.scalar(
            select(func.coalesce(func.sum(Deal.value), 0))
            .join(Lead, Deal.lead_id == Lead.id)
            .where(Lead.owner_id == user.id, Deal.status == DealStatus.WON)
        )
        or 0
    )

    return DashboardOverview(
        summary=summary,
        top_posts=_top_posts(db, user.id, since, limit=5, ascending=False),
        worst_posts=_top_posts(db, user.id, since, limit=5, ascending=True),
        predictions=predictions,
        crm=CrmSummary(
            total_leads=total_leads,
            open_deals=open_deals,
            won_deals=won_deals,
            pipeline_value=pipeline_value,
            won_value=won_value,
        ),
        leads_by_source=_lead_breakdown(db, user.id, Lead.source),
        leads_by_country=_lead_breakdown(db, user.id, Lead.country),
    )
