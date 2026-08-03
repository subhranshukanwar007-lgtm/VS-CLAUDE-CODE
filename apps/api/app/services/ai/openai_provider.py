import httpx

from app.services.ai.base import AIProvider, AIProviderError

_ENDPOINT = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self.model = model

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": self.model, "messages": messages, "max_tokens": max_tokens},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AIProviderError(f"OpenAI API error {exc.response.status_code}: {exc.response.text}") from exc
            except httpx.HTTPError as exc:
                raise AIProviderError(f"OpenAI request failed: {exc}") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Unexpected OpenAI response shape: {data}") from exc
