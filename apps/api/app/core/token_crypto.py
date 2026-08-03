"""Symmetric encryption for OAuth tokens stored on SocialAccount.

Platform access tokens are credentials: they let anyone holding them post as the
user. They must not sit in the database in plaintext, so they're encrypted at
rest with Fernet (AES-128-CBC + HMAC-SHA256) using a key derived from
`SECRET_KEY`.

Consequence worth understanding before you rotate SECRET_KEY in production:
every stored token becomes undecryptable and each account has to be reconnected.
`decrypt_token` returns None rather than raising on an undecryptable value so a
rotated key degrades into "reconnect your account" instead of a 500.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger("token_crypto")


def _fernet() -> Fernet:
    # Fernet needs exactly 32 url-safe-base64 bytes; SECRET_KEY is an arbitrary
    # string, so hash it to a fixed width first.
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_token(stored: str | None) -> str | None:
    """Returns None when the value is missing or was encrypted under a different
    SECRET_KEY, so callers surface "reconnect this account" to the user."""

    if not stored:
        return None
    try:
        return _fernet().decrypt(stored.encode()).decode()
    except InvalidToken:
        logger.warning("stored token could not be decrypted (SECRET_KEY rotated?)")
        return None
