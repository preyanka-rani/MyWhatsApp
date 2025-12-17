from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json
from datetime import datetime
from app.models import Message, Conversation, ConversationMember, User
from app.core.redis import redis_manager
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for handling notifications and real-time events.

    Uses Redis pub/sub to deliver real-time notifications to connected clients.
    """

    async def notify_new_message(self, db: AsyncSession, message: Message):
        """
        Notify conversation members about new message.

        Args:
            db: Database session
            message: Message instance
        """
        # Get conversation members
        result = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == message.conversation_id
            )
        )
        members = result.scalars().all()

        # Create notification payload
        notification = {
            "type": "new_message",
            "message_id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "sender_id": str(message.sender_id),
            "message_type": message.type.value,
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
        }

        # Publish to each member (except sender)
        for member in members:
            if member.user_id != message.sender_id:
                await self._publish_user_notification(member.user_id, notification)

        logger.info(f"New message notification sent for message {message.id}")

    async def notify_typing_indicator(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_typing: bool
    ):
        """
        Notify conversation members about typing status.

        Args:
            conversation_id: Conversation ID
            user_id: User ID who is typing
            is_typing: Whether user is typing
        """
        notification = {
            "type": "typing_indicator",
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to conversation channel
        channel = f"conversation:{conversation_id}"
        await redis_manager.publish(channel, json.dumps(notification))

        logger.debug(
            f"Typing indicator sent for user {user_id} in conversation {conversation_id}"
        )

    async def notify_message_status_update(
        self, message_id: uuid.UUID, sender_id: uuid.UUID, status: str
    ):
        """
        Notify message sender about status update (delivered/read).

        Args:
            message_id: Message ID
            sender_id: Sender user ID to notify
            status: New message status
        """
        notification = {
            "type": "message_status_update",
            "message_id": str(message_id),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._publish_user_notification(sender_id, notification)
        logger.info(f"Status update notification sent for message {message_id}")

    async def notify_group_update(
        self,
        db: AsyncSession,
        group_id: uuid.UUID,
        update_type: str,
        data: Dict[str, Any],
    ):
        """
        Notify group members about group updates.

        Args:
            db: Database session
            group_id: Group ID
            update_type: Type of update (member_added, member_removed, settings_updated)
            data: Update data
        """
        from app.models import GroupMember

        # Get group members
        result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == group_id)
        )
        members = result.scalars().all()

        notification = {
            "type": "group_update",
            "group_id": str(group_id),
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to each member
        for member in members:
            await self._publish_user_notification(member.user_id, notification)

        logger.info(f"Group update notification sent for group {group_id}")

    async def _publish_user_notification(
        self, user_id: uuid.UUID, notification: Dict[str, Any]
    ):
        """
        Publish notification to specific user's channel.

        Args:
            user_id: User ID
            notification: Notification data
        """
        channel = f"user:{user_id}"
        await redis_manager.publish(channel, json.dumps(notification))

    async def subscribe_user_notifications(self, user_id: uuid.UUID):
        """
        Subscribe to user's notification channel.

        Args:
            user_id: User ID
        """
        channel = f"user:{user_id}"
        await redis_manager.subscribe(channel)
        logger.info(f"Subscribed to notifications for user {user_id}")

    async def subscribe_conversation_notifications(self, conversation_id: uuid.UUID):
        """
        Subscribe to conversation's notification channel.

        Args:
            conversation_id: Conversation ID
        """
        channel = f"conversation:{conversation_id}"
        await redis_manager.subscribe(channel)
        logger.info(f"Subscribed to notifications for conversation {conversation_id}")


# Singleton instance
notification_service = NotificationService()
