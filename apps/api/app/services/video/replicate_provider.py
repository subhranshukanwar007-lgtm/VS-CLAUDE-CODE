from typing import Any

import httpx

from app.models.video_generation import VideoGenerationStatus
from app.services.video.base import VideoPollResult, VideoProvider, VideoProviderError

_API_BASE = "https://api.replicate.com/v1"

_STATUS_MAP = {
    "starting": VideoGenerationStatus.PROCESSING,
    "processing": VideoGenerationStatus.PROCESSING,
    "succeeded": VideoGenerationStatus.SUCCEEDED,
    "failed": VideoGenerationStatus.FAILED,
    "canceled": VideoGenerationStatus.FAILED,
}


class ReplicateProvider(VideoProvider):
    """Calls Replicate's "official models" API directly (no version hash
    needed): POST /v1/models/{owner}/{name}/predictions to start a job, GET
    /v1/predictions/{id} to poll it. `model` must be an "owner/name" slug —
    see https://replicate.com/collections/text-to-video for options; different
    models expect different `extra_params` (aspect ratio, duration, an input
    image for image-to-video, etc.), which are passed straight through into
    Replicate's `input` object alongside `prompt`."""

    name = "replicate"

    def __init__(self, api_token: str) -> None:
        self._api_token = api_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}", "Content-Type": "application/json"}

    async def submit(self, prompt: str, model: str, extra_params: dict[str, Any]) -> str:
        if "/" not in model:
            raise VideoProviderError(f"Invalid Replicate model slug '{model}' — expected 'owner/name'")
        owner, name = model.split("/", 1)

        payload = {"input": {"prompt": prompt, **extra_params}}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{_API_BASE}/models/{owner}/{name}/predictions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise VideoProviderError(
                    f"Replicate API error {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise VideoProviderError(f"Replicate request failed: {exc}") from exc

        data = response.json()
        job_id = data.get("id")
        if not job_id:
            raise VideoProviderError(f"Unexpected Replicate response shape: {data}")
        return job_id

    async def poll(self, external_job_id: str) -> VideoPollResult:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{_API_BASE}/predictions/{external_job_id}", headers=self._headers()
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise VideoProviderError(
                    f"Replicate API error {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise VideoProviderError(f"Replicate request failed: {exc}") from exc

        data = response.json()
        raw_status = data.get("status")
        status = _STATUS_MAP.get(raw_status, VideoGenerationStatus.PROCESSING)

        video_url: str | None = None
        output = data.get("output")
        if isinstance(output, str):
            video_url = output
        elif isinstance(output, list) and output:
            video_url = output[-1]

        error = data.get("error")
        if raw_status == "canceled" and not error:
            error = "Generation was canceled"

        return VideoPollResult(status=status, video_url=video_url, error=error)
