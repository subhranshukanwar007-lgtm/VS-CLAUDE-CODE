"""Extension point for real social-platform publishing.

Each platform integration (Instagram, Facebook, YouTube, LinkedIn, Threads,
Pinterest, TikTok, X) needs: (1) an OAuth connect flow that stores tokens on
SocialAccount, and (2) a Publisher that turns a Post into a live platform post
using that platform's official API.

This repo ships a working scheduling *engine* (see app/services/scheduler_service.py
and app/workers/tasks.py) plus one real Publisher — LogPublisher — which records a
post as published without calling any external network. It is intentionally NOT a
simulated "fake Instagram API": it's the honest default so the scheduler is fully
testable without developer credentials for eight different platforms. Wiring in a
real platform means implementing Publisher below and registering it in
app/integrations/registry.py; nothing else in the scheduling pipeline changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.post import Post
from app.models.social_account import SocialAccount


@dataclass
class PublishResult:
    external_post_id: str
    permalink: str | None = None


class PublisherError(Exception):
    pass


class Publisher(ABC):
    platform: str

    @abstractmethod
    async def publish(self, post: Post, account: SocialAccount | None) -> PublishResult:
        raise NotImplementedError
