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

    # Check if conversation already exists between these two users
    # Get all direct conversations for current user
    existing = await db.execute(
        select(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(
            and_(
                Conversation.type == ConversationType.DIRECT,
                ConversationMember.user_id == current_user.id,
            )
        )
    )

    user_conversations = existing.scalars().all()

    # Check if any of these conversations has exactly 2 members (current user + other user)
    for conv in user_conversations:
        members_result = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conv.id
            )
        )
        members = members_result.scalars().all()

        if len(members) == 2:
            member_ids = {m.user_id for m in members}
            if member_ids == {current_user.id, other_user_id}:
                # Update the custom name for current user if provided
                for member in members:
                    if member.user_id == current_user.id:
                        if data.name:  # Only update if name is provided
                            member.custom_name = data.name
                            await db.commit()

                        # Get other user info
                        other_user = await db.get(User, other_user_id)

                        # Return formatted response with custom name
                        return {
                            "id": conv.id,
                            "type": conv.type,
                            "name": member.custom_name
                            or (other_user.phone if other_user else "Unknown"),
                            "created_at": (
                                conv.created_at.isoformat() if conv.created_at else None
                            ),
                            "last_message_at": (
                                conv.last_message_at.isoformat()
                                if conv.last_message_at
                                else None
                            ),
                        }
                break

    # Create new conversation
    conversation = Conversation(type=ConversationType.DIRECT)
    db.add(conversation)
    await db.flush()

    # Add members with custom name for current user
    member1 = ConversationMember(
        conversation_id=conversation.id,
        user_id=current_user.id,
        custom_name=data.name,  # Save the custom name for current user
    )
    member2 = ConversationMember(conversation_id=conversation.id, user_id=other_user_id)

    db.add(member1)
    db.add(member2)

    await db.commit()
    await db.refresh(conversation)

    logger.info(f"Conversation created: {conversation.id}")

    # Get other user info for fallback
    other_user = await db.get(User, other_user_id)

    # Return conversation with custom name in consistent format
    return {
        "id": conversation.id,
        "type": conversation.type.value,
        "name": data.name or (other_user.phone if other_user else "Unknown"),
        "created_at": (
            conversation.created_at.isoformat() if conversation.created_at else None
        ),
        "last_message_at": (
            conversation.last_message_at.isoformat()
            if conversation.last_message_at
            else None
        ),
        "participants": [],
    }


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
    from app.models import Group

    result = await db.execute(
        select(Conversation, ConversationMember.custom_name)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(ConversationMember.user_id == current_user.id)
        .order_by(Conversation.last_message_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )

    conversations_with_names = result.all()

    # Format response with custom names or group names
    response = []
    for conv, custom_name in conversations_with_names:
        display_name = custom_name

        # For GROUP conversations, get the group name
        if conv.type == ConversationType.GROUP:
            group_result = await db.execute(
                select(Group).where(Group.conversation_id == conv.id)
            )
            group = group_result.scalar_one_or_none()
            if group:
                display_name = group.name

        conv_dict = {
            "id": conv.id,
            "type": conv.type.value,
            "name": display_name,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "last_message_at": (
                conv.last_message_at.isoformat() if conv.last_message_at else None
            ),
            "participants": [],
        }
        response.append(conv_dict)

    return response


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


@router.get("/{conversation_id}/members")
async def get_conversation_members(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get members of a conversation with their user details.

    Returns list of members with user information.
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

    # Get all members with user details
    result = await db.execute(
        select(ConversationMember, User)
        .join(User, User.id == ConversationMember.user_id)
        .where(ConversationMember.conversation_id == conversation_id)
    )

    members_data = result.all()

    members = []
    for member, user in members_data:
        members.append(
            {
                "user_id": str(user.id),
                "phone_number": user.phone_number,
                "custom_name": member.custom_name,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }
        )

    return members


@router.put("/{conversation_id}/language")
async def set_conversation_language(
    conversation_id: uuid.UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set target language for a conversation.
    Messages sent in this conversation will be translated to this language for the recipient.

    Request body: {"language": "bn"}
    """
    from app.services.translation_service import translation_service

    language = data.get("language")
    if not language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Language code is required"
        )

    # Validate language code
    supported_languages = translation_service.get_supported_languages()
    if language not in supported_languages and language is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language code. Supported: {list(supported_languages.keys())}",
        )

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

    # Get conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Update target language
    conversation.target_language = language if language != "" else None
    await db.commit()
    await db.refresh(conversation)

    logger.info(f"Conversation {conversation_id} target language set to: {language}")

    return {
        "conversation_id": str(conversation_id),
        "target_language": language,
        "language_name": (
            supported_languages.get(language, "Default") if language else "Default"
        ),
    }
