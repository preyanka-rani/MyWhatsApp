"""
Group model and group members.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class Group(Base):
    """
    Group model for group conversations.

    Attributes:
        id: Unique group identifier (UUID)
        conversation_id: Foreign key to conversation (one-to-one)
        name: Group name
        description: Group description
        profile_picture_url: Group profile picture URL
        created_by: Foreign key to creator user
        created_at: Group creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="group")
    creator = relationship("User")
    members = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Group(id={self.id}, name={self.name})>"

    def to_dict(self):
        """Convert group to dictionary representation."""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "name": self.name,
            "description": self.description,
            "profile_picture_url": self.profile_picture_url,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GroupMember(Base):
    """
    Junction table for group members with role information.

    Attributes:
        id: Unique member record identifier
        group_id: Foreign key to group
        user_id: Foreign key to user
        is_admin: Whether user is group admin
        joined_at: When user joined the group
    """

    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_admin = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id}, is_admin={self.is_admin})>"
