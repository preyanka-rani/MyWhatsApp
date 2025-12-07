"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import security
from app.services.otp_service import otp_service
from app.models import User
from app.schemas import OTPRequest, OTPVerify, TokenResponse, UserResponse, UserUpdate
from app.api.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/request-otp")
async def request_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Request OTP for phone number authentication.

    Generates and sends a 6-digit OTP to the provided phone number.
    """
    result = await otp_service.request_otp(request.phone_number)
    return result


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify OTP and authenticate user.

    Creates user if doesn't exist, generates JWT token for authenticated session.
    """
    # Verify OTP
    is_valid = await otp_service.verify_otp(request.phone_number, request.otp_code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP"
        )

    # Check if user exists
    result = await db.execute(
        select(User).where(User.phone_number == request.phone_number)
    )
    user = result.scalar_one_or_none()

    # Create user if doesn't exist
    if not user:
        user = User(
            phone_number=request.phone_number,
            name=request.phone_number,  # Default name, can be updated later
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user created: {user.id}")

    # Generate JWT token
    access_token = security.create_access_token(
        data={"user_id": str(user.id), "phone": user.phone_number}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    """
    return current_user


@router.put("/users/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile information.
    """
    if update_data.name is not None:
        current_user.name = update_data.name

    if update_data.about is not None:
        current_user.about = update_data.about

    if update_data.profile_picture_url is not None:
        current_user.profile_picture_url = update_data.profile_picture_url

    await db.commit()
    await db.refresh(current_user)

    logger.info(f"User profile updated: {current_user.id}")
    return current_user
