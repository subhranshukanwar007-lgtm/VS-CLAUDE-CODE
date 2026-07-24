from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceUnavailableError
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AgentChatRequest,
    AIGenerationResult,
    CaptionRequest,
    HashtagRequest,
    ScriptRequest,
)
from app.services import content_service
from app.services.agents.personas import AGENT_PERSONAS
from app.services.agents.runner import run_agent
from app.services.ai.base import AIProviderError

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/caption", response_model=AIGenerationResult)
async def caption(
    payload: CaptionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AIGenerationResult:
    try:
        record = await content_service.generate_caption(
            db, user, payload.topic, payload.platform, payload.tone, payload.brand_voice or user.brand_voice, payload.provider
        )
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    return AIGenerationResult(id=record.id, provider=record.provider, model=record.model, result=record.result)


@router.post("/hashtags", response_model=AIGenerationResult)
async def hashtags(
    payload: HashtagRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AIGenerationResult:
    try:
        record = await content_service.generate_hashtags(db, user, payload.topic, payload.count, payload.provider)
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    return AIGenerationResult(id=record.id, provider=record.provider, model=record.model, result=record.result)


@router.post("/script", response_model=AIGenerationResult)
async def script(
    payload: ScriptRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AIGenerationResult:
    try:
        record = await content_service.generate_script(
            db,
            user,
            payload.topic,
            payload.format,
            payload.duration_seconds,
            payload.brand_voice or user.brand_voice,
            payload.provider,
        )
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    return AIGenerationResult(id=record.id, provider=record.provider, model=record.model, result=record.result)


@router.get("/agents")
def list_agents() -> dict[str, str]:
    return AGENT_PERSONAS


@router.post("/agents/chat", response_model=AIGenerationResult)
async def agent_chat(
    payload: AgentChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AIGenerationResult:
    try:
        record = await run_agent(db, user, payload.agent, payload.message, payload.provider)
    except AIProviderError as exc:
        raise ServiceUnavailableError(str(exc)) from exc
    return AIGenerationResult(id=record.id, provider=record.provider, model=record.model, result=record.result)
