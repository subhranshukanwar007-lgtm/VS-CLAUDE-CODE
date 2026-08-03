"""Buying-intent scoring for leads.

The problem this solves: engagement capture turns every commenter into a lead, so
the CRM fills up fast and the one person who actually asked "how much?" gets
buried. This reads what each lead actually said and flags the ones worth a human
conversation right now.

Two layers, deliberately:

1. A keyword pre-check (`_rule_based_intent`) that catches unambiguous buying
   language — "price", "how do i join", "dm me the link". It costs nothing, works
   with no AI key configured, and covers the highest-value case.
2. An AI pass that reads the full conversation for the cases rules miss (interest
   expressed indirectly, or in Hinglish, or across several comments).

The AI is asked for a strict two-line format rather than free prose so the result
is parseable. If it answers in an unexpected shape, `_parse_ai_verdict` returns
None and the rule-based verdict stands — a malformed model response must never
silently downgrade a HOT lead to cold.

Scoring never overwrites a *higher* score with a lower one on re-analysis: someone
who asked about price yesterday is still a hot lead today even if their newest
comment is just an emoji.
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.automation_setting import LANGUAGE_INSTRUCTIONS
from app.models.lead import Lead, LeadIntent
from app.models.note import Note
from app.models.notification import NotificationType
from app.models.user import User
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_provider
from app.services.automation_settings_service import get_or_create
from app.services.notification_service import notify

logger = logging.getLogger("intent")

# Unambiguous buying signals. Matched case-insensitively on word boundaries so
# "price" doesn't fire on "surprise".
_HOT_PATTERNS = (
    r"\bprice\b",
    r"\bpricing\b",
    r"\bcost\b",
    r"\bhow much\b",
    r"\bkitna\b",  # Hinglish: "how much"
    r"\bkitne ka\b",
    r"\bfees?\b",
    r"\bcharges?\b",
    r"\bhow (?:do|can) i (?:join|start|buy|sign up|enroll)\b",
    r"\bjoin karna\b",
    r"\bwhere (?:do|can) i (?:pay|sign up|buy)\b",
    r"\bsend (?:me )?(?:the )?(?:link|details|dm)\b",
    r"\bdm me\b",
    r"\binterested\b",
    r"\bi want to (?:join|buy|start)\b",
    r"\bavailable\b",
    r"\bslots?\b",
    r"\bbook(?:ing)?\b",
)

_WARM_PATTERNS = (
    r"\bhow (?:do|does|to)\b",
    r"\bwhat (?:should|do) i\b",
    r"\bcan you (?:help|explain|tell)\b",
    r"\badvice\b",
    r"\bstruggling\b",
    r"\bproblem\b",
    r"\bhelp me\b",
    r"\bkaise\b",  # Hinglish: "how"
    r"\bplease guide\b",
    r"\?",  # asked a question at all
)

_INTENT_RANK = {
    LeadIntent.UNKNOWN: 0,
    LeadIntent.COLD: 1,
    LeadIntent.WARM: 2,
    LeadIntent.HOT: 3,
}

_MAX_NOTES_CONSIDERED = 20


def lead_conversation(db: Session, lead: Lead) -> str:
    """Everything this lead has said, oldest first, as plain text. Notes are where
    engagement capture records each comment, so this is the lead's own words."""

    notes = db.scalars(
        select(Note)
        .where(Note.lead_id == lead.id)
        .order_by(Note.created_at.desc())
        .limit(_MAX_NOTES_CONSIDERED)
    ).all()
    return "\n".join(note.body for note in reversed(notes) if note.body)


def _rule_based_intent(text: str) -> tuple[LeadIntent, str | None]:
    lowered = text.lower()
    for pattern in _HOT_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            return LeadIntent.HOT, f'Asked about buying: "{match.group(0)}"'
    for pattern in _WARM_PATTERNS:
        if re.search(pattern, lowered):
            return LeadIntent.WARM, "Asked a question about the topic"
    return LeadIntent.COLD, "No question or buying signal yet"


_VERDICT_RE = re.compile(r"\b(hot|warm|cold)\b", re.IGNORECASE)


def _parse_ai_verdict(raw: str) -> tuple[LeadIntent, str] | None:
    """Expects:
        INTENT: hot
        REASON: asked what the program costs

    Returns None if the response doesn't contain a recognisable verdict, so the
    caller keeps the rule-based result instead of trusting a garbled reply.
    """

    intent_line = None
    reason_line = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("intent:"):
            intent_line = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("reason:"):
            reason_line = stripped.split(":", 1)[1].strip()

    if intent_line is None:
        return None
    match = _VERDICT_RE.search(intent_line)
    if match is None:
        return None

    intent = LeadIntent(match.group(1).lower())
    reason = (reason_line or "Scored by AI from the lead's messages")[:500]
    return intent, reason


