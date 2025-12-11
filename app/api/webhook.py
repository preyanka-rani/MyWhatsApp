"""
Webhook endpoints for WhatsApp Business API integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.models import Message, MessageStatus, User
from app.services.whatsapp_client import whatsapp_client
from app.services.message_service import message_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.get("")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge"),
):
    """
    Verify webhook endpoint with WhatsApp.

    WhatsApp calls this endpoint to verify the webhook URL.
    """
    logger.info(f"Webhook verification request: mode={mode}, token={token}")

    if mode == "subscribe" and token == settings.VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return int(challenge)
    else:
        logger.warning("Webhook verification failed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed"
        )


@router.post("")
async def handle_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle incoming WhatsApp webhook events.

    Processes incoming messages, status updates, and other events from WhatsApp.
    """
    try:
        webhook_data = await request.json()
        logger.info("=" * 70)
        logger.info("📥 WEBHOOK EVENT RECEIVED")
        logger.info("=" * 70)
        logger.info(f"Raw webhook data: {webhook_data}")

        # Parse webhook event
        event = whatsapp_client.parse_webhook_event(webhook_data)

        if not event:
            logger.warning("⚠️  Failed to parse webhook event - event is None")
            logger.warning(f"Webhook data was: {webhook_data}")
            return {"status": "ignored"}

        logger.info(f"✅ Parsed event type: {event['type']}")
        logger.info(f"Event details: {event}")

        # Handle message event
        if event["type"] == "message":
            logger.info("📨 Processing incoming message...")
            await handle_incoming_message(db, event)

        # Handle status update event
        elif event["type"] == "status":
            logger.info("📊 Processing status update...")
            await handle_status_update(db, event)

        logger.info("✅ Webhook processed successfully")
        logger.info("=" * 70)
        return {"status": "success"}

    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ ERROR handling webhook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        logger.error("=" * 70)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )


