from app.config import settings
from app.models.video_generation import VideoProviderKind
from app.services.video.base import VideoProvider, VideoProviderError
from app.services.video.higgsfield_provider import HiggsfieldProvider
from app.services.video.replicate_provider import ReplicateProvider


def get_video_provider(kind: VideoProviderKind | None = None) -> VideoProvider:
    resolved = kind or VideoProviderKind(settings.default_video_provider)

    if resolved == VideoProviderKind.REPLICATE:
        if not settings.replicate_api_token:
            raise VideoProviderError("REPLICATE_API_TOKEN is not configured")
        return ReplicateProvider(settings.replicate_api_token)

    if resolved == VideoProviderKind.HIGGSFIELD:
        if not settings.higgsfield_api_key or not settings.higgsfield_api_secret:
            raise VideoProviderError("HIGGSFIELD_API_KEY / HIGGSFIELD_API_SECRET are not configured")
        return HiggsfieldProvider(settings.higgsfield_api_key, settings.higgsfield_api_secret)

    raise VideoProviderError(f"Unknown video provider: {resolved}")


def default_model_for(kind: VideoProviderKind | None = None) -> str:
    resolved = kind or VideoProviderKind(settings.default_video_provider)
    if resolved == VideoProviderKind.HIGGSFIELD:
        return settings.higgsfield_model
    return settings.replicate_video_model
