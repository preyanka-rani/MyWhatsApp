from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class Media(Base):
    """
    Media model for storing file metadata.

    Attributes:
        id: Unique media identifier (UUID)
        filename: Original filename
        mime_type: MIME type of the file
        size: File size in bytes
        url: S3 URL or storage path
        thumbnail_url: Optional thumbnail URL (for images/videos)
        whatsapp_media_id: WhatsApp API media ID
        uploaded_by: Foreign key to user who uploaded
        created_at: Upload timestamp
    """

    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    whatsapp_media_id = Column(String(255), nullable=True, index=True)
    uploaded_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    uploader = relationship("User")
    message = relationship("Message", back_populates="media", uselist=False)

    def __repr__(self):
        return f"<Media(id={self.id}, filename={self.filename}, type={self.mime_type})>"

    def to_dict(self):
        """Convert media to dictionary representation."""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size": self.size,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "whatsapp_media_id": self.whatsapp_media_id,
            "uploaded_by": str(self.uploaded_by),
            "created_at": self.created_at.isoformat(),
        }
