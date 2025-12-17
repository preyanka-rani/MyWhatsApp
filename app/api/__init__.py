"""API module initialization."""

from fastapi import APIRouter
from app.api import auth, conversations, messages, groups, media

# Create main API router
api_router = APIRouter()

# Include all sub-routers (webhook is included at root level in main.py)
api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(messages.messages_router)  # Add separate messages router
api_router.include_router(groups.router)
api_router.include_router(media.router)

__all__ = ["api_router"]
