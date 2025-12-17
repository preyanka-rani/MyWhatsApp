from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # WhatsApp Business API Configuration
    WHATSAPP_ACCESS_TOKEN: str = Field(
        ..., description="WhatsApp Business API access token"
    )
    WHATSAPP_PHONE_NUMBER_ID: str = Field(..., description="WhatsApp phone number ID")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = Field(
        ..., description="WhatsApp business account ID"
    )
    WHATSAPP_BUSINESS_PHONE: str = Field(
        default="+8801608529761", description="WhatsApp business phone number"
    )
    VERIFY_TOKEN: str = Field(..., description="Webhook verification token")

    # Database Configuration
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    DATABASE_POOL_SIZE: int = Field(
        default=20, description="Database connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10, description="Max overflow connections"
    )

    # Redis Configuration
    REDIS_URL: str = Field(..., description="Redis connection URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Max Redis connections")

    # JWT Configuration
    SECRET_KEY: str = Field(..., description="Secret key for JWT encoding")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=43200, description="JWT expiration (30 days)"
    )

    # Twilio Configuration (for OTP)
    TWILIO_ACCOUNT_SID: str = Field(default="", description="Twilio account SID")
    TWILIO_AUTH_TOKEN: str = Field(default="", description="Twilio auth token")
    TWILIO_PHONE_NUMBER: str = Field(default="", description="Twilio phone number")

    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = Field(default="", description="AWS access key")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", description="AWS secret key")
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    S3_BUCKET_NAME: str = Field(default="", description="S3 bucket name")

    # Application Configuration
    APP_NAME: str = Field(default="WhatsApp Clone API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ALLOWED_ORIGINS: str = Field(default="*", description="CORS allowed origins")
    PUBLIC_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Public base URL for media access (use ngrok URL for WhatsApp)",
    )

    # Media Configuration
    MAX_UPLOAD_SIZE: int = Field(
        default=10485760, description="Max upload size in bytes (10MB)"
    )
    ALLOWED_MEDIA_TYPES: str = Field(
        default="image/jpeg,image/png,image/gif,video/mp4,audio/mpeg,application/pdf",
        description="Allowed media MIME types",
    )

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/1", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/2", description="Celery result backend"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins into a list."""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def allowed_media_types_list(self) -> List[str]:
        """Parse allowed media types into a list."""
        return [mime.strip() for mime in self.ALLOWED_MEDIA_TYPES.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
