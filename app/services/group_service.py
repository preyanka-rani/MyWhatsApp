"""
Group Service for managing groups and group memberships.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid
from app.models import (
    Group,
    GroupMember,
    Conversation,
    ConversationType,
    ConversationMember,
    User,
)
import logging

logger = logging.getLogger(__name__)


class GroupService:
    """
    Service class for group-related operations.

    Handles group creation, member management, and group settings.
    """

    async def create_group(
        self,
        db: AsyncSession,
        name: str,
        description: Optional[str],
        created_by: uuid.UUID,
        member_ids: List[uuid.UUID],
    ) -> Group:
        """
        Create a new group.

        Args:
            db: Database session
            name: Group name
            description: Group description
            created_by: Creator user ID
            member_ids: List of initial member user IDs

        Returns:
            Created group instance
        """
        # Create conversation for the group
        conversation = Conversation(type=ConversationType.GROUP)
        db.add(conversation)
        await db.flush()

        # Create group
        group = Group(
            conversation_id=conversation.id,
            name=name,
            description=description,
            created_by=created_by,
        )
        db.add(group)
        await db.flush()

        # Add creator as admin
        creator_member = GroupMember(
            group_id=group.id, user_id=created_by, is_admin=True
        )
        db.add(creator_member)

        # Add creator to conversation
        creator_conv_member = ConversationMember(
            conversation_id=conversation.id, user_id=created_by
        )
        db.add(creator_conv_member)

        # Add other members
        for member_id in member_ids:
            if member_id != created_by:
                member = GroupMember(
                    group_id=group.id, user_id=member_id, is_admin=False
                )
                db.add(member)

                conv_member = ConversationMember(
                    conversation_id=conversation.id, user_id=member_id
                )
                db.add(conv_member)

        await db.commit()
        await db.refresh(group)

        logger.info(f"Group created: {group.id} by user {created_by}")
        return group

    async def get_group(self, db: AsyncSession, group_id: uuid.UUID) -> Optional[Group]:
        """
        Get group by ID.

        Args:
            db: Database session
            group_id: Group ID

        Returns:
            Group instance or None
        """
        result = await db.execute(select(Group).where(Group.id == group_id))
        return result.scalar_one_or_none()

    async def add_member(
        self,
        db: AsyncSession,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        added_by: uuid.UUID,
    ) -> Optional[GroupMember]:
        """
        Add member to group.

        Args:
            db: Database session
            group_id: Group ID
            user_id: User ID to add
            added_by: User ID of person adding member (must be admin)

        Returns:
            Created GroupMember or None if not authorized
        """
        # Check if added_by is admin
        admin_check = await db.execute(
            select(GroupMember).where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == added_by,
                    GroupMember.is_admin == True,
                )
            )
        )

        if not admin_check.scalar_one_or_none():
            logger.warning(
                f"User {added_by} not authorized to add members to group {group_id}"
            )
            return None

        # Check if user is already a member
        existing = await db.execute(
            select(GroupMember).where(
                and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
            )
        )

        if existing.scalar_one_or_none():
            logger.info(f"User {user_id} already in group {group_id}")
            return None

        # Get group and add to conversation
        group = await self.get_group(db, group_id)
        if not group:
            return None

        # Add to group
        member = GroupMember(group_id=group_id, user_id=user_id, is_admin=False)
        db.add(member)

        # Add to conversation
        conv_member = ConversationMember(
            conversation_id=group.conversation_id, user_id=user_id
        )
        db.add(conv_member)

        await db.commit()
        await db.refresh(member)

        logger.info(f"User {user_id} added to group {group_id}")
        return member

    async def remove_member(
        self,
        db: AsyncSession,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        removed_by: uuid.UUID,
    ) -> bool:
        """
        Remove member from group.

        Args:
            db: Database session
            group_id: Group ID
            user_id: User ID to remove
            removed_by: User ID of person removing member (must be admin)

        Returns:
            True if successful, False otherwise
        """
        # Check if removed_by is admin
        admin_check = await db.execute(
            select(GroupMember).where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == removed_by,
                    GroupMember.is_admin == True,
                )
            )
        )

        if not admin_check.scalar_one_or_none():
            logger.warning(
                f"User {removed_by} not authorized to remove members from group {group_id}"
            )
            return False

        # Get member
        result = await db.execute(
            select(GroupMember).where(
                and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            logger.info(f"User {user_id} not in group {group_id}")
            return False

        # Get group
        group = await self.get_group(db, group_id)
        if not group:
            return False

        # Remove from group
        await db.delete(member)

        # Remove from conversation
        conv_member_result = await db.execute(
            select(ConversationMember).where(
                and_(
                    ConversationMember.conversation_id == group.conversation_id,
                    ConversationMember.user_id == user_id,
                )
            )
        )
        conv_member = conv_member_result.scalar_one_or_none()
        if conv_member:
            await db.delete(conv_member)

        await db.commit()

        logger.info(f"User {user_id} removed from group {group_id}")
        return True

    async def update_group(
        self,
        db: AsyncSession,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        profile_picture_url: Optional[str] = None,
    ) -> Optional[Group]:
        """
        Update group settings.

        Args:
            db: Database session
            group_id: Group ID
            user_id: User ID attempting to update (must be admin)
            name: Optional new name
            description: Optional new description
            profile_picture_url: Optional new profile picture URL

        Returns:
            Updated group or None if not authorized
        """
        # Check if user is admin
        admin_check = await db.execute(
            select(GroupMember).where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.is_admin == True,
                )
            )
        )

        if not admin_check.scalar_one_or_none():
            logger.warning(f"User {user_id} not authorized to update group {group_id}")
            return None

        group = await self.get_group(db, group_id)
        if not group:
            return None

        if name:
            group.name = name
        if description is not None:
            group.description = description
        if profile_picture_url:
            group.profile_picture_url = profile_picture_url

        await db.commit()
        await db.refresh(group)

        logger.info(f"Group {group_id} updated")
        return group

    async def get_group_members(
        self, db: AsyncSession, group_id: uuid.UUID
    ) -> List[User]:
        """
        Get all members of a group.

        Args:
            db: Database session
            group_id: Group ID

        Returns:
            List of User instances
        """
        result = await db.execute(
            select(User)
            .join(GroupMember, GroupMember.user_id == User.id)
            .where(GroupMember.group_id == group_id)
        )
        return result.scalars().all()


# Singleton instance
group_service = GroupService()
