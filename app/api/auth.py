from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import security
from app.services.otp_service import otp_service
from app.models import User
from app.schemas import (
    OTPRequest,
    OTPVerify,
    TokenResponse,
    UserResponse,
    UserUpdate,
    LanguageUpdate,
)
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


@router.get("/users/search", response_model=UserResponse)
async def search_user_by_phone(
    phone_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for a user by phone number.
    """
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with this phone number",
        )

    return user


@router.post("/users/create-or-get", response_model=UserResponse)
async def create_or_get_user(
    phone_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a user if doesn't exist, or return existing user.
    This allows adding contacts without requiring them to login first.
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    user = result.scalar_one_or_none()

    # If user doesn't exist, create them
    if not user:
        user = User(
            phone_number=phone_number,
            name=phone_number,  # Default name
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Auto-created user for contact: {user.id} - {phone_number}")

    return user


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


@router.put("/users/me/language")
async def update_user_language(
    data: LanguageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user's preferred language for message translation.

    Request body: {"language": "bn"}
    """
    from app.services.translation_service import translation_service

    # Validate language code
    supported_languages = translation_service.get_supported_languages()
    if data.language not in supported_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language code. Supported: {list(supported_languages.keys())}",
        )

    current_user.preferred_language = data.language
    await db.commit()
    await db.refresh(current_user)

    logger.info(f"User language updated: {current_user.id} -> {data.language}")

    return {
        "user_id": str(current_user.id),
        "preferred_language": data.language,
        "language_name": supported_languages[data.language],
    }


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported languages for translation.
    """
    from app.services.translation_service import translation_service

    languages = translation_service.get_supported_languages()

    return {
        "languages": [{"code": code, "name": name} for code, name in languages.items()]
    }
