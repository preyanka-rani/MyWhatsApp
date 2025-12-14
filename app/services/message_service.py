from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from datetime import datetime
import uuid
from app.models import Message, MessageType, MessageStatus, Conversation, User
from app.services.whatsapp_client import whatsapp_client
from app.services.notification_service import notification_service
import logging

logger = logging.getLogger(__name__)


class MessageService:
    """
    Service class for message-related business logic.

    Handles message creation, retrieval, status updates, and search.
    """

    async def create_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        message_type: MessageType,
        content: Optional[str] = None,
        media_id: Optional[uuid.UUID] = None,
        reply_to_id: Optional[uuid.UUID] = None,
    ) -> Message:
        """
        Create a new message in a conversation.

        Args:
            db: Database session
            conversation_id: ID of conversation
            sender_id: ID of sender
            message_type: Type of message
            content: Message text content
            media_id: Optional media ID
            reply_to_id: Optional ID of message being replied to

        Returns:
            Created message instance
        """
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            type=message_type,
            content=content,
            media_id=media_id,
            reply_to_id=reply_to_id,
            status=MessageStatus.SENT,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        # Update conversation's last message timestamp
        conversation = await db.get(Conversation, conversation_id)
        if conversation:
            conversation.last_message_at = message.created_at
            await db.commit()

        logger.info(f"Message created: {message.id}")

        # Send notification to conversation members
        await notification_service.notify_new_message(db, message)

        # Also broadcast directly via WebSocket (for when Redis is not available)
        try:
            from app.websocket.manager import connection_manager

            message_data = {
                "id": str(message.id),
                "conversation_id": str(conversation_id),
                "sender_id": str(sender_id),
                "content": content,
                "type": message_type.value,
                "status": MessageStatus.SENT.value,
                "created_at": (
                    message.created_at.isoformat() if message.created_at else None
                ),
            }

            # Include media information if present
            if media_id:
                message_data["media_id"] = str(media_id)
                # Load media details
                from app.models import Media

                media = await db.get(Media, media_id)
                if media:
                    message_data["media"] = {
                        "id": str(media.id),
                        "url": media.url,
                        "thumbnail_url": media.thumbnail_url,
                        "mime_type": media.mime_type,
                        "filename": media.filename,
                        "size": media.size,
                    }

            await connection_manager.broadcast_to_conversation(
                str(conversation_id),
                {
                    "type": "new_message",
                    "message": message_data,
                },
            )
            logger.info(f"Message broadcasted via WebSocket: {message.id}")
        except Exception as e:
            logger.error(f"Failed to broadcast message via WebSocket: {e}")

        return message

    async def get_message(
        self, db: AsyncSession, message_id: uuid.UUID
    ) -> Optional[Message]:
        """
        Get message by ID.

        Args:
            db: Database session
            message_id: Message ID

        Returns:
            Message instance or None
        """
        result = await db.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()

    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int = 50,
        cursor: Optional[datetime] = None,
    ) -> List[Message]:
        """
        Get paginated messages for a conversation.

        Args:
            db: Database session
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            cursor: Cursor timestamp for pagination

        Returns:
            List of messages
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
        )

        if cursor:
            query = query.where(Message.created_at < cursor)

        query = query.limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def update_message_status(
        self, db: AsyncSession, message_id: uuid.UUID, status: MessageStatus
    ) -> Optional[Message]:
        """
        Update message delivery status.

        Args:
            db: Database session
            message_id: Message ID
            status: New status

        Returns:
            Updated message or None
        """
        message = await self.get_message(db, message_id)
        if message:
            message.status = status
            await db.commit()
            await db.refresh(message)
            logger.info(f"Message {message_id} status updated to {status}")

        return message

    async def edit_message(
        self,
        db: AsyncSession,
        message_id: uuid.UUID,
        new_content: str,
        user_id: uuid.UUID,
    ) -> Optional[Message]:
        """
        Edit message content (only by sender).

        Args:
            db: Database session
            message_id: Message ID
            new_content: New message content
            user_id: ID of user attempting to edit

        Returns:
            Updated message or None
        """
        message = await self.get_message(db, message_id)

        if not message or message.sender_id != user_id:
            logger.warning(f"Edit denied for message {message_id} by user {user_id}")
            return None

        message.content = new_content
        message.edited_at = datetime.utcnow()
        await db.commit()
        await db.refresh(message)

        logger.info(f"Message {message_id} edited")
        return message

    async def delete_message(
        self,
        db: AsyncSession,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete message (soft or hard delete).

        Args:
            db: Database session
            message_id: Message ID
            user_id: ID of user attempting to delete
            soft_delete: Whether to soft delete (default) or hard delete

        Returns:
            True if successful, False otherwise
        """
        message = await self.get_message(db, message_id)

        if not message or message.sender_id != user_id:
            logger.warning(f"Delete denied for message {message_id} by user {user_id}")
            return False

        if soft_delete:
            message.is_deleted = True
            message.content = None
            await db.commit()
            logger.info(f"Message {message_id} soft deleted")
        else:
            await db.delete(message)
            await db.commit()
            logger.info(f"Message {message_id} hard deleted")

        return True

    async def search_messages(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        search_query: str,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> List[Message]:
        """
        Search messages by content.

        Args:
            db: Database session
            user_id: ID of user performing search
            search_query: Search query string
            conversation_id: Optional conversation ID to limit search
            limit: Maximum number of results

        Returns:
            List of matching messages
        """
        query = select(Message).where(
            and_(
                Message.content.ilike(f"%{search_query}%"), Message.is_deleted == False
            )
        )

        if conversation_id:
            query = query.where(Message.conversation_id == conversation_id)

        query = query.order_by(desc(Message.created_at)).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def send_whatsapp_message(
        self, db: AsyncSession, message: Message, recipient_phone: str
    ) -> Optional[str]:
        """
        Send message via WhatsApp Business API.

        Args:
            db: Database session
            message: Message instance
            recipient_phone: Recipient's phone number

        Returns:
            WhatsApp message ID or None
        """
        try:
            if message.type == MessageType.TEXT:
                response = await whatsapp_client.send_message(
                    to=recipient_phone, message_text=message.content
                )
            else:
                # Handle media messages
                media = message.media
                if media:
                    response = await whatsapp_client.send_media(
                        to=recipient_phone,
                        media_type=message.type.value.lower(),
                        media_link=media.url,
                        caption=message.content,
                    )
                else:
                    logger.error(f"Media not found for message {message.id}")
                    return None

            whatsapp_msg_id = response.get("messages", [{}])[0].get("id")

            # Update message with WhatsApp message ID
            message.whatsapp_message_id = whatsapp_msg_id
            await db.commit()

            return whatsapp_msg_id

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            message.status = MessageStatus.FAILED
            await db.commit()
            return None


# Singleton instance
message_service = MessageService()
