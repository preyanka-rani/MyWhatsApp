from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid
from app.models import User
from app.core.redis import redis_manager
import logging
import json

logger = logging.getLogger(__name__)


class PresenceService:
    """
    Service for managing user presence (online/offline/last seen).

    Uses Redis for real-time presence tracking and database for persistence.
    """

    ONLINE_KEY_PREFIX = "user:online:"
    LAST_SEEN_KEY_PREFIX = "user:last_seen:"
    PRESENCE_EXPIRY = 300  # 5 minutes

    async def set_user_online(self, db: AsyncSession, user_id: uuid.UUID):
        """
        Mark user as online.

        Args:
            db: Database session
            user_id: User ID
        """
        # Update Redis
        redis_key = f"{self.ONLINE_KEY_PREFIX}{user_id}"
        await redis_manager.set_value(redis_key, "1", expiry=self.PRESENCE_EXPIRY)

        # Update database
        user = await db.get(User, user_id)
        if user:
            user.is_online = True
            await db.commit()

        logger.info(f"User {user_id} marked as online")

    async def set_user_offline(self, db: AsyncSession, user_id: uuid.UUID):
        """
        Mark user as offline and update last seen.

        Args:
            db: Database session
            user_id: User ID
        """
        last_seen = datetime.utcnow()

        # Update Redis
        online_key = f"{self.ONLINE_KEY_PREFIX}{user_id}"
        await redis_manager.delete_value(online_key)

        last_seen_key = f"{self.LAST_SEEN_KEY_PREFIX}{user_id}"
        await redis_manager.set_value(last_seen_key, last_seen.isoformat())

        # Update database
        user = await db.get(User, user_id)
        if user:
            user.is_online = False
            user.last_seen = last_seen
            await db.commit()

        logger.info(f"User {user_id} marked as offline")

    async def is_user_online(self, user_id: uuid.UUID) -> bool:
        """
        Check if user is currently online.

        Args:
            user_id: User ID

        Returns:
            True if online, False otherwise
        """
        redis_key = f"{self.ONLINE_KEY_PREFIX}{user_id}"
        value = await redis_manager.get_value(redis_key)
        return value == "1"

    async def get_last_seen(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[datetime]:
        """
        Get user's last seen timestamp.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Last seen datetime or None
        """
        # Try Redis first
        redis_key = f"{self.LAST_SEEN_KEY_PREFIX}{user_id}"
        value = await redis_manager.get_value(redis_key)

        if value:
            return datetime.fromisoformat(value)

        # Fallback to database
        user = await db.get(User, user_id)
        return user.last_seen if user else None

    async def update_presence(self, db: AsyncSession, user_id: uuid.UUID):
        """
        Update user presence (refresh online status).

        Args:
            db: Database session
            user_id: User ID
        """
        await self.set_user_online(db, user_id)

    async def broadcast_presence_update(self, user_id: uuid.UUID, is_online: bool):
        """
        Broadcast presence update to subscribers.

        Args:
            user_id: User ID
            is_online: Whether user is online
        """
        message = json.dumps(
            {
                "type": "presence_update",
                "user_id": str(user_id),
                "is_online": is_online,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        await redis_manager.publish(f"presence:{user_id}", message)
        logger.info(f"Presence update broadcasted for user {user_id}")


# Singleton instance
presence_service = PresenceService()
