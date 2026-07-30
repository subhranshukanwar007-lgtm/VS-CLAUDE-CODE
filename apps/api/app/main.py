from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import configure_logging
from app.middleware.audit import AuditLogMiddleware
from app.middleware.rate_limit import limiter

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_middleware(AuditLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic v2 puts the original exception object in `ctx` when a field
    validator raises ValueError, and that object is not JSON serializable — passing
    exc.errors() straight to JSONResponse turns a 422 into a 500. Stringify ctx
    values so custom validators surface their message properly."""

    detail = []
    for error in exc.errors():
        cleaned = {k: v for k, v in error.items() if k != "ctx"}
        cleaned["loc"] = [str(part) for part in error.get("loc", ())]
        if "ctx" in error and isinstance(error["ctx"], dict):
            cleaned["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        detail.append(cleaned)
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


app.include_router(api_router, prefix=settings.api_v1_prefix)
