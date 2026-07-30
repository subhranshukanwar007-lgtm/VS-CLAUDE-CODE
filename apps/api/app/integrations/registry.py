from app.integrations.base import Publisher
from app.integrations.log_publisher import LogPublisher
from app.integrations.meta_publisher import (
    FacebookPublisher,
    InstagramPublisher,
    ThreadsPublisher,
)
from app.models.post import Platform

_DEFAULT = LogPublisher()

# Register a real Publisher per platform here once its OAuth + API integration is
# implemented. Any platform not present falls back to `_DEFAULT` (LogPublisher),
# which marks the post published without making a network call.
#
# Implemented: Instagram, Facebook and Threads, all through Meta's APIs and one
# Meta developer app.
# Still on the default: YouTube, LinkedIn, Pinterest, TikTok, X. X notably has no
# free API tier for new developers as of 2026-02-06 (pay-per-use only), which is
# why it isn't wired up by default — see docs/ROADMAP.md.
_REGISTRY: dict[Platform, Publisher] = {
    Platform.INSTAGRAM: InstagramPublisher(),
    Platform.FACEBOOK: FacebookPublisher(),
    Platform.THREADS: ThreadsPublisher(),
}


def get_publisher(platform: Platform) -> Publisher:
    return _REGISTRY.get(platform, _DEFAULT)


def has_real_publisher(platform: Platform) -> bool:
    """True when the platform actually posts rather than falling back to
    LogPublisher. The API exposes this so the UI never promises a publish it
    can't perform."""

    return platform in _REGISTRY
