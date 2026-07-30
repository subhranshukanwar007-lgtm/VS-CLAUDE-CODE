from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models.ai_generation import AIGeneration, AIGenerationKind
from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.deal import Deal, DealStatus
from app.models.lead import Lead, LeadIntent
from app.models.metric import Metric, MetricKind
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


def _sales_context(db: Session, user: User) -> str:
    """The Sales Agent's job is to close specific people, so it gets the actual hot
    and warm leads by name rather than a count."""

    leads = db.scalars(
        select(Lead)
        .where(Lead.owner_id == user.id, Lead.intent.in_((LeadIntent.HOT, LeadIntent.WARM)))
        .order_by(Lead.intent_scored_at.desc())
        .limit(10)
    ).all()
    if not leads:
        return (
            "Account context: no leads currently scored hot or warm. Say so if the user "
            "asks who to contact."
        )
    lines = "\n".join(
        f"- {lead.full_name} ({lead.intent.value}, from {lead.source.value}): "
        f"{lead.intent_reason or 'no reason recorded'}"
        for lead in leads
    )
    return f"Account context — leads worth contacting right now:\n{lines}"


def _money_context(db: Session, user: User) -> str:
    """Real money figures, so the Money Agent reasons from actuals instead of
    inventing plausible-looking numbers."""

    since = date.today() - timedelta(days=30)
    revenue_30d = (
        db.scalar(
            select(func.coalesce(func.sum(Metric.value), 0)).where(
                Metric.owner_id == user.id,
                Metric.kind == MetricKind.REVENUE,
                Metric.recorded_on >= since,
            )
        )
        or 0
    )

    def _deal_agg(status: DealStatus) -> tuple[int, float]:
        row = db.execute(
            select(func.count(), func.coalesce(func.sum(Deal.value), 0))
            .join(Lead, Deal.lead_id == Lead.id)
            .where(Lead.owner_id == user.id, Deal.status == status)
        ).one()
        return int(row[0]), float(row[1])

    won_count, won_value = _deal_agg(DealStatus.WON)
    open_count, open_value = _deal_agg(DealStatus.OPEN)
    lost_count, _ = _deal_agg(DealStatus.LOST)

    closed = won_count + lost_count
    win_rate = f"{(won_count / closed * 100):.0f}%" if closed else "not enough closed deals to say"
    avg_deal = f"{(won_value / won_count):.2f}" if won_count else "no won deals yet"

    return (
        "Account context (real figures from this account's database):\n"
        f"- Revenue recorded in the last 30 days: {float(revenue_30d):.2f}\n"
        f"- Won deals: {won_count} totalling {won_value:.2f}\n"
        f"- Open pipeline: {open_count} deals totalling {open_value:.2f}\n"
        f"- Lost deals: {lost_count}\n"
        f"- Win rate on closed deals: {win_rate}\n"
        f"- Average won deal size: {avg_deal}\n"
        "Currency is whatever the deals were recorded in; do not assume USD. "
        "Ad spend and costs are not tracked in this system, so you cannot compute "
        "profit or ROAS — say so rather than guessing."
    )


_CONTEXT_BUILDERS = {
    "crm": _crm_context,
    "analytics": _analytics_context,
    "money": _money_context,
    "sales": _sales_context,
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
