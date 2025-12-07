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
        logger.info(f"Webhook event received: {webhook_data}")

        # Parse webhook event
        event = whatsapp_client.parse_webhook_event(webhook_data)

        if not event:
            logger.warning("Failed to parse webhook event")
            return {"status": "ignored"}

        # Handle message event
        if event["type"] == "message":
            await handle_incoming_message(db, event)

        # Handle status update event
        elif event["type"] == "status":
            await handle_status_update(db, event)

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
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
    from_phone = event["from"]
    message_type = event["message_type"]
    text_content = event.get("text")

    # Find user by phone number
    result = await db.execute(select(User).where(User.phone_number == f"+{from_phone}"))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Received message from unknown user: {from_phone}")
        return

    # TODO: Create conversation and message
    # This would require additional logic to determine the conversation
    logger.info(f"Incoming message from {from_phone}: {text_content}")


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
