import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.post import Platform


class MetricKind(StrEnum):
    FOLLOWERS = "followers"
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    REVENUE = "revenue"
    CONVERSIONS = "conversions"
    WATCH_TIME_SECONDS = "watch_time_seconds"
    CTR = "ctr"
    RETENTION = "retention"


class Metric(BaseModel):
    """Daily rollup of a single metric for a single platform, owned by a user.
    Populated by platform integrations (see app/integrations/) or CSV import; the
    dashboard aggregates over this table rather than hitting live platform APIs on
    every request."""

    __tablename__ = "metrics"

    owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="metric_platform"), nullable=False)
    kind: Mapped[MetricKind] = mapped_column(Enum(MetricKind, name="metric_kind"), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    post_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)
