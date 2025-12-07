"""
Messages API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
import uuid
from app.core.database import get_db
from app.models import Message, ConversationMember, MessageType, MessageStatus, User
from app.schemas import MessageCreate, MessageResponse, MessageUpdate
from app.api.dependencies import get_current_user
from app.services.message_service import message_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Messages"])


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message in a conversation.

    Creates a new message and notifies conversation members.
    """
    # Verify user is member of conversation
    member_check = await db.execute(
        select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == current_user.id,
            )
        )
    )

    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this conversation",
        )

    # Create message
    try:
        message_type = MessageType[data.type.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message type: {data.type}",
        )

    message = await message_service.create_message(
        db=db,
        conversation_id=conversation_id,
        sender_id=current_user.id,
        message_type=message_type,
        content=data.content,
        media_id=data.media_id,
        reply_to_id=data.reply_to_id,
    )

    return message


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    cursor: Optional[datetime] = Query(default=None),
):
    """
    Get messages from a conversation with pagination.

    Returns messages ordered by creation time (newest first).
    Use cursor for pagination (provide created_at of last message).
    """
    # Verify user is member
    member_check = await db.execute(
        select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == current_user.id,
            )
        )
    )

    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this conversation",
        )

    messages = await message_service.get_conversation_messages(
        db=db, conversation_id=conversation_id, limit=limit, cursor=cursor
    )

    return messages


@router.patch("/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: uuid.UUID,
    data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Edit a message (only by sender).

    Updates message content and sets edited_at timestamp.
    """
    message = await message_service.edit_message(
        db=db, message_id=message_id, new_content=data.content, user_id=current_user.id
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or unauthorized",
        )

    return message


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a message (only by sender).

    Performs soft delete by default.
    """
    success = await message_service.delete_message(
        db=db, message_id=message_id, user_id=current_user.id, soft_delete=True
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or unauthorized",
        )

    return None


@router.get("/messages/search", response_model=List[MessageResponse])
async def search_messages(
    query: str = Query(..., min_length=1),
    conversation_id: Optional[uuid.UUID] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
):
    """
    Search messages by content.

    Searches within user's conversations. Can be limited to specific conversation.
    """
    messages = await message_service.search_messages(
        db=db,
        user_id=current_user.id,
        search_query=query,
        conversation_id=conversation_id,
        limit=limit,
    )

    return messages
