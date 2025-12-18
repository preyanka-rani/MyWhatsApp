import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class WhatsAppAPIClient:
    """
    Client for WhatsApp Business API integration.

    This class handles sending messages, media, and processing webhook events
    from the WhatsApp Business API.
    """

    BASE_URL = "https://graph.facebook.com/v24.0"

    def __init__(self):
        """Initialize WhatsApp API client with credentials from settings."""
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.business_account_id = settings.WHATSAPP_BUSINESS_ACCOUNT_ID

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_message(
        self, to: str, message_text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp Business API.

        Args:
            to: Recipient phone number (with country code)
            message_text: Text message content
            preview_url: Enable URL preview

        Returns:
            API response with message ID
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": preview_url, "body": message_text},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Message sent successfully to {to}: {result}")
                return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def send_media(
        self,
        to: str,
        media_type: str,
        media_id: Optional[str] = None,
        media_link: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send media (image, video, audio, document) via WhatsApp.

        Args:
            to: Recipient phone number
            media_type: Type of media (image, video, audio, document)
            media_id: WhatsApp media ID (if already uploaded)
            media_link: Direct URL to media file
            caption: Optional caption for media
            filename: Optional filename for documents

        Returns:
            API response with message ID
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

        media_object = {}
        if media_id:
            media_object["id"] = media_id
        elif media_link:
            media_object["link"] = media_link
        else:
            raise ValueError("Either media_id or media_link must be provided")

        if caption and media_type in ["image", "video"]:
            media_object["caption"] = caption

        if filename and media_type == "document":
            media_object["filename"] = filename

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_object,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Media sent successfully to {to}: {result}")
                return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to send media: {e}")
            raise

    async def upload_media(self, file_path: str, mime_type: str) -> str:
        """
        Upload media to WhatsApp servers.

        Args:
            file_path: Path to media file
            mime_type: MIME type of file

        Returns:
            WhatsApp media ID
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/media"

        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    files = {"file": (file_path, f, mime_type)}
                    data = {"messaging_product": "whatsapp"}

                    response = await client.post(
                        url,
                        files=files,
                        data=data,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                    )
                    response.raise_for_status()
                    result = response.json()
                    media_id = result.get("id")
                    logger.info(f"Media uploaded successfully: {media_id}")
                    return media_id
        except httpx.HTTPError as e:
            logger.error(f"Failed to upload media: {e}")
            raise

    async def download_media(self, media_id: str) -> bytes:
        """
        Download media from WhatsApp servers.

        Args:
            media_id: WhatsApp media ID

        Returns:
            Media file bytes
        """
        # First, get the media URL
        url = f"{self.BASE_URL}/{media_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                media_info = response.json()
                media_url = media_info.get("url")

                # Download the actual media
                media_response = await client.get(media_url, headers=self.headers)
                media_response.raise_for_status()
                logger.info(f"Media downloaded successfully: {media_id}")
                return media_response.content
        except httpx.HTTPError as e:
            logger.error(f"Failed to download media: {e}")
            raise

    async def delete_message(self, whatsapp_message_id: str) -> Dict[str, Any]:
        """
        Delete a WhatsApp message (delete for everyone).

        Args:
            whatsapp_message_id: WhatsApp message ID to delete

        Returns:
            API response confirming deletion

        Raises:
            httpx.HTTPError: If deletion fails
        """
        # Correct endpoint: DELETE /{phone_number_id}/messages/{message_id}
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages/{whatsapp_message_id}"

        # Only Authorization header needed for DELETE
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        try:
            async with httpx.AsyncClient() as client:
                # Use DELETE HTTP method
                response = await client.delete(url, headers=headers)
                response.raise_for_status()
                result = response.json()
                logger.info(
                    f"Message {whatsapp_message_id} deleted successfully: {result}"
                )
                return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete message {whatsapp_message_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    def parse_webhook_event(
        self, webhook_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook event from WhatsApp.

        Args:
            webhook_data: Raw webhook data from WhatsApp

        Returns:
            Parsed event data or None if invalid
        """
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            # Extract messages
            messages = value.get("messages", [])
            if messages:
                message = messages[0]
                return {
                    "type": "message",
                    "from": message.get("from"),
                    "message_id": message.get("id"),
                    "timestamp": message.get("timestamp"),
                    "message_type": message.get("type"),
                    "text": (
                        message.get("text", {}).get("body")
                        if message.get("type") == "text"
                        else None
                    ),
                    "media": (
                        message.get(message.get("type"))
                        if message.get("type") != "text"
                        else None
                    ),
                }

            # Extract status updates
            statuses = value.get("statuses", [])
            if statuses:
                status = statuses[0]
                return {
                    "type": "status",
                    "message_id": status.get("id"),
                    "status": status.get("status"),
                    "timestamp": status.get("timestamp"),
                    "recipient_id": status.get("recipient_id"),
                }

            return None
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")
            return None


# Singleton instance
whatsapp_client = WhatsAppAPIClient()
