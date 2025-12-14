from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class MessageType(str, enum.Enum):
    """Message type enumeration."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"
    LOCATION = "LOCATION"
    CONTACT = "CONTACT"


class MessageStatus(str, enum.Enum):
    """Message delivery status enumeration."""

    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class Message(Base):
    """
    Message model representing individual chat messages.

    Attributes:
        id: Unique message identifier (UUID)
        conversation_id: Foreign key to conversation
        sender_id: Foreign key to sender user
        type: Type of message (text, media, etc.)
        content: Message text content
        media_id: Optional foreign key to media
        reply_to_id: Optional foreign key to message being replied to
        status: Delivery status
        is_deleted: Soft delete flag
        whatsapp_message_id: WhatsApp API message ID
        created_at: Message creation timestamp
        updated_at: Last update timestamp
        edited_at: Last edit timestamp
    """

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.TEXT)
    content = Column(Text, nullable=True)
    original_language = Column(String(10), nullable=True)  # Detected source language
    translations = Column(
        Text, nullable=True
    )  # JSON string of translations {lang: text}
    media_id = Column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    reply_to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(SQLEnum(MessageStatus), nullable=False, default=MessageStatus.SENT)
    is_deleted = Column(Boolean, default=False)
    whatsapp_message_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    edited_at = Column(DateTime, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_messages"
    )
    media = relationship("Media", back_populates="message")
    reply_to = relationship("Message", remote_side=[id], uselist=False)

    def __repr__(self):
        return f"<Message(id={self.id}, type={self.type}, sender_id={self.sender_id})>"

    def to_dict(self):
        """Convert message to dictionary representation."""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "sender_id": str(self.sender_id),
            "type": self.type.value,
            "content": self.content if not self.is_deleted else "[Deleted]",
            "media_id": str(self.media_id) if self.media_id else None,
            "reply_to_id": str(self.reply_to_id) if self.reply_to_id else None,
            "status": self.status.value,
            "is_deleted": self.is_deleted,
            "whatsapp_message_id": self.whatsapp_message_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
        }
