"""
Conversation and conversation member models.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class ConversationType(str, enum.Enum):
    """Conversation type enumeration."""

    DIRECT = "DIRECT"  # 1:1 conversation
    GROUP = "GROUP"  # Group conversation


class Conversation(Base):
    """
    Conversation model representing chat threads.

    Attributes:
        id: Unique conversation identifier (UUID)
        type: Type of conversation (DIRECT or GROUP)
        last_message_at: Timestamp of last message
        created_at: Conversation creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    type = Column(
        SQLEnum(ConversationType), nullable=False, default=ConversationType.DIRECT
    )
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    members = relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    group = relationship("Group", back_populates="conversation", uselist=False)

    def __repr__(self):
        return f"<Conversation(id={self.id}, type={self.type})>"


class ConversationMember(Base):
    """
    Junction table for conversation members.

    Attributes:
        id: Unique member record identifier
        conversation_id: Foreign key to conversation
        user_id: Foreign key to user
        joined_at: When user joined the conversation
        last_read_at: Last time user read messages
        is_muted: Whether conversation is muted for this user
    """

    __tablename__ = "conversation_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_read_at = Column(DateTime, nullable=True)
    is_muted = Column(Boolean, default=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User", back_populates="conversation_memberships")

    def __repr__(self):
        return f"<ConversationMember(conversation_id={self.conversation_id}, user_id={self.user_id})>"
