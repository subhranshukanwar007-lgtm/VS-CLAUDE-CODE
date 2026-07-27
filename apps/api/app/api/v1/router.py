from fastapi import APIRouter

from app.api.v1 import (
    ai,
    auth,
    dashboard,
    deals,
    leads,
    notes,
    notifications,
    pipelines,
    posts,
    social_accounts,
    tasks,
    users,
    video,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(leads.router)
api_router.include_router(pipelines.router)
api_router.include_router(deals.router)
api_router.include_router(tasks.router)
api_router.include_router(notes.router)
api_router.include_router(posts.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(video.router)
api_router.include_router(social_accounts.router)
api_router.include_router(webhooks.router)
