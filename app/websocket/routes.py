"""
WebSocket API endpoints.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import json
from app.core.database import get_db
from app.core.security import security
from app.websocket.manager import connection_manager
from app.services.presence_service import presence_service
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def get_user_from_token(token: str, db: AsyncSession) -> uuid.UUID:
    """
    Extract and validate user from JWT token.

    Args:
        token: JWT token
        db: Database session

    Returns:
        User ID

    Raises:
        Exception if token is invalid
    """
    from app.models import User
    from sqlalchemy import select

    payload = security.decode_access_token(token)
    if not payload:
        raise Exception("Invalid token")

    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise Exception("Invalid token payload")

    user_id = uuid.UUID(user_id_str)

    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise Exception("User not found")

    return user_id


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
):
    """
    WebSocket endpoint for real-time communication.

    Accepts connections with JWT token for authentication.
    Handles incoming events and broadcasts messages.

    Query Parameters:
        token: JWT authentication token

    Events:
        - typing_indicator: User typing status
        - presence_update: User online/offline status
        - new_message: Incoming message notification
        - message_status: Message delivery status update
    """
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Authenticate user
        user_id = await get_user_from_token(token, db)

        # Connect user
        await connection_manager.connect(websocket, user_id, db)

        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "user_id": str(user_id),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )

        # Start listening to Redis in background
        redis_task = asyncio.create_task(
            connection_manager.listen_to_redis(user_id, websocket)
        )

        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)

                event_type = message.get("type")

                # Handle typing indicator
                if event_type == "typing_indicator":
                    conversation_id = uuid.UUID(message.get("conversation_id"))
                    is_typing = message.get("is_typing", False)

                    await connection_manager.handle_typing_indicator(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        is_typing=is_typing,
                    )

                # Handle presence update (heartbeat)
                elif event_type == "heartbeat":
                    await presence_service.update_presence(db, user_id)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "heartbeat_ack",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                    )

                # Handle message read receipt
                elif event_type == "message_read":
                    from app.services.message_service import message_service
                    from app.models import MessageStatus

                    message_id = uuid.UUID(message.get("message_id"))
                    await message_service.update_message_status(
                        db, message_id, MessageStatus.READ
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
        finally:
            redis_task.cancel()
            await connection_manager.disconnect(websocket, db)

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")

    finally:
        try:
            await db_gen.aclose()
        except:
            pass


from datetime import datetime
