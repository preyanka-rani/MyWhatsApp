"""
Conversations API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime
import uuid
from app.core.database import get_db
from app.models import Conversation, ConversationMember, User, ConversationType
from app.schemas import ConversationCreate, ConversationResponse, UserResponse
from app.api.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new 1:1 conversation.

    Creates a direct conversation between current user and one other participant.
    """
    if len(data.participant_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct conversations must have exactly 1 other participant",
        )

    other_user_id = data.participant_ids[0]

    # Check if conversation already exists
    existing = await db.execute(
        select(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(
            and_(
                Conversation.type == ConversationType.DIRECT,
                ConversationMember.user_id.in_([current_user.id, other_user_id]),
            )
        )
        .group_by(Conversation.id)
        .having(
            select(ConversationMember.conversation_id)
            .where(ConversationMember.conversation_id == Conversation.id)
            .group_by(ConversationMember.conversation_id)
            .having(select(func.count()).scalar_subquery() == 2)
        )
    )

    existing_conv = existing.scalar_one_or_none()
    if existing_conv:
        return existing_conv

    # Create new conversation
    conversation = Conversation(type=ConversationType.DIRECT)
    db.add(conversation)
    await db.flush()

    # Add members
    member1 = ConversationMember(
        conversation_id=conversation.id, user_id=current_user.id
    )
    member2 = ConversationMember(conversation_id=conversation.id, user_id=other_user_id)

    db.add(member1)
    db.add(member2)

    await db.commit()
    await db.refresh(conversation)

    logger.info(f"Conversation created: {conversation.id}")
    return conversation


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List all conversations for current user.

    Returns paginated list of conversations ordered by last message time.
    """
    result = await db.execute(
        select(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(ConversationMember.user_id == current_user.id)
        .order_by(Conversation.last_message_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )

    conversations = result.scalars().all()
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get conversation details by ID.

    Returns conversation information if user is a member.
    """
    # Check if user is member
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

    conversation = await db.get(Conversation, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    return conversation
