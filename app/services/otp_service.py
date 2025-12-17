from typing import Optional, Dict
from datetime import datetime, timedelta
from twilio.rest import Client
from app.core.config import settings
from app.core.security import security
from app.core.redis import redis_manager
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """
    Service for OTP generation, verification, and delivery.

    Uses Twilio for SMS delivery and Redis for OTP storage.
    Falls back to in-memory storage when Redis is unavailable.
    """

    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    OTP_KEY_PREFIX = "otp:"
    MAX_ATTEMPTS_KEY_PREFIX = "otp_attempts:"
    MAX_ATTEMPTS = 3

    def __init__(self):
        """Initialize OTP service with Twilio client."""
        self.twilio_client = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.twilio_client = Client(
                settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
            )
        self.from_phone = settings.TWILIO_PHONE_NUMBER
        # In-memory fallback storage when Redis is not available
        self._memory_storage: Dict[str, Dict] = {}

    async def _set_value(self, key: str, value: str, expiry: int):
        """Set value in Redis or memory fallback."""
        if redis_manager.redis_client:
            await redis_manager.set_value(key, value, expiry)
        else:
            # Fallback to in-memory storage
            self._memory_storage[key] = {
                "value": value,
                "expires_at": datetime.utcnow() + timedelta(seconds=expiry),
            }

    async def _get_value(self, key: str) -> Optional[str]:
        """Get value from Redis or memory fallback."""
        if redis_manager.redis_client:
            return await redis_manager.get_value(key)
        else:
            # Fallback to in-memory storage
            if key in self._memory_storage:
                data = self._memory_storage[key]
                if datetime.utcnow() < data["expires_at"]:
                    return data["value"]
                else:
                    # Expired
                    del self._memory_storage[key]
            return None

    async def _delete_value(self, key: str):
        """Delete value from Redis or memory fallback."""
        if redis_manager.redis_client:
            await redis_manager.delete_value(key)
        else:
            # Fallback to in-memory storage
            if key in self._memory_storage:
                del self._memory_storage[key]

    async def request_otp(self, phone_number: str) -> Dict[str, any]:
        """
        Generate and send OTP to phone number.

        Args:
            phone_number: Phone number to send OTP to

        Returns:
            Dictionary with status and message
        """
        # Generate OTP
        otp_code = security.generate_otp(6)

        # Store OTP in Redis with expiry
        redis_key = f"{self.OTP_KEY_PREFIX}{phone_number}"
        await self._set_value(redis_key, otp_code, expiry=self.OTP_EXPIRY_SECONDS)

        # Reset attempts counter
        attempts_key = f"{self.MAX_ATTEMPTS_KEY_PREFIX}{phone_number}"
        await self._set_value(attempts_key, "0", expiry=self.OTP_EXPIRY_SECONDS)

        # Send OTP via SMS
        if self.twilio_client:
            try:
                message = self.twilio_client.messages.create(
                    body=f"Your WhatsApp verification code is: {otp_code}",
                    from_=self.from_phone,
                    to=phone_number,
                )
                logger.info(f"OTP sent to {phone_number} via Twilio: {message.sid}")
                return {
                    "status": "success",
                    "message": "OTP sent successfully",
                    "expires_in": self.OTP_EXPIRY_SECONDS,
                }
            except Exception as e:
                logger.error(f"Failed to send OTP via Twilio: {e}")
                # Fallback to mock OTP for development
                logger.warning(
                    f"DEVELOPMENT MODE: OTP for {phone_number} is {otp_code}"
                )
                return {
                    "status": "success",
                    "message": "OTP sent (development mode)",
                    "otp": otp_code,  # Only in development!
                    "expires_in": self.OTP_EXPIRY_SECONDS,
                }
        else:
            # Development mode - return OTP directly
            logger.warning(f"DEVELOPMENT MODE: OTP for {phone_number} is {otp_code}")
            return {
                "status": "success",
                "message": "OTP generated (development mode)",
                "otp": otp_code,  # Only in development!
                "expires_in": self.OTP_EXPIRY_SECONDS,
            }

    async def verify_otp(self, phone_number: str, otp_code: str) -> bool:
        """
        Verify OTP code for phone number.

        Args:
            phone_number: Phone number
            otp_code: OTP code to verify

        Returns:
            True if valid, False otherwise
        """
        # Check attempts
        attempts_key = f"{self.MAX_ATTEMPTS_KEY_PREFIX}{phone_number}"
        attempts_str = await self._get_value(attempts_key)
        attempts = int(attempts_str) if attempts_str else 0

        if attempts >= self.MAX_ATTEMPTS:
            logger.warning(f"Max OTP attempts exceeded for {phone_number}")
            return False

        # Get stored OTP
        redis_key = f"{self.OTP_KEY_PREFIX}{phone_number}"
        stored_otp = await self._get_value(redis_key)

        if not stored_otp:
            logger.warning(
                f"No OTP found for {phone_number} (expired or not requested)"
            )
            return False

        # Verify OTP
        if stored_otp == otp_code:
            # Clear OTP and attempts
            await self._delete_value(redis_key)
            await self._delete_value(attempts_key)
            logger.info(f"OTP verified successfully for {phone_number}")
            return True
        else:
            # Increment attempts
            await self._set_value(
                attempts_key, str(attempts + 1), expiry=self.OTP_EXPIRY_SECONDS
            )
            logger.warning(f"Invalid OTP for {phone_number} (attempt {attempts + 1})")
            return False


# Singleton instance
otp_service = OTPService()
