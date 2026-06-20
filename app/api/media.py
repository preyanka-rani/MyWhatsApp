from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.core.database import get_db
from app.models import Media, User
from app.schemas import MediaUploadResponse
from app.api.dependencies import get_current_user
from app.services.media_manager import media_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    "", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload media file (image, video, audio, document).

    Validates file type and size, uploads to S3, generates thumbnail for images.
    """
    # Read file
    file_data = await file.read()
    file_size = len(file_data)
    mime_type = file.content_type or "application/octet-stream"

    # Validate file
    is_valid, error_message = media_manager.validate_file(mime_type, file_size)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    # Upload to S3
    try:
        url = await media_manager.upload_to_s3(
            file_data=file_data, filename=file.filename, mime_type=mime_type
        )
        logger.info(f"Media uploaded to: {url}")
    except Exception as e:
        logger.error(f"Failed to upload media: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )

    # Generate thumbnail for images
    thumbnail_url = None
    if mime_type.startswith("image/"):
        try:
            thumbnail_data = await media_manager.generate_thumbnail(file_data)
            thumbnail_url = await media_manager.upload_to_s3(
                file_data=thumbnail_data,
                filename=f"thumb_{file.filename}",
                mime_type="image/jpeg",
            )
            logger.info(f"Thumbnail generated: {thumbnail_url}")
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}", exc_info=True)
            # Don't fail the upload if thumbnail generation fails

    # Create media record
    media = Media(
        filename=file.filename,
        mime_type=mime_type,
        size=file_size,
        url=url,
        thumbnail_url=thumbnail_url,
        uploaded_by=current_user.id,
    )

    db.add(media)
    await db.commit()
    await db.refresh(media)

    logger.info(f"Media uploaded: {media.id}")
    return media


@router.get("/{media_id}", response_model=MediaUploadResponse)
async def get_media(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get media details by ID.

    Returns media metadata including URL.
    """
    media = await db.get(Media, media_id)

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    return media
