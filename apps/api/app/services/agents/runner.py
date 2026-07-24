from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models.ai_generation import AIGeneration, AIGenerationKind
from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.deal import Deal, DealStatus
from app.models.lead import Lead
from app.models.post import Post, PostStatus
from app.models.user import User
from app.services.agents.personas import AGENT_PERSONAS, DATA_GROUNDED_AGENTS
from app.services.ai.factory import get_provider


def _crm_context(db: Session, user: User) -> str:
    total_leads = db.scalar(select(func.count()).select_from(Lead).where(Lead.owner_id == user.id)) or 0
    open_value = (
        db.scalar(
            select(func.coalesce(func.sum(Deal.value), 0))
            .join(Lead, Deal.lead_id == Lead.id)
            .where(Lead.owner_id == user.id, Deal.status == DealStatus.OPEN)
        )
        or 0
    )
    return f"Account context: {total_leads} total leads, ${float(open_value):.2f} in open pipeline value."


def _analytics_context(db: Session, user: User) -> str:
    published = (
        db.scalar(
            select(func.count()).select_from(Post).where(Post.author_id == user.id, Post.status == PostStatus.PUBLISHED)
        )
        or 0
    )
    return f"Account context: {published} posts published to date."


def _scheduler_context(db: Session, user: User) -> str:
    queued = (
        db.scalar(
            select(func.count())
            .select_from(Post)
            .where(Post.author_id == user.id, Post.status == PostStatus.SCHEDULED)
        )
        or 0
    )
    return f"Account context: {queued} posts currently scheduled/queued."


_CONTEXT_BUILDERS = {
    "crm": _crm_context,
    "analytics": _analytics_context,
    "scheduler": _scheduler_context,
}


async def run_agent(
    db: Session, user: User, agent: str, message: str, provider_kind: AIProviderKind | None
) -> AIGeneration:
    persona = AGENT_PERSONAS.get(agent)
    if persona is None:
        raise ForbiddenError(f"Unknown agent '{agent}'. Valid agents: {', '.join(sorted(AGENT_PERSONAS))}")

    system = persona
    if agent in DATA_GROUNDED_AGENTS:
        system = f"{persona}\n\n{_CONTEXT_BUILDERS[agent](db, user)}"

    provider = get_provider(provider_kind)
    result_text = await provider.generate(message, system=system, max_tokens=800)

    record = AIGeneration(
        user_id=user.id,
        kind=AIGenerationKind.AGENT_CHAT,
        provider=AIProviderKind(provider.name),
        model=provider.model,
        prompt=f"[{agent}] {message}",
        result=result_text,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
