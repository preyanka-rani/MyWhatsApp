from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from app.core.database import get_db
from app.models import Group, User
from app.schemas import (
    GroupCreate,
    GroupUpdate,
    GroupMemberAdd,
    GroupResponse,
    UserResponse,
)
from app.api.dependencies import get_current_user
from app.services.group_service import group_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new group.

    Current user becomes the group admin automatically.
    """
    group = await group_service.create_group(
        db=db,
        name=data.name,
        description=data.description,
        created_by=current_user.id,
        member_ids=data.member_ids,
    )

    return group


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get group details.

    Returns group information including member count.
    """
    group = await group_service.get_group(db, group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    return group


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update group settings (admin only).

    Updates group name, description, or profile picture.
    """
    group = await group_service.update_group(
        db=db,
        group_id=group_id,
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        profile_picture_url=data.profile_picture_url,
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this group",
        )

    return group


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_group_member(
    group_id: uuid.UUID,
    data: GroupMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add member to group (admin only).

    Adds a user to the group and associated conversation.
    """
    member = await group_service.add_member(
        db=db, group_id=group_id, user_id=data.user_id, added_by=current_user.id
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members or user already in group",
        )

    return {"message": "Member added successfully"}


@router.delete(
    "/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_group_member(
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove member from group (admin only).

    Removes user from group and associated conversation.
    """
    success = await group_service.remove_member(
        db=db, group_id=group_id, user_id=member_id, removed_by=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove members",
        )

    return None


@router.get("/{group_id}/members", response_model=List[UserResponse])
async def get_group_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all members of a group.

    Returns list of users who are members of the group.
    """
    members = await group_service.get_group_members(db, group_id)
    return members
