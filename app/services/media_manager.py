import boto3
from botocore.exceptions import ClientError
from PIL import Image
import io
import os
import uuid
from typing import Tuple, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MediaManager:
    """
    Handles media file operations including upload, download, and processing.

    Integrates with AWS S3 for storage and provides thumbnail generation
    for images and videos.
    """

    def __init__(self):
        """Initialize Media Manager with S3 client."""
        # Only create S3 client if credentials are properly configured
        # Check for valid (non-placeholder) AWS credentials
        valid_key = settings.AWS_ACCESS_KEY_ID and settings.AWS_ACCESS_KEY_ID not in [
            "",
            "your_aws_access_key",
            "your-access-key",
        ]
        valid_secret = (
            settings.AWS_SECRET_ACCESS_KEY
            and settings.AWS_SECRET_ACCESS_KEY
            not in ["", "your_aws_secret_key", "your-secret-key"]
        )
        valid_bucket = settings.S3_BUCKET_NAME and settings.S3_BUCKET_NAME not in [
            "",
            "your-bucket-name",
        ]

        print(
            f"DEBUG: valid_key={valid_key}, valid_secret={valid_secret}, valid_bucket={valid_bucket}"
        )

        if valid_key and valid_secret and valid_bucket:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION,
                )
                logger.info(
                    f"S3 client initialized for bucket: {settings.S3_BUCKET_NAME}"
                )
                print(f" S3 client initialized for bucket: {settings.S3_BUCKET_NAME}")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize S3 client: {e}. Using local storage."
                )
                self.s3_client = None
                print(f" Failed to initialize S3 client: {e}. Using local storage.")
        else:
            logger.info(
                "AWS credentials not configured. Using local storage for media files."
            )
            print(
                " AWS credentials not configured. Using local storage for media files."
            )
            self.s3_client = None

        self.bucket_name = settings.S3_BUCKET_NAME
        self.max_upload_size = settings.MAX_UPLOAD_SIZE
        self.allowed_types = settings.allowed_media_types_list

    def validate_file(
        self, mime_type: str, file_size: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file against size and type restrictions.

        Args:
            mime_type: MIME type of file
            file_size: Size of file in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        if file_size > self.max_upload_size:
            return (
                False,
                f"File size exceeds maximum allowed size of {self.max_upload_size} bytes",
            )

        if mime_type not in self.allowed_types:
            return False, f"File type {mime_type} is not allowed"

        return True, None

    async def upload_to_s3(
        self, file_data: bytes, filename: str, mime_type: str
    ) -> str:
        """
        Upload file to S3 bucket.

        Args:
            file_data: File bytes
            filename: Original filename
            mime_type: MIME type

        Returns:
            S3 URL of uploaded file
        """
        if not self.s3_client:
            # Fallback: save locally for development
            return await self._save_locally(file_data, filename)

        try:
            # Generate unique key
            file_extension = os.path.splitext(filename)[1]
            s3_key = f"media/{uuid.uuid4()}{file_extension}"

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=mime_type,
            )

            # Generate URL
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            logger.info(f"File uploaded to S3: {url}")
            return url

        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    async def _save_locally(self, file_data: bytes, filename: str) -> str:
        """
        Fallback method to save files locally during development.

        Args:
            file_data: File bytes
            filename: Original filename

        Returns:
            Local file path
        """
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as f:
            f.write(file_data)

        logger.info(f"File saved locally: {file_path}")
        return f"/uploads/{unique_filename}"

    async def generate_thumbnail(
        self, image_data: bytes, size: Tuple[int, int] = (200, 200)
    ) -> bytes:
        """
        Generate thumbnail for image.

        Args:
            image_data: Original image bytes
            size: Thumbnail size (width, height)

        Returns:
            Thumbnail image bytes
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail(size, Image.Resampling.LANCZOS)

            # Save thumbnail to bytes
            thumbnail_io = io.BytesIO()
            image.save(thumbnail_io, format="JPEG", quality=85)
            thumbnail_io.seek(0)

            logger.info("Thumbnail generated successfully")
            return thumbnail_io.read()

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            raise

    async def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for S3 object.

        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds

        Returns:
            Presigned URL
        """
        if not self.s3_client:
            return s3_key  # Return original URL for local files

        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            logger.info(f"Presigned URL generated for {s3_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def delete_from_s3(self, s3_key: str):
        """
        Delete file from S3 bucket.

        Args:
            s3_key: S3 object key
        """
        if not self.s3_client:
            # Delete local file
            try:
                if os.path.exists(s3_key):
                    os.remove(s3_key)
                    logger.info(f"Local file deleted: {s3_key}")
            except Exception as e:
                logger.error(f"Failed to delete local file: {e}")
            return

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"File deleted from S3: {s3_key}")

        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            raise


# Singleton instance
media_manager = MediaManager()
