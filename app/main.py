from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import redis_manager
from app.api import api_router
from app.api.webhook import router as webhook_router
from app.websocket import websocket_router
from app.utils import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting WhatsApp Clone API...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Connect to Redis
    await redis_manager.connect()
    logger.info("Redis connected")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down WhatsApp Clone API...")

    # Disconnect Redis
    await redis_manager.disconnect()
    logger.info("Redis disconnected")

    # Close database connections
    await engine.dispose()
    logger.info("Database connections closed")

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A complete WhatsApp-like messaging system built with FastAPI",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files directory for media uploads
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Include webhook router at root level (WhatsApp requires /webhook, not /api/webhook)
app.include_router(webhook_router)

# Include API routers
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
