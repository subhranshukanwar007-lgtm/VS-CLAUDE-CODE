import json
import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger("audit")

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SKIP_PATH_PREFIXES = ("/api/v1/auth/login", "/docs", "/openapi.json")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Persists a lightweight audit trail for every mutating API call. Runs after
    the request completes so it never blocks the response, and swallows its own
    errors so audit-logging can never break a real request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)

        if request.method in _MUTATING_METHODS and not request.url.path.startswith(_SKIP_PATH_PREFIXES):
            try:
                self._record(request, response)
            except Exception:  # noqa: BLE001 - audit logging must never break the request
                logger.exception("failed to write audit log entry")

        return response

    @staticmethod
    def _record(request: Request, response: Response) -> None:
        actor_id = getattr(request.state, "user_id", None)
        db = SessionLocal()
        try:
            db.add(
                AuditLog(
                    actor_id=actor_id,
                    action=f"{request.method} {response.status_code}",
                    resource_type=request.url.path,
                    resource_id=None,
                    ip_address=request.client.host if request.client else None,
                    metadata_json=json.dumps({"query": str(request.query_params)}),
                )
            )
            db.commit()
        finally:
            db.close()
