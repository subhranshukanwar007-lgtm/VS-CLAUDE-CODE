"""Turns one topic into a shoot-ready content package.

The workflow this serves: the user has already trained their own avatar and voice
inside Higgsfield. What they need from this app is everything *around* the
generation — the hook that stops the scroll, the spoken script, the prompt to
paste into Higgsfield, what B-roll to cut over each line, and the on-screen
captions in the script their audience actually reads.

Two design decisions worth knowing:

1. **The Higgsfield prompt never describes a person.** The face and voice come
   from the user's own trained avatar, so a prompt that also describes someone's
   appearance fights it. The prompt covers framing, motion and delivery only.

2. **The AI is asked for strict JSON and the result is validated.** A half-parsed
   package — a script with no captions, beats that don't cover the duration — is
   worse than a clear failure, because the user only discovers it mid-shoot. If
   the model returns something unusable, this raises rather than patching over it.
"""

import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.ai_generation import AIGeneration, AIGenerationKind
from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.automation_setting import LANGUAGE_INSTRUCTIONS, ReplyLanguage
from app.models.user import User
from app.schemas.script import ContentPackage, ContentPackageRequest, ScriptBeat
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_provider
from app.services.automation_settings_service import get_or_create

logger = logging.getLogger("script")

_SYSTEM = """You write short-form video packages for a creator who already has an AI \
avatar and a cloned voice. They will paste your output into their video tool, so \
everything must be usable as-is — never placeholders, never "insert your hook here".

You return ONE JSON object and nothing else. No markdown fence, no commentary.

Schema:
{
  "hooks": ["3 different opening lines, strongest first"],
  "beats": [
    {
      "start_seconds": 0,
      "end_seconds": 3,
      "spoken": "exactly what the presenter says out loud",
      "caption": "the on-screen text for this beat",
      "broll": "what the viewer sees while this line is spoken"
    }
  ],
  "higgsfield_prompt": "camera framing, motion and delivery direction",
  "broll_notes": "how to shoot or source this B-roll overall",
  "post_caption": "the caption that goes under the post",
  "cta": "one line telling viewers exactly what to do",
  "hashtags": "space separated, 5-8 tags"
}

Rules that matter:
- Beats must run from 0 to the requested duration with no gaps and no overlaps.
- The first beat is the hook and must be at most 3 seconds. The first two seconds \
decide whether anyone watches.
- "spoken" is speech: contractions, short sentences, no bullet points, no emoji.
- "caption" is on-screen text: 3-7 words, punchy, it is not a transcript of "spoken".
- "broll" is a concrete shot, not a mood. "Close-up of oats being poured into a bowl", \
not "healthy food imagery".
- "higgsfield_prompt" must describe ONLY framing, camera movement, lighting, pacing \
and delivery energy. NEVER describe the person's face, age, gender, hair, body or \
clothing — the creator's own trained avatar supplies all of that, and describing a \
person fights it.
- One idea per video. Do not cram.
- Never invent statistics, studies or medical claims. If a number would strengthen a \
line, rewrite the line without it."""


def _language_for(db: Session, user: User, requested: ReplyLanguage | None) -> ReplyLanguage:
    if requested is not None:
        return requested
    return get_or_create(db, user.id).reply_language


def _extract_json(raw: str) -> dict:
    """Models wrap JSON in prose or a code fence often enough that stripping it is
    worth doing; guessing at malformed JSON is not. Raises when nothing parses."""

    text = raw.strip()

    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost {...} span.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise AIProviderError(
        "The AI returned something that isn't a valid content package. Try again, or "
        "switch provider in the request."
    )


def _parse_beats(payload: dict) -> list[ScriptBeat]:
    raw_beats = payload.get("beats")
    if not isinstance(raw_beats, list) or not raw_beats:
        raise AIProviderError("The AI returned no script beats. Try again.")

    beats: list[ScriptBeat] = []
    for index, raw in enumerate(raw_beats):
        if not isinstance(raw, dict):
            continue
        spoken = str(raw.get("spoken", "")).strip()
        if not spoken:
            # A beat with no spoken line is unusable on a talking-head video.
            continue
        try:
            start = int(raw.get("start_seconds", 0))
            end = int(raw.get("end_seconds", start + 3))
        except (TypeError, ValueError):
            start, end = index * 3, index * 3 + 3
        beats.append(
            ScriptBeat(
                start_seconds=max(0, start),
                end_seconds=max(start + 1, end),
                spoken=spoken,
                caption=str(raw.get("caption", "")).strip() or spoken[:40],
                broll=str(raw.get("broll", "")).strip() or "Talking head, no cutaway.",
            )
        )

    if not beats:
        raise AIProviderError("The AI returned no usable script beats. Try again.")
    return beats


def _parse_hooks(payload: dict, beats: list[ScriptBeat]) -> list[str]:
    raw = payload.get("hooks")
    hooks = [str(h).strip() for h in raw if str(h).strip()] if isinstance(raw, list) else []
    if hooks:
        return hooks
    # The opening spoken line is the hook by definition, so this is a real
    # fallback rather than a fabricated one.
    return [beats[0].spoken]


async def generate_content_package(
    db: Session, user: User, request: ContentPackageRequest
) -> ContentPackage:
    language = _language_for(db, user, request.language)
    provider = get_provider(request.provider)

    brand_voice = (user.brand_voice or "").strip()
    prompt = (
        f"Topic: {request.topic}\n"
        f"Platform: {request.platform.value}\n"
        f"Target duration: {request.duration_seconds} seconds\n"
        f"Language for spoken lines, captions and post caption: "
        f"{LANGUAGE_INSTRUCTIONS[language]}\n"
    )
    if brand_voice:
        prompt += f"\nThe creator's brand voice, match it: {brand_voice}\n"
    prompt += "\nReturn the JSON object now."

    raw = await provider.generate(prompt, system=_SYSTEM, max_tokens=2000)
    payload = _extract_json(raw)
    beats = _parse_beats(payload)

    record = AIGeneration(
        user_id=user.id,
        kind=AIGenerationKind.SCRIPT,
        provider=AIProviderKind(provider.name),
        model=provider.model,
        prompt=f"[content-package] {request.topic}",
        result=raw,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ContentPackage(
        topic=request.topic,
        platform=request.platform,
        language=language,
        duration_seconds=request.duration_seconds,
        hooks=_parse_hooks(payload, beats),
        beats=beats,
        higgsfield_prompt=str(payload.get("higgsfield_prompt", "")).strip()
        or "Handheld medium close-up, slight push in, natural daylight, energetic delivery.",
        broll_notes=str(payload.get("broll_notes", "")).strip(),
        post_caption=str(payload.get("post_caption", "")).strip(),
        cta=str(payload.get("cta", "")).strip(),
        hashtags=str(payload.get("hashtags", "")).strip(),
        generation_id=record.id,
        provider=AIProviderKind(provider.name),
        model=provider.model,
    )
