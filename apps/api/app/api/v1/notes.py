from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.deps import get_current_user
from app.models.lead import Lead
from app.models.note import Note
from app.models.user import User, UserRole
from app.schemas.note import NoteCreate, NoteRead

router = APIRouter(prefix="/notes", tags=["crm"])

_PRIVILEGED = {UserRole.OWNER, UserRole.ADMIN}


@router.get("", response_model=list[NoteRead])
def list_notes_for_lead(
    lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Note]:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead")
    if user.role not in _PRIVILEGED and lead.owner_id != user.id:
        raise ForbiddenError()
    return list(db.scalars(select(Note).where(Note.lead_id == lead_id).order_by(Note.created_at.desc())))


@router.post("", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Note:
    lead = db.get(Lead, payload.lead_id)
    if lead is None:
        raise NotFoundError("Lead")
    if user.role not in _PRIVILEGED and lead.owner_id != user.id:
        raise ForbiddenError()

    note = Note(lead_id=payload.lead_id, author_id=user.id, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    note = db.get(Note, note_id)
    if note is None:
        raise NotFoundError("Note")
    if user.role not in _PRIVILEGED and note.author_id != user.id:
        raise ForbiddenError()
    db.delete(note)
    db.commit()