def _apply_score(db: Session, lead: Lead, intent: LeadIntent, reason: str) -> Lead:
    """Persist a score and notify on the transition into HOT.

    Notification fires only on the *transition*, so a lead that stays hot across
    repeated scoring runs doesn't re-notify every time. Scores are never
    downgraded — someone who asked the price yesterday is still worth talking to
    today even if their newest comment is just an emoji.
    """

    previous = lead.intent
    if _INTENT_RANK[intent] < _INTENT_RANK[previous]:
        lead.intent_scored_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(lead)
        return lead

    lead.intent = intent
    lead.intent_reason = reason
    lead.intent_scored_at = datetime.now(timezone.utc)
    db.commit()

    if intent == LeadIntent.HOT and previous != LeadIntent.HOT:
        notify(
            db,
            lead.owner_id,
            NotificationType.HOT_LEAD,
            title=f"\U0001f525 {lead.full_name} is ready to talk",
            body=reason,
            link=f"/crm?lead={lead.id}",
        )
        logger.info("lead %s became HOT: %s", lead.id, reason)

    db.refresh(lead)
    return lead


def score_lead_fast(db: Session, lead: Lead) -> Lead:
    """Rule-based scoring only — no network, no AI key needed, returns instantly.

    This is what the Meta webhook calls. Meta expects a webhook to respond
    quickly and retries on timeout, so an AI round-trip cannot happen inline; but
    the highest-value case ("how much?") is exactly what the keyword rules catch,
    so the hot-lead notification still lands within seconds of the comment. The
    AI pass refines the rest later via `score_all_unscored`.
    """

    conversation = lead_conversation(db, lead)
    if not conversation.strip():
        return lead
    intent, reason = _rule_based_intent(conversation)
    return _apply_score(db, lead, intent, reason or "")


async def score_lead(
    db: Session,
    lead: Lead,
    *,
    use_ai: bool = True,
    provider_kind: AIProviderKind | None = None,
) -> Lead:
    """Full scoring: keyword rules plus an AI reading of the conversation."""

    conversation = lead_conversation(db, lead)
    if not conversation.strip():
        # Nothing said yet — leave the score alone rather than recording a
        # confident "cold" we have no evidence for.
        return lead

    intent, reason = _rule_based_intent(conversation)

    if use_ai:
        try:
            verdict = await _ai_intent(db, lead, conversation, provider_kind)
        except AIProviderError as exc:
            # No AI key, or the provider is down. The rule-based score still stands.
            logger.info("intent AI pass unavailable for lead %s: %s", lead.id, exc)
        else:
            if verdict is not None:
                ai_intent, ai_reason = verdict
                # Trust whichever layer saw the stronger signal.
                if _INTENT_RANK[ai_intent] > _INTENT_RANK[intent]:
                    intent, reason = ai_intent, ai_reason
                elif ai_intent == intent:
                    reason = ai_reason

    return _apply_score(db, lead, intent, reason or "")


async def _ai_intent(
    db: Session, lead: Lead, conversation: str, provider_kind: AIProviderKind | None
) -> tuple[LeadIntent, str] | None:
    provider = get_provider(provider_kind)
    setting = get_or_create(db, lead.owner_id)
    language = LANGUAGE_INSTRUCTIONS[setting.reply_language]

    system = (
        "You classify how close a social-media follower is to buying, based only on "
        "what they wrote. Answer in exactly two lines and nothing else:\n"
        "INTENT: hot|warm|cold\n"
        "REASON: <one short sentence>\n\n"
        "hot = they showed a buying signal (asked the price, asked how to join, "
        "asked about availability, asked for a link, said they want in).\n"
        "warm = genuine interest or a real question about the topic, but no buying "
        "signal.\n"
        "cold = a compliment, an emoji, or a generic reaction.\n"
        f"The messages may be in English, Hindi or Hinglish. {language}"
    )
    prompt = (
        f"Lead name: {lead.full_name}\n"
        f"Came from: {lead.source.value}\n\n"
        f"What they wrote:\n{conversation}"
    )

    raw = await provider.generate(prompt, system=system, max_tokens=120)
    return _parse_ai_verdict(raw)


async def score_all_unscored(db: Session, user: User, *, use_ai: bool = True) -> int:
    """Score every lead of `user`'s that has never been scored. Called by the beat
    task. Per-lead failures are logged and skipped so one bad lead can't stop the
    batch."""

    leads = db.scalars(
        select(Lead).where(Lead.owner_id == user.id, Lead.intent_scored_at.is_(None))
    ).all()

    scored = 0
    for lead in leads:
        try:
            await score_lead(db, lead, use_ai=use_ai)
            scored += 1
        except Exception:  # noqa: BLE001 - one bad lead must not kill the batch
            logger.exception("failed to score lead %s", lead.id)
            db.rollback()
    return scored
