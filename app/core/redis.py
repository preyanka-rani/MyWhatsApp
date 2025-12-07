"""
Redis connection management and pub/sub utilities.
"""

import redis.asyncio as aioredis
from typing import Optional
from app.core.config import settings


class RedisManager:
    """Redis connection manager with pub/sub support."""

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.pubsub = None

    async def connect(self):
        """Establish Redis connection."""
        self.redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
        self.pubsub = self.redis_client.pubsub()

    async def disconnect(self):
        """Close Redis connection."""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

    async def set_value(self, key: str, value: str, expiry: Optional[int] = None):
        """
        Set a value in Redis.

        Args:
            key: Redis key
            value: Value to store
            expiry: Optional expiration in seconds
        """
        if expiry:
            await self.redis_client.setex(key, expiry, value)
        else:
            await self.redis_client.set(key, value)

    async def get_value(self, key: str) -> Optional[str]:
        """
        Get a value from Redis.

        Args:
            key: Redis key

        Returns:
            Value or None if not found
        """
        return await self.redis_client.get(key)

    async def delete_value(self, key: str):
        """
        Delete a value from Redis.

        Args:
            key: Redis key
        """
        await self.redis_client.delete(key)

    async def publish(self, channel: str, message: str):
        """
        Publish a message to a Redis channel.

        Args:
            channel: Channel name
            message: Message to publish
        """
        await self.redis_client.publish(channel, message)

    async def subscribe(self, *channels: str):
        """
        Subscribe to Redis channels.

        Args:
            channels: Channel names to subscribe to
        """
        await self.pubsub.subscribe(*channels)

    async def unsubscribe(self, *channels: str):
        """
        Unsubscribe from Redis channels.

        Args:
            channels: Channel names to unsubscribe from
        """
        await self.pubsub.unsubscribe(*channels)

    async def listen(self):
        """
        Listen for messages on subscribed channels.

        Yields:
            Messages from subscribed channels
        """
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                yield message


# Global Redis manager instance
redis_manager = RedisManager()
