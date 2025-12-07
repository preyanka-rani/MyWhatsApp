"""
Dependency functions for FastAPI routes.
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from app.core.database import get_db
from app.core.security import security
from app.models import User
from sqlalchemy import select

# Security scheme
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Current user instance

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = security.decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, otherwise None.

    Args:
        authorization: Optional authorization header
        db: Database session

    Returns:
        User instance or None
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    # Decode token
    payload = security.decode_access_token(token)

    if not payload:
        return None

    user_id_str = payload.get("user_id")
    if not user_id_str:
        return None

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
