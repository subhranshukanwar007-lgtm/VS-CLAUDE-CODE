import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_generation import AIGeneration, AIGenerationKind
from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.lead import Lead, LeadStatus
from app.models.note import Note
from app.models.notification import NotificationType
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_provider
from app.services.notification_service import notify

logger = logging.getLogger("followup")

ACTIVE_LEAD_STATUSES = (LeadStatus.LEAD, LeadStatus.PROSPECT)


def _last_activity(db: Session, lead: Lead) -> datetime:
    """Most recent signal of activity on a lead: its own last update, its newest
    note, its newest task, or the last time follow-up automation touched it —
    whichever is most recent. This is what "gone quiet" is measured against."""

    latest_note = db.scalar(select(func.max(Note.created_at)).where(Note.lead_id == lead.id))
    latest_task = db.scalar(select(func.max(Task.created_at)).where(Task.lead_id == lead.id))

    candidates = [lead.updated_at, lead.created_at]
    if latest_note is not None:
        candidates.append(latest_note)
    if latest_task is not None:
        candidates.append(latest_task)
    if lead.last_follow_up_at is not None:
        candidates.append(lead.last_follow_up_at)
    return max(candidates)


def is_lead_stale(db: Session, lead: Lead) -> bool:
    """Whether `lead` currently needs a follow-up, judged against its own owner's
    follow_up_days setting (not the viewing user's) — so this stays correct when
    an admin is browsing another member's leads."""

    owner = lead.owner
    if owner is None or owner.follow_up_days <= 0 or lead.status not in ACTIVE_LEAD_STATUSES:
        return False
    threshold = datetime.now(timezone.utc) - timedelta(days=owner.follow_up_days)
    return _last_activity(db, lead) <= threshold


def get_stale_leads(db: Session, user: User) -> list[Lead]:
    """Active (lead/prospect) leads owned by `user` with no activity in the last
    `user.follow_up_days` days. Returns [] when follow-up automation is disabled
    (follow_up_days <= 0)."""

    if user.follow_up_days <= 0:
        return []

    threshold = datetime.now(timezone.utc) - timedelta(days=user.follow_up_days)
    leads = db.scalars(
        select(Lead).where(Lead.owner_id == user.id, Lead.status.in_(ACTIVE_LEAD_STATUSES))
    ).all()
    return [lead for lead in leads if _last_activity(db, lead) <= threshold]


async def generate_follow_up_message(
    db: Session, user: User, lead: Lead, provider_kind: AIProviderKind | None = None
) -> AIGeneration:
    system = (
        "You are a sales follow-up specialist. Write a short, warm, non-pushy follow-up message "
        "for a lead who has gone quiet. One or two sentences, no generic filler, reference their "
        "specific situation. Output only the message text, nothing else."
    )
    days_quiet = (datetime.now(timezone.utc) - _last_activity(db, lead)).days
    prompt_lines = [
        f"Lead name: {lead.full_name}",
        f"Company: {lead.company or 'unknown'}",
        f"Source: {lead.source.value}",
        f"Status: {lead.status.value}",
        f"Days since last activity: {days_quiet}",
    ]
    if lead.estimated_value:
        prompt_lines.append(f"Estimated deal value: ${lead.estimated_value}")
    prompt = "\n".join(prompt_lines)

    provider = get_provider(provider_kind)
    result_text = await provider.generate(prompt, system=system, max_tokens=300)

    record = AIGeneration(
        user_id=user.id,
        kind=AIGenerationKind.FOLLOW_UP,
        provider=AIProviderKind(provider.name),
        model=provider.model,
        prompt=prompt,
        result=result_text,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


async def trigger_follow_up(
    db: Session, user: User, lead: Lead, provider_kind: AIProviderKind | None = None
) -> tuple[AIGeneration, Task]:
    """Generate a follow-up draft for `lead`, create a reminder Task carrying that
    draft, mark the lead's `last_follow_up_at`, and notify the owner. Used by both
    the manual "suggest follow-up" endpoint and the daily automation task."""

    generation = await generate_follow_up_message(db, user, lead, provider_kind)

    now = datetime.now(timezone.utc)
    task = Task(
        assignee_id=user.id,
        lead_id=lead.id,
        title=f"Follow up with {lead.full_name}",
        description=generation.result,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        due_at=now,
    )
    db.add(task)
    lead.last_follow_up_at = now
    db.commit()
    db.refresh(task)

    notify(
        db,
        user.id,
        NotificationType.FOLLOW_UP_SUGGESTED,
        title=f"Follow-up suggested: {lead.full_name}",
        body=generation.result[:200],
        link=f"/crm?lead={lead.id}",
    )
    return generation, task


async def run_follow_up_automation_for_user(db: Session, user: User) -> int:
    stale_leads = get_stale_leads(db, user)
    triggered = 0
    for lead in stale_leads:
        try:
            await trigger_follow_up(db, user, lead)
            triggered += 1
        except AIProviderError as exc:
            logger.info("skipping follow-up automation for user %s: %s", user.id, exc)
            break
    return triggered


async def run_follow_up_automation(db: Session) -> int:
    """Entry point for the daily Celery beat task: runs stale-lead detection and
    AI follow-up drafting for every active user with automation enabled."""

    users = db.scalars(select(User).where(User.is_active.is_(True), User.follow_up_days > 0)).all()
    total = 0
    for user in users:
        total += await run_follow_up_automation_for_user(db, user)
    return total
