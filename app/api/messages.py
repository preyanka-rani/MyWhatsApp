from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
import uuid
from app.core.database import get_db
from app.models import (
    Message,
    ConversationMember,
    MessageType,
    MessageStatus,
    User,
    Conversation,
    ConversationType,
)
from app.schemas import (
    MessageCreate,
    MessageCreateInConversation,
    MessageResponse,
    MessageUpdate,
)
from app.api.dependencies import get_current_user
from app.services.message_service import message_service
from app.services.whatsapp_client import whatsapp_client
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
    data: MessageCreateInConversation,
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

    # Get conversation to check type
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
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

    # Translate message if conversation has target_language set
    # This translation is for the RECIPIENT - messages sent in this conversation
    # will be translated to conversation's target language
    translated_content = data.content
    if (
        conversation.target_language
        and data.content
        and message_type == MessageType.TEXT
    ):
        from app.services.translation_service import translation_service
        import json

        try:
            result = await translation_service.translate(
                data.content,
                source_lang="auto",
                target_lang=conversation.target_language,
            )
            translated_content = result["translation"]

            # Store original language and all translations
            if not message.original_language:
                message.original_language = result["source_lang"]

            translations_dict = {}
            if message.translations:
                try:
                    translations_dict = json.loads(message.translations)
                except:
                    pass

            # Store translation for conversation's target language
            translations_dict[conversation.target_language] = translated_content
            message.translations = json.dumps(translations_dict)
            await db.commit()
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Continue with original content if translation fails

    # Send via WhatsApp Business API ONLY for DIRECT conversations (not groups)
    # Groups are app-only feature and don't sync with actual WhatsApp
    if conversation.type == ConversationType.DIRECT:
        try:
            # Get conversation members (excluding current user)
            members_result = await db.execute(
                select(ConversationMember).where(
                    and_(
                        ConversationMember.conversation_id == conversation_id,
                        ConversationMember.user_id != current_user.id,
                    )
                )
            )
            other_members = members_result.scalars().all()

            # Send WhatsApp message to each member
            for member in other_members:
                user_result = await db.execute(
                    select(User).where(User.id == member.user_id)
                )
                recipient = user_result.scalar_one_or_none()

                if recipient and recipient.phone_number:
                    try:
                        # Send media or text via WhatsApp Business API
                        if message_type != MessageType.TEXT and data.media_id:
                            # Send media message
                            from app.models import Media

                            media = await db.get(Media, data.media_id)
                            if media:
                                # Map our MessageType to WhatsApp media type
                                media_type_mapping = {
                                    MessageType.IMAGE: "image",
                                    MessageType.VIDEO: "video",
                                    MessageType.AUDIO: "audio",
                                    MessageType.DOCUMENT: "document",
                                }
                                whatsapp_media_type = media_type_mapping.get(
                                    message_type, "document"
                                )

                                logger.info(
                                    f"Sending {whatsapp_media_type} to {recipient.phone_number}"
                                )

                                # Convert relative URL to absolute public URL for WhatsApp
                                from app.core.config import settings

                                media_url = (
                                    media.url
                                    if media.url.startswith("http")
                                    else f"{settings.PUBLIC_BASE_URL}{media.url}"
                                )
                                logger.info(f"Media URL for WhatsApp: {media_url}")

                                whatsapp_response = await whatsapp_client.send_media(
                                    to=recipient.phone_number,
                                    media_type=whatsapp_media_type,
                                    media_link=media_url,
                                    caption=data.content,
                                    filename=(
                                        media.filename
                                        if message_type == MessageType.DOCUMENT
                                        else None
                                    ),
                                )

                                # Store WhatsApp message ID
                                if (
                                    whatsapp_response
                                    and "messages" in whatsapp_response
                                ):
                                    message.whatsapp_message_id = whatsapp_response[
                                        "messages"
                                    ][0]["id"]
                                    await db.commit()

                                logger.info(
                                    f" Media sent via WhatsApp: {whatsapp_response}"
                                )
                        else:
                            # Send text message (use translated content if available)
                            whatsapp_response = await whatsapp_client.send_message(
                                to=recipient.phone_number,
                                message_text=translated_content or "",
                            )

                            # Store WhatsApp message ID
                            if whatsapp_response and "messages" in whatsapp_response:
                                message.whatsapp_message_id = whatsapp_response[
                                    "messages"
                                ][0]["id"]
                                await db.commit()

                            logger.info(
                                f" WhatsApp message sent to {recipient.phone_number}: {whatsapp_response}"
                            )
                    except Exception as wa_error:
                        logger.error(
                            f" Failed to send WhatsApp message to {recipient.phone_number}: {wa_error}"
                        )
                        # Continue even if WhatsApp sending fails
        except Exception as e:
            logger.error(f"Error sending WhatsApp messages: {e}")
            # Don't fail the request if WhatsApp sending fails
    else:
        logger.info(
            f"Group message - skipping WhatsApp Business API (app-only feature)"
        )

    # Load media details if message has media and create response
    msg_dict = {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "type": message.type.value if hasattr(message.type, "value") else message.type,
        "content": message.content,
        "media_id": message.media_id,
        "media": None,
        "reply_to_id": message.reply_to_id,
        "status": (
            message.status.value if hasattr(message.status, "value") else message.status
        ),
        "is_deleted": message.is_deleted,
        "whatsapp_message_id": message.whatsapp_message_id,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
        "edited_at": message.edited_at,
    }

    if message.media_id:
        from app.models import Media

        media = await db.get(Media, message.media_id)
        if media:
            msg_dict["media"] = media.to_dict()

    response_data = MessageResponse(**msg_dict)
    return response_data


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
    Messages are automatically translated to user's preferred language.
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

    # Load media details for messages with media
    from app.models import Media

    # Eagerly load media relationships to avoid lazy loading issues
    message_ids = [msg.media_id for msg in messages if msg.media_id]
    media_dict = {}
    if message_ids:
        stmt = select(Media).where(Media.id.in_(message_ids))
        result = await db.execute(stmt)
        media_dict = {media.id: media.to_dict() for media in result.scalars().all()}

    # Create response data with media included
    messages_data = []
    for message in messages:
        # Convert message to dict and add media if exists
        msg_dict = {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "type": (
                message.type.value if hasattr(message.type, "value") else message.type
            ),
            "content": message.content,
            "media_id": message.media_id,
            "media": media_dict.get(message.media_id),
            "reply_to_id": message.reply_to_id,
            "status": (
                message.status.value
                if hasattr(message.status, "value")
                else message.status
            ),
            "is_deleted": message.is_deleted,
            "whatsapp_message_id": message.whatsapp_message_id,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
            "edited_at": message.edited_at,
        }
        messages_data.append(MessageResponse(**msg_dict))

    # Translate messages to user's preferred language
    if current_user.preferred_language and current_user.preferred_language != "en":
        from app.services.translation_service import translation_service
        import json

        # Collect messages that need translation
        messages_to_translate = []
        message_indices = []

        for idx, message in enumerate(messages):
            if message.type == MessageType.TEXT and message.content:
                # Check if translation already exists in cache
                has_translation = False
                if message.translations:
                    try:
                        translations_dict = json.loads(message.translations)
                        if current_user.preferred_language in translations_dict:
                            # Use cached translation - update the response data
                            messages_data[idx].content = translations_dict[
                                current_user.preferred_language
                            ]
                            has_translation = True
                    except:
                        pass

                # Add to batch if no cache
                if not has_translation:
                    messages_to_translate.append(message.content)
                    message_indices.append(idx)

        # Batch translate all messages at once
        if messages_to_translate:
            try:
                results = await translation_service.translate_batch(
                    messages_to_translate,
                    source_lang="auto",
                    target_lang=current_user.preferred_language,
                )

                # Update messages with translations
                for i, result in enumerate(results):
                    msg_idx = message_indices[i]
                    message = messages[msg_idx]

                    # Store translation in cache
                    translations_dict = {}
                    if message.translations:
                        try:
                            translations_dict = json.loads(message.translations)
                        except:
                            pass

                    translations_dict[current_user.preferred_language] = result[
                        "translation"
                    ]
                    message.translations = json.dumps(translations_dict)

                    if not message.original_language:
                        message.original_language = result["source_lang"]

                    # Update both the model and response data
                    message.content = result["translation"]
                    messages_data[msg_idx].content = result["translation"]

                # Commit translation cache to database
                await db.commit()
            except Exception as e:
                logger.error(f" Batch translation failed: {e}")

    return messages_data


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
