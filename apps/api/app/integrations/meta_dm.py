"""Private replies: the DM that answers a public comment.

This is the mechanic behind every "comment PLAN and I'll DM you" reel. Meta
supports it on two surfaces, with two genuinely different endpoints:

- **Instagram** — ``POST /{ig-user-id}/messages`` with
  ``{"recipient": {"comment_id": ...}, "message": {"text": ...}}``. Addressing
  the recipient by *comment id* rather than user id is what makes it a private
  reply; you cannot DM an Instagram user who has not messaged you first, but you
  may answer their comment once.
- **Facebook Pages** — ``POST /{comment-id}/private_replies`` with ``message``.
  Different shape, same idea.

Constraints that are Meta's, not ours, and that the caller must respect:

- **One private reply per comment, ever.** A second attempt fails. See
  ``app/models/private_reply.py`` for how that is deduplicated durably.
- **7 days** from the comment to the reply.
- If the person answers, that opens a normal 24-hour window in which you can
  message them freely — which is the actual goal. The private reply is the
  door-opener, not the conversation.

Requires the ``instagram_manage_messages`` (Instagram) or
``pages_messaging`` (Facebook) permission on the connected account's token; an
account connected only for publishing will be rejected by Meta here, and the
error text says so.
"""

import logging

import httpx

from app.core.token_crypto import decrypt_token
from app.integrations.meta_publisher import GRAPH_BASE, _TIMEOUT, _graph_error
from app.models.post import Platform
from app.models.social_account import SocialAccount

logger = logging.getLogger("dm.meta")


class PrivateReplyError(Exception):
    """Carries Meta's own error wording. Raised rather than swallowed so the
    queue row records why a DM did not go out."""


def _token(account: SocialAccount) -> tuple[str, str]:
    if not account.external_account_id:
        raise PrivateReplyError(
            "The connected account has no account ID stored. Reconnect it in "
            "Settings -> Connected accounts."
        )
    token = decrypt_token(account.access_token_encrypted)
    if not token:
        raise PrivateReplyError(
            "No usable access token for this account. Reconnect it in Settings -> "
            "Connected accounts (tokens expire, and they also become unreadable if "
            "SECRET_KEY changed)."
        )
    return account.external_account_id, token


async def send_private_reply(account: SocialAccount, comment_id: str, message: str) -> str:
    """Sends one private reply and returns Meta's message id.

    Raises ``PrivateReplyError`` on any non-success. Never returns quietly on
    failure: a DM the user believes was sent but wasn't is worse than a visible
    error, because they will not follow up manually.
    """

    account_id, token = _token(account)

    if account.platform is Platform.INSTAGRAM:
        url = f"{GRAPH_BASE}/{account_id}/messages"
        payload = {
            "recipient": {"comment_id": comment_id},
            "message": {"text": message},
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, params={"access_token": token}, json=payload)
    elif account.platform is Platform.FACEBOOK:
        url = f"{GRAPH_BASE}/{comment_id}/private_replies"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, params={"access_token": token, "message": message})
    else:
        # Threads is the one people ask about: it has no DM API at all. Not
        # restricted, not gated — absent.
        raise PrivateReplyError(
            f"{account.platform.value} has no private reply API. Only Instagram and "
            "Facebook support answering a comment with a DM."
        )

    if response.status_code >= 400:
        raise PrivateReplyError(_graph_error(response))

    body = response.json() if response.content else {}
    return str(body.get("message_id") or body.get("id") or "")
