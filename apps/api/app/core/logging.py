import logging
import sys

from app.config import settings


def configure_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if not settings.debug else logging.INFO)
