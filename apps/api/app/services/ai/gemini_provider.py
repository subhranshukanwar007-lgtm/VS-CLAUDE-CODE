import httpx

from app.services.ai.base import AIProvider, AIProviderError


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self.model = model

    async def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    endpoint,
                    params={"key": self._api_key},
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise AIProviderError(f"Gemini API error {exc.response.status_code}: {exc.response.text}") from exc
            except httpx.HTTPError as exc:
                raise AIProviderError(f"Gemini request failed: {exc}") from exc

        data = response.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Unexpected Gemini response shape: {data}") from exc
