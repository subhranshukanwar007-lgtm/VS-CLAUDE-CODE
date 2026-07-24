from sqlalchemy.orm import Session

from app.models.ai_generation import AIGeneration, AIGenerationKind
from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.user import User
from app.services.ai.factory import get_provider


async def _run(
    db: Session,
    user: User,
    kind: AIGenerationKind,
    prompt: str,
    system: str | None,
    provider_kind: AIProviderKind | None,
    max_tokens: int = 1024,
) -> AIGeneration:
    provider = get_provider(provider_kind)
    result_text = await provider.generate(prompt, system=system, max_tokens=max_tokens)

    record = AIGeneration(
        user_id=user.id,
        kind=kind,
        provider=AIProviderKind(provider.name),
        model=provider.model,
        prompt=prompt,
        result=result_text,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


async def generate_caption(
    db: Session, user: User, topic: str, platform: str, tone: str, brand_voice: str | None, provider: AIProviderKind | None
) -> AIGeneration:
    system = (
        "You are an expert social media copywriter. Write a single, ready-to-post caption "
        f"for {platform}. Tone: {tone}. Keep it platform-appropriate, no markdown formatting, "
        "no hashtags (those are generated separately)."
    )
    if brand_voice:
        system += f" Match this brand voice: {brand_voice}"
    return await _run(db, user, AIGenerationKind.CAPTION, topic, system, provider, max_tokens=400)


async def generate_hashtags(
    db: Session, user: User, topic: str, count: int, provider: AIProviderKind | None
) -> AIGeneration:
    system = (
        f"You generate exactly {count} relevant, high-performing social media hashtags for the "
        "given topic. Output only the hashtags, space-separated, each starting with #. No commentary."
    )
    return await _run(db, user, AIGenerationKind.HASHTAGS, topic, system, provider, max_tokens=300)


async def generate_script(
    db: Session,
    user: User,
    topic: str,
    format: str,
    duration_seconds: int,
    brand_voice: str | None,
    provider: AIProviderKind | None,
) -> AIGeneration:
    system = (
        f"You are a short-form video scriptwriter. Write a {format} script of about "
        f"{duration_seconds} seconds. Structure it as: HOOK (first 3 seconds), BODY, and CTA. "
        "Include on-screen text suggestions in brackets."
    )
    if brand_voice:
        system += f" Match this brand voice: {brand_voice}"
    return await _run(db, user, AIGenerationKind.SCRIPT, topic, system, provider, max_tokens=800)
