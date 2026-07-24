from app.integrations.base import Publisher
from app.integrations.log_publisher import LogPublisher
from app.models.post import Platform

_DEFAULT = LogPublisher()

# Register a real Publisher per platform here once its OAuth + API integration is
# implemented. Any platform not present falls back to `_DEFAULT`.
_REGISTRY: dict[Platform, Publisher] = {}


def get_publisher(platform: Platform) -> Publisher:
    return _REGISTRY.get(platform, _DEFAULT)
