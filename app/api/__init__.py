"""API module initialization."""

from fastapi import APIRouter
from app.api import auth, conversations, messages, groups, media, webhook

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(groups.router)
api_router.include_router(media.router)
api_router.include_router(webhook.router)

__all__ = ["api_router"]
