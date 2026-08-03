import httpx

from app.services.ai.base import AIProvider, AIProviderError

_ENDPOINT = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5") -> None:
        self._api_key = api_key
        self.model = model

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    _ENDPOINT,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": _ANTHROPIC_VERSION,
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AIProviderError(f"Anthropic API error {exc.response.status_code}: {exc.response.text}") from exc
            except httpx.HTTPError as exc:
                raise AIProviderError(f"Anthropic request failed: {exc}") from exc

        data = response.json()
        try:
            return "".join(block["text"] for block in data["content"] if block.get("type") == "text").strip()
        except (KeyError, TypeError) as exc:
            raise AIProviderError(f"Unexpected Anthropic response shape: {data}") from exc
