import httpx

from app.config import settings
from app.core.exceptions import UnauthorizedError

_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleProfile:
    def __init__(self, sub: str, email: str, name: str, picture: str | None) -> None:
        self.sub = sub
        self.email = email
        self.name = name
        self.picture = picture


async def verify_google_id_token(id_token: str) -> GoogleProfile:
    """Verify a Google Sign-In ID token against Google's tokeninfo endpoint and
    return the verified profile. Raises UnauthorizedError on any failure (expired,
    wrong audience, invalid signature, etc.) — never returns a profile for a token
    that didn't validate."""

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(_GOOGLE_TOKENINFO_URL, params={"id_token": id_token})

    if response.status_code != 200:
        raise UnauthorizedError("Invalid Google ID token")

    payload = response.json()

    if settings.google_client_id and payload.get("aud") != settings.google_client_id:
        raise UnauthorizedError("Google ID token audience mismatch")

    try:
        return GoogleProfile(
            sub=payload["sub"],
            email=payload["email"],
            name=payload.get("name", payload["email"]),
            picture=payload.get("picture"),
        )
    except KeyError as exc:
        raise UnauthorizedError("Google ID token missing required claims") from exc