async def handle_incoming_message(db: AsyncSession, event: dict):
    """
    Handle incoming message from WhatsApp.

    Args:
        db: Database session
        event: Parsed webhook event
    """
    from app.models import (
        Conversation,
        ConversationMember,
        ConversationType,
        MessageType,
    )
    from app.websocket.manager import connection_manager
    from sqlalchemy import and_
    import uuid as uuid_module

    logger.info("🔍 Processing incoming message event...")

    from_phone = event["from"]
    message_type = event["message_type"]
    text_content = event.get("text")
    media_data = event.get("media")
    whatsapp_message_id = event.get("message_id")

    logger.info(f"   From: +{from_phone}")
    logger.info(f"   Type: {message_type}")
    logger.info(f"   Content: {text_content}")
    logger.info(f"   Media: {media_data}")
    logger.info(f"   WhatsApp Message ID: {whatsapp_message_id}")

    # Find or create sender user
    logger.info(f"🔍 Looking for sender user: +{from_phone}")
    sender_result = await db.execute(
        select(User).where(User.phone_number == f"+{from_phone}")
    )
    sender = sender_result.scalar_one_or_none()

    if not sender:
        logger.info(f"👤 Creating new user for: +{from_phone}")
        sender = User(phone_number=f"+{from_phone}")
        db.add(sender)
        await db.flush()
        logger.info(f"✅ User created with ID: {sender.id}")
    else:
        logger.info(f"✅ Found sender user ID: {sender.id}")

    # Get the WhatsApp Business account owner (recipient of this message)
    logger.info(f"🔍 Looking for business account: {settings.WHATSAPP_BUSINESS_PHONE}")
    recipient_result = await db.execute(
        select(User).where(User.phone_number == settings.WHATSAPP_BUSINESS_PHONE)
    )
    recipient = recipient_result.scalar_one_or_none()

    if not recipient:
        logger.warning(f"⚠️  Business phone not found, looking for any other user...")
        # If no business phone configured, find any user that's not the sender
        recipient_result = await db.execute(
            select(User).where(User.id != sender.id).limit(1)
        )
        recipient = recipient_result.scalar_one_or_none()

    if not recipient:
        logger.error("❌ No recipient user found to receive message")
        return

    logger.info(f"✅ Recipient user ID: {recipient.id} ({recipient.phone_number})")

    # Find or create conversation between sender and recipient
    logger.info("🔍 Looking for existing conversation...")
    existing = await db.execute(
        select(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(
            and_(
                Conversation.type == ConversationType.DIRECT,
                ConversationMember.user_id == recipient.id,
            )
        )
    )

    conversations = existing.scalars().all()
    conversation = None

    logger.info(f"   Found {len(conversations)} potential conversations")

    # Find conversation with both users
    for conv in conversations:
        members_result = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conv.id
            )
        )
        members = members_result.scalars().all()

        if len(members) == 2:
            member_ids = {m.user_id for m in members}
            if member_ids == {sender.id, recipient.id}:
                conversation = conv
                logger.info(f"✅ Found existing conversation: {conv.id}")
                break

    # Create conversation if not found
    if not conversation:
        logger.info(
            f"💬 Creating new conversation between {sender.phone_number} and {recipient.phone_number}"
        )
        conversation = Conversation(type=ConversationType.DIRECT)
        db.add(conversation)
        await db.flush()
        logger.info(f"✅ Conversation created with ID: {conversation.id}")

        # Add members
        member1 = ConversationMember(
            conversation_id=conversation.id,
            user_id=recipient.id,
            custom_name=from_phone,
        )
        member2 = ConversationMember(conversation_id=conversation.id, user_id=sender.id)
        db.add(member1)
        db.add(member2)
        await db.flush()
        logger.info(f"✅ Added 2 members to conversation")

    # Process media if present
    media_id = None
    if media_data and message_type != "text":
        logger.info(f"📸 Processing {message_type} media...")
        try:
            from app.models import Media
            from app.services.media_manager import media_manager

            # Get WhatsApp media ID
            whatsapp_media_id = media_data.get("id")
            mime_type = media_data.get("mime_type", "application/octet-stream")
            filename = media_data.get("filename", f"{message_type}_{whatsapp_media_id}")

            logger.info(f"   WhatsApp Media ID: {whatsapp_media_id}")
            logger.info(f"   MIME Type: {mime_type}")
            logger.info(f"   Filename: {filename}")

            # Download media from WhatsApp
            logger.info("⬇️  Downloading media from WhatsApp...")
            media_bytes = await whatsapp_client.download_media(whatsapp_media_id)
            logger.info(f"✅ Downloaded {len(media_bytes)} bytes")

            # Upload to S3
            logger.info("☁️  Uploading to S3...")
            url = await media_manager.upload_to_s3(
                file_data=media_bytes, filename=filename, mime_type=mime_type
            )
            logger.info(f"✅ Uploaded to: {url}")

            # Generate thumbnail for images
            thumbnail_url = None
            if mime_type.startswith("image/"):
                try:
                    logger.info("🖼️  Generating thumbnail...")
                    thumbnail_data = await media_manager.generate_thumbnail(media_bytes)
                    thumbnail_url = await media_manager.upload_to_s3(
                        file_data=thumbnail_data,
                        filename=f"thumb_{filename}",
                        mime_type="image/jpeg",
                    )
                    logger.info(f"✅ Thumbnail created: {thumbnail_url}")
                except Exception as thumb_error:
                    logger.warning(f"⚠️  Thumbnail generation failed: {thumb_error}")

            # Create media record
            media = Media(
                filename=filename,
                mime_type=mime_type,
                size=len(media_bytes),
                url=url,
                thumbnail_url=thumbnail_url,
                whatsapp_media_id=whatsapp_media_id,
                uploaded_by=sender.id,
            )
            db.add(media)
            await db.flush()
            media_id = media.id
            logger.info(f"✅ Media record created: {media_id}")

        except Exception as media_error:
            logger.error(f"❌ Failed to process media: {media_error}")
            import traceback

            logger.error(traceback.format_exc())

    # Map WhatsApp message types to our MessageType enum
    type_mapping = {
        "text": MessageType.TEXT,
        "image": MessageType.IMAGE,
        "video": MessageType.VIDEO,
        "audio": MessageType.AUDIO,
        "document": MessageType.DOCUMENT,
        "location": MessageType.LOCATION,
        "contacts": MessageType.CONTACT,
    }

    # Create message
    logger.info("💾 Creating message in database...")
    msg_type = type_mapping.get(message_type, MessageType.TEXT)
    message = Message(
        conversation_id=conversation.id,
        sender_id=sender.id,
        type=msg_type,
        content=text_content or (media_data.get("caption") if media_data else None),
        media_id=media_id,
        status=MessageStatus.DELIVERED,
        whatsapp_message_id=whatsapp_message_id,
    )

    db.add(message)

    # Update conversation's last message timestamp
    conversation.last_message_at = message.created_at

    await db.commit()
    await db.refresh(message)

    logger.info(f"✅ Message saved to database!")
    logger.info(f"   Message ID: {message.id}")
    logger.info(f"   Conversation ID: {conversation.id}")
    logger.info(f"   Sender ID: {sender.id}")
    logger.info(f"   Content: {text_content}")

    # Broadcast to WebSocket connections
    logger.info("📡 Broadcasting to WebSocket connections...")
    try:
        message_data = {
            "id": str(message.id),
            "conversation_id": str(conversation.id),
            "sender_id": str(sender.id),
            "content": text_content
            or (media_data.get("caption") if media_data else None),
            "type": msg_type.value,
            "status": MessageStatus.DELIVERED.value,
            "created_at": (
                message.created_at.isoformat() if message.created_at else None
            ),
        }

        # Include media information if present
        if media_id:
            message_data["media_id"] = str(media_id)
            message_data["media"] = {
                "id": str(media_id),
                "url": url,
                "thumbnail_url": thumbnail_url,
                "mime_type": mime_type,
                "filename": filename,
            }

        await connection_manager.broadcast_to_conversation(
            str(conversation.id),
            {
                "type": "new_message",
                "message": message_data,
            },
        )
        logger.info(f"✅ Message broadcasted via WebSocket successfully")
    except Exception as e:
        logger.error(f"❌ Failed to broadcast message: {e}")
        import traceback

        logger.error(traceback.format_exc())

    logger.info("=" * 70)
    logger.info("✅ INCOMING MESSAGE PROCESSED SUCCESSFULLY")
    logger.info("=" * 70)


async def handle_status_update(db: AsyncSession, event: dict):
    """
    Handle message status update from WhatsApp.

    Args:
        db: Database session
        event: Parsed webhook event
    """
    whatsapp_message_id = event["message_id"]
    status = event["status"]

    # Find message by WhatsApp message ID
    result = await db.execute(
        select(Message).where(Message.whatsapp_message_id == whatsapp_message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        logger.warning(f"Status update for unknown message: {whatsapp_message_id}")
        return

    # Update message status
    status_map = {
        "sent": MessageStatus.SENT,
        "delivered": MessageStatus.DELIVERED,
        "read": MessageStatus.READ,
        "failed": MessageStatus.FAILED,
    }

    new_status = status_map.get(status.lower())
    if new_status:
        await message_service.update_message_status(db, message.id, new_status)
        logger.info(f"Message {message.id} status updated to {new_status}")
