"""Services module initialization."""

from app.services.whatsapp_client import whatsapp_client, WhatsAppAPIClient
from app.services.media_manager import media_manager, MediaManager
from app.services.message_service import message_service, MessageService
from app.services.group_service import group_service, GroupService
from app.services.presence_service import presence_service, PresenceService
from app.services.notification_service import notification_service, NotificationService

__all__ = [
    "whatsapp_client",
    "WhatsAppAPIClient",
    "media_manager",
    "MediaManager",
    "message_service",
    "MessageService",
    "group_service",
    "GroupService",
    "presence_service",
    "PresenceService",
    "notification_service",
    "NotificationService",
]
