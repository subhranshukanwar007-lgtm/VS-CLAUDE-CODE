from typing import Any

import httpx

from app.models.video_generation import VideoGenerationStatus
from app.services.video.base import VideoPollResult, VideoProvider, VideoProviderError

_API_BASE = "https://platform.higgsfield.ai"

_STATUS_MAP = {
    "queued": VideoGenerationStatus.PENDING,
    "in_queue": VideoGenerationStatus.PENDING,
    "processing": VideoGenerationStatus.PROCESSING,
    "in_progress": VideoGenerationStatus.PROCESSING,
    "completed": VideoGenerationStatus.SUCCEEDED,
    "succeeded": VideoGenerationStatus.SUCCEEDED,
    "failed": VideoGenerationStatus.FAILED,
    "error": VideoGenerationStatus.FAILED,
    "cancelled": VideoGenerationStatus.FAILED,
    "nsfw": VideoGenerationStatus.FAILED,
}


class HiggsfieldProvider(VideoProvider):
    """Calls the Higgsfield platform API (platform.higgsfield.ai), verified
    against Higgsfield's own published docs: key+secret auth, POST /{model_id}
    to submit a job, GET /requests/{request_id}/status to poll it.

    Caveat worth being explicit about: the *general* submit/poll mechanics
    here are confirmed from Higgsfield's docs. The exact request fields for
    training a persistent personal avatar on your own face/photos, or for
    voice cloning specifically, were not independently confirmed from public
    docs at the time this was written — those aren't hardcoded here. Pass
    whatever fields your Higgsfield dashboard's API reference shows for the
    model you're using (reference image URLs, voice IDs, etc.) via
    `extra_params`; they're sent through unmodified alongside `prompt`.
    """

    name = "higgsfield"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self._api_key}:{self._api_secret}",
            "Content-Type": "application/json",
        }

    async def submit(self, prompt: str, model: str, extra_params: dict[str, Any]) -> str:
        payload = {"prompt": prompt, **extra_params}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(f"{_API_BASE}/{model}", headers=self._headers(), json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise VideoProviderError(
                    f"Higgsfield API error {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise VideoProviderError(f"Higgsfield request failed: {exc}") from exc

        data = response.json()
        request_id = data.get("request_id")
        if not request_id:
            raise VideoProviderError(f"Unexpected Higgsfield response shape: {data}")
        return request_id

    async def poll(self, external_job_id: str) -> VideoPollResult:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{_API_BASE}/requests/{external_job_id}/status", headers=self._headers()
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise VideoProviderError(
                    f"Higgsfield API error {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise VideoProviderError(f"Higgsfield request failed: {exc}") from exc

        return parse_status_response(response.json())


def parse_status_response(data: dict[str, Any]) -> VideoPollResult:
    """Pure parsing of a Higgsfield /requests/{id}/status response into a
    VideoPollResult. Split out from `poll()` so the response-shape handling
    can be unit tested directly against sample JSON without mocking HTTP."""

    raw_status = str(data.get("status", "")).lower()
    status = _STATUS_MAP.get(raw_status, VideoGenerationStatus.PROCESSING)

    video_url: str | None = None
    video = data.get("video")
    if isinstance(video, dict):
        video_url = video.get("url")
    if not video_url:
        images = data.get("images")
        if isinstance(images, list) and images:
            last = images[-1]
            video_url = last.get("url") if isinstance(last, dict) else None

    error = data.get("error") or data.get("message")

    return VideoPollResult(status=status, video_url=video_url, error=error)
