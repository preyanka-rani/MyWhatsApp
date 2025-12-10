"""
WebSocket connection manager for real-time communication.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional
import uuid
import json
from datetime import datetime
from app.core.redis import redis_manager
from app.services.presence_service import presence_service
from app.services.notification_service import notification_service
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and real-time message delivery.

    Handles user connections, presence updates, and message broadcasting.
    """

    def __init__(self):
        # Map user_id -> set of WebSocket connections
        self.active_connections: Dict[uuid.UUID, Set[WebSocket]] = {}
        # Map WebSocket -> user_id
        self.connection_user_map: Dict[WebSocket, uuid.UUID] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID, db):
        """
        Accept new WebSocket connection and set user online.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            db: Database session
        """
        await websocket.accept()

        # Add to connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.connection_user_map[websocket] = user_id

        # Set user online
        await presence_service.set_user_online(db, user_id)
        await presence_service.broadcast_presence_update(user_id, is_online=True)

        # Subscribe to user's notification channel
        await notification_service.subscribe_user_notifications(user_id)

        logger.info(f"User {user_id} connected via WebSocket")

    async def disconnect(self, websocket: WebSocket, db):
        """
        Handle WebSocket disconnection and update user presence.

        Args:
            websocket: WebSocket connection
            db: Database session
        """
        user_id = self.connection_user_map.get(websocket)

        if not user_id:
            return

        # Remove from connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # If no more connections for this user, set offline
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                await presence_service.set_user_offline(db, user_id)
                await presence_service.broadcast_presence_update(
                    user_id, is_online=False
                )

        del self.connection_user_map[websocket]

        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: dict, user_id: uuid.UUID):
        """
        Send message to specific user's all connections.

        Args:
            message: Message data to send
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            message_json = json.dumps(message)

            # Send to all user's connections
            for connection in connections.copy():
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    connections.discard(connection)

    async def send_to_conversation(
        self,
        message: dict,
        conversation_id: uuid.UUID,
        exclude_user_id: Optional[uuid.UUID] = None,
    ):
        """
        Send message to all members of a conversation.

        Args:
            message: Message data to send
            conversation_id: Conversation ID
            exclude_user_id: Optional user ID to exclude (e.g., sender)
        """
        from app.models import ConversationMember
        from sqlalchemy import select

        # This would need database access to get conversation members
        # For now, we'll use Redis pub/sub
        channel = f"conversation:{conversation_id}"
        await redis_manager.publish(channel, json.dumps(message))

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: dict,
        exclude_user_id: Optional[uuid.UUID] = None,
    ):
        """
        Broadcast message to all active connections in a conversation.

        Args:
            conversation_id: Conversation ID (string)
            message: Message data to send
            exclude_user_id: Optional user ID to exclude (e.g., sender)
        """
        message_json = json.dumps(message)

        # Send to all connected users
        for user_id, connections in self.active_connections.items():
            if exclude_user_id and user_id == exclude_user_id:
                continue

            for connection in connections.copy():
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    connections.discard(connection)

    async def handle_typing_indicator(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID, is_typing: bool
    ):
        """
        Handle typing indicator event.

        Args:
            user_id: User who is typing
            conversation_id: Conversation ID
            is_typing: Whether user is typing
        """
        await notification_service.notify_typing_indicator(
            conversation_id=conversation_id, user_id=user_id, is_typing=is_typing
        )

    async def send_to_user(self, user_id: uuid.UUID, message: dict):
        """
        Send a message to a specific user across all their connections.

        Args:
            user_id: User ID to send message to
            message: Message data to send
        """
        if user_id not in self.active_connections:
            logger.debug(f"User {user_id} is not connected")
            return

        message_json = json.dumps(message)
        connections = self.active_connections[user_id].copy()

        for connection in connections:
            try:
                await connection.send_text(message_json)
                logger.debug(f"Message sent to user {user_id}")
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                self.active_connections[user_id].discard(connection)

    async def listen_to_redis(self, user_id: uuid.UUID, websocket: WebSocket):
        """
        Listen to Redis pub/sub for notifications and forward to WebSocket.

        Args:
            user_id: User ID
            websocket: WebSocket connection
        """
        try:
            async for message in redis_manager.listen():
                data = message.get("data")
                if data:
                    try:
                        await websocket.send_text(data)
                    except Exception as e:
                        logger.error(
                            f"Error forwarding Redis message to WebSocket: {e}"
                        )
                        break
        except Exception as e:
            logger.error(f"Error listening to Redis: {e}")


# Global connection manager instance
connection_manager = ConnectionManager()
