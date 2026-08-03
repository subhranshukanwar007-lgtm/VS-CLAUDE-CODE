from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.models.video_generation import VideoGenerationStatus


class VideoProviderError(Exception):
    """Raised when a video provider call fails (missing token, network error,
    bad response). Mirrors AIProviderError's role for the text providers."""


@dataclass
class VideoPollResult:
    status: VideoGenerationStatus
    video_url: str | None = None
    error: str | None = None


class VideoProvider(ABC):
    """Strategy interface every video-generation backend implements. Generation
    is asynchronous by nature (these jobs take anywhere from ~30s to several
    minutes), so the interface is submit-then-poll rather than a single call."""

    name: str

    @abstractmethod
    async def submit(self, prompt: str, model: str, extra_params: dict[str, Any]) -> str:
        """Kick off a generation job and return the provider's job id."""
        raise NotImplementedError

    @abstractmethod
    async def poll(self, external_job_id: str) -> VideoPollResult:
        """Check a job's current status. Must raise VideoProviderError (not a
        provider-specific exception) on failure so callers have one error type
        to handle."""
        raise NotImplementedError
