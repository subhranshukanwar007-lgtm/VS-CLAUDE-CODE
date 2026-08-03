from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

_PRIVILEGED = {UserRole.OWNER, UserRole.ADMIN}


def _get_visible_task(db: Session, user: User, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError("Task")
    if user.role not in _PRIVILEGED and task.assignee_id != user.id:
        raise ForbiddenError()
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Task]:
    query = select(Task)
    if user.role not in _PRIVILEGED:
        query = query.where(Task.assignee_id == user.id)
    return list(db.scalars(query.order_by(Task.due_at.asc().nulls_last())))


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Task:
    data = payload.model_dump()
    data["assignee_id"] = data.get("assignee_id") or user.id
    task = Task(**data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID, payload: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Task:
    task = _get_visible_task(db, user, task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    task = _get_visible_task(db, user, task_id)
    db.delete(task)
    db.commit()
