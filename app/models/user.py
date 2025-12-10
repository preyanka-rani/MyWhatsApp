"""
User model representing application users.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class User(Base):
    """
    User model for storing user information.

    Attributes:
        id: Unique user identifier (UUID)
        phone_number: User's phone number (unique)
        name: User's display name
        profile_picture_url: URL to profile picture
        about: User status/about text
        is_online: Online status
        last_seen: Last seen timestamp
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    profile_picture_url = Column(String(500), nullable=True)
    about = Column(String(255), nullable=True, default="Hey there! I'm using WhatsApp")
    preferred_language = Column(
        String(10), nullable=True, default="en"
    )  # ISO language code
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    sent_messages = relationship(
        "Message", foreign_keys="Message.sender_id", back_populates="sender"
    )
    conversation_memberships = relationship("ConversationMember", back_populates="user")
    group_memberships = relationship("GroupMember", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, phone={self.phone_number}, name={self.name})>"

    def to_dict(self):
        """Convert user to dictionary representation."""
        return {
            "id": str(self.id),
            "phone_number": self.phone_number,
            "name": self.name,
            "profile_picture_url": self.profile_picture_url,
            "about": self.about,
            "preferred_language": self.preferred_language,
            "is_online": self.is_online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
