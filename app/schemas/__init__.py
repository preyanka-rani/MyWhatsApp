"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re


# ============ Auth Schemas ============


class OTPRequest(BaseModel):
    """Request schema for OTP generation."""

    phone_number: str = Field(
        ..., description="Phone number with country code (e.g., +1234567890)"
    )

    @validator("phone_number")
    def validate_phone(cls, v):
        """Validate phone number format."""
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(
                "Invalid phone number format. Use international format with + prefix"
            )
        return v


class OTPVerify(BaseModel):
    """Request schema for OTP verification."""

    phone_number: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit OTP code"
    )


class TokenResponse(BaseModel):
    """Response schema for authentication token."""

    access_token: str
    token_type: str = "bearer"
    user: dict


# ============ User Schemas ============


class UserCreate(BaseModel):
    """Schema for user creation."""

    phone_number: str
    name: str = Field(..., min_length=1, max_length=100)
    about: Optional[str] = Field(None, max_length=255)


class UserUpdate(BaseModel):
    """Schema for user profile update."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    about: Optional[str] = Field(None, max_length=255)
    profile_picture_url: Optional[str] = None


class LanguageUpdate(BaseModel):
    """Schema for updating user's preferred language."""

    language: str = Field(
        ..., min_length=2, max_length=10, description="ISO language code"
    )


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: UUID
    phone_number: str
    name: str
    profile_picture_url: Optional[str]
    about: Optional[str]
    preferred_language: Optional[str] = "en"
    is_online: bool
    last_seen: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Message Schemas ============


class MessageCreate(BaseModel):
    """Schema for creating a message."""

    conversation_id: UUID
    type: str = Field(
        ..., description="Message type: TEXT, IMAGE, VIDEO, AUDIO, DOCUMENT"
    )
    content: Optional[str] = None
    media_id: Optional[UUID] = None
    reply_to_id: Optional[UUID] = None


class MessageCreateInConversation(BaseModel):
    """Schema for creating a message within a conversation (conversation_id in URL)."""

    type: str = Field(
        ..., description="Message type: TEXT, IMAGE, VIDEO, AUDIO, DOCUMENT"
    )
    content: Optional[str] = None
    media_id: Optional[UUID] = None
    reply_to_id: Optional[UUID] = None


class MessageResponse(BaseModel):
    """Response schema for message data."""

    id: UUID
    conversation_id: UUID
    sender_id: UUID
    type: str
    content: Optional[str]
    media_id: Optional[UUID]
    reply_to_id: Optional[UUID]
    status: str
    is_deleted: bool
    whatsapp_message_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageUpdate(BaseModel):
    """Schema for updating a message."""

    content: str = Field(..., min_length=1)


# ============ Conversation Schemas ============


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    participant_ids: List[UUID] = Field(
        ..., min_items=1, description="List of participant user IDs"
    )
    name: Optional[str] = Field(None, description="Custom name for the conversation")


class ConversationResponse(BaseModel):
    """Response schema for conversation data."""

    id: UUID
    type: str
    name: Optional[str] = None  # Custom name for this conversation
    last_message_at: Optional[datetime]
    created_at: datetime
    participants: List[UserResponse] = []

    class Config:
        from_attributes = True


# ============ Group Schemas ============


class GroupCreate(BaseModel):
    """Schema for creating a group."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    member_ids: List[UUID] = Field(
        ..., min_items=1, description="List of initial member user IDs"
    )


class GroupUpdate(BaseModel):
    """Schema for updating group settings."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    profile_picture_url: Optional[str] = None


class GroupMemberAdd(BaseModel):
    """Schema for adding group member."""

    user_id: UUID


class GroupResponse(BaseModel):
    """Response schema for group data."""

    id: UUID
    conversation_id: UUID
    name: str
    description: Optional[str]
    profile_picture_url: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


# ============ Media Schemas ============


class MediaUploadResponse(BaseModel):
    """Response schema for media upload."""

    id: UUID
    filename: str
    mime_type: str
    size: int
    url: str
    thumbnail_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ WebSocket Schemas ============


class TypingIndicator(BaseModel):
    """Schema for typing indicator event."""

    conversation_id: UUID
    is_typing: bool


class PresenceUpdate(BaseModel):
    """Schema for presence update event."""

    is_online: bool


# ============ Webhook Schemas ============


class WebhookVerification(BaseModel):
    """Schema for webhook verification."""

    hub_mode: str = Field(..., alias="hub.mode")
    hub_challenge: str = Field(..., alias="hub.challenge")
    hub_verify_token: str = Field(..., alias="hub.verify_token")

    class Config:
        populate_by_name = True
