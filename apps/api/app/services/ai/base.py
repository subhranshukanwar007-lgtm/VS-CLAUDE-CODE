from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised when an AI provider call fails (missing key, network error, bad response)."""


class AIProvider(ABC):
    """Strategy interface every LLM provider implements. Add a new provider by
    subclassing this and registering it in services/ai/factory.py — nothing else
    in the codebase needs to change."""

    name: str
    model: str

    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        """Return the raw text completion for `prompt`. Must raise AIProviderError
        (not a provider-specific exception) on failure so callers have one error
        type to handle."""
        raise NotImplementedError
