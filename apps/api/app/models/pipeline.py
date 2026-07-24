from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PipelineStage(BaseModel):
    """A Kanban-style stage in the sales pipeline (e.g. New, Contacted, Qualified, Won, Lost)."""

    __tablename__ = "pipeline_stages"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    is_won_stage: Mapped[bool] = mapped_column(default=False)
    is_lost_stage: Mapped[bool] = mapped_column(default=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="stage")  # noqa: F821
    deals: Mapped[list["Deal"]] = relationship(back_populates="stage")  # noqa: F821
