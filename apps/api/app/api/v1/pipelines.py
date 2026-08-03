from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.pipeline import PipelineStage
from app.models.user import User
from app.schemas.pipeline import PipelineStageCreate, PipelineStageRead, PipelineStageUpdate

router = APIRouter(prefix="/pipeline-stages", tags=["crm"])


@router.get("", response_model=list[PipelineStageRead])
def list_stages(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[PipelineStage]:
    return list(db.scalars(select(PipelineStage).order_by(PipelineStage.order)))


@router.post("", response_model=PipelineStageRead, status_code=201)
def create_stage(
    payload: PipelineStageCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> PipelineStage:
    stage = PipelineStage(**payload.model_dump())
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


@router.patch("/{stage_id}", response_model=PipelineStageRead)
def update_stage(
    stage_id: UUID,
    payload: PipelineStageUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PipelineStage:
    stage = db.get(PipelineStage, stage_id)
    if stage is None:
        raise NotFoundError("Pipeline stage")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(stage, field, value)
    db.commit()
    db.refresh(stage)
    return stage


@router.delete("/{stage_id}", status_code=204)
def delete_stage(stage_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> None:
    stage = db.get(PipelineStage, stage_id)
    if stage is None:
        raise NotFoundError("Pipeline stage")
    db.delete(stage)
    db.commit()
