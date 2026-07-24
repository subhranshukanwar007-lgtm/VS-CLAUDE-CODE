from app.config import settings
from app.models.ai_generation import AIProvider as AIProviderKind
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIProvider, AIProviderError
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider


def get_provider(kind: AIProviderKind | None = None) -> AIProvider:
    """Resolve which configured AI provider to use. Falls back to
    settings.default_ai_provider when the caller doesn't specify one, and raises
    AIProviderError immediately if the corresponding API key isn't configured
    rather than silently returning fake output."""

    resolved = kind or AIProviderKind(settings.default_ai_provider)

    if resolved == AIProviderKind.OPENAI:
        if not settings.openai_api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")
        return OpenAIProvider(settings.openai_api_key)

    if resolved == AIProviderKind.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise AIProviderError("ANTHROPIC_API_KEY is not configured")
        return AnthropicProvider(settings.anthropic_api_key)

    if resolved == AIProviderKind.GEMINI:
        if not settings.gemini_api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured")
        return GeminiProvider(settings.gemini_api_key)

    raise AIProviderError(f"Unknown AI provider: {resolved}")
