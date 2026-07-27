from app.config import settings
from app.models.video_generation import VideoProviderKind
from app.services.video.base import VideoProvider, VideoProviderError
from app.services.video.replicate_provider import ReplicateProvider


def get_video_provider(kind: VideoProviderKind | None = None) -> VideoProvider:
    resolved = kind or VideoProviderKind.REPLICATE

    if resolved == VideoProviderKind.REPLICATE:
        if not settings.replicate_api_token:
            raise VideoProviderError("REPLICATE_API_TOKEN is not configured")
        return ReplicateProvider(settings.replicate_api_token)

    raise VideoProviderError(f"Unknown video provider: {resolved}")
