import asyncio
import httpx
import websockets
import json
from pathlib import Path


class MediaSharingExample:
    """Example class for media sharing operations."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.user_id = None

    async def authenticate(self, phone_number: str, otp_code: str):
        """Authenticate and get access token."""
        async with httpx.AsyncClient() as client:
            # Request OTP
            print(f"📱 Requesting OTP for {phone_number}...")
            response = await client.post(
                f"{self.base_url}/api/auth/request-otp",
                json={"phone_number": phone_number},
            )
            print(f" OTP requested: {response.json()}")

            # Verify OTP
            print(f" Verifying OTP...")
            response = await client.post(
                f"{self.base_url}/api/auth/verify-otp",
                json={"phone_number": phone_number, "otp_code": otp_code},
            )
            data = response.json()
            self.token = data["access_token"]
            self.user_id = data["user"]["id"]
            print(f" Authenticated! Token: {self.token[:20]}...")
            return self.token

    async def upload_media(self, file_path: str) -> dict:
        """
        Upload a media file (image, video, audio, or document).

        Args:
            file_path: Path to the file to upload

        Returns:
            Media object with ID and URL
        """
        headers = {"Authorization": f"Bearer {self.token}"}
        file = Path(file_path)

        if not file.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine MIME type
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        mime_type = mime_types.get(file.suffix.lower(), "application/octet-stream")

        print(f" Uploading {file.name} ({mime_type})...")

        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": (file.name, f, mime_type)}
                response = await client.post(
                    f"{self.base_url}/api/media", headers=headers, files=files
                )

            if response.status_code == 201:
                media = response.json()
                print(f" Media uploaded successfully!")
                print(f"   ID: {media['id']}")
                print(f"   URL: {media['url']}")
                print(f"   Size: {media['size']} bytes")
                if media.get("thumbnail_url"):
                    print(f"   Thumbnail: {media['thumbnail_url']}")
                return media
            else:
                print(f" Upload failed: {response.text}")
                raise Exception(f"Upload failed: {response.status_code}")

    async def send_image(
        self, conversation_id: str, file_path: str, caption: str = None
    ):
        """Send an image message."""
        # Upload image
        media = await self.upload_media(file_path)

        # Send message
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "type": "IMAGE",
                    "media_id": media["id"],
                    "content": caption,
                },
            )

            if response.status_code == 201:
                message = response.json()
                print(f" Image message sent!")
                print(f"   Message ID: {message['id']}")
                return message
            else:
                print(f" Failed to send message: {response.text}")

    async def send_video(
        self, conversation_id: str, file_path: str, caption: str = None
    ):
        """Send a video message."""
        media = await self.upload_media(file_path)

        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "type": "VIDEO",
                    "media_id": media["id"],
                    "content": caption,
                },
            )

            if response.status_code == 201:
                message = response.json()
                print(f" Video message sent!")
                print(f"   Message ID: {message['id']}")
                return message
            else:
                print(f" Failed to send message: {response.text}")

    async def send_audio(self, conversation_id: str, file_path: str):
        """Send an audio message."""
        media = await self.upload_media(file_path)

        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "type": "AUDIO",
                    "media_id": media["id"],
                },
            )

            if response.status_code == 201:
                message = response.json()
                print(f" Audio message sent!")
                print(f"   Message ID: {message['id']}")
                return message
            else:
                print(f" Failed to send message: {response.text}")

    async def send_document(
        self, conversation_id: str, file_path: str, caption: str = None
    ):
        """Send a document message."""
        media = await self.upload_media(file_path)

        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "type": "DOCUMENT",
                    "media_id": media["id"],
                    "content": caption,
                },
            )

            if response.status_code == 201:
                message = response.json()
                print(f" Document message sent!")
                print(f"   Message ID: {message['id']}")
                return message
            else:
                print(f" Failed to send message: {response.text}")

    async def receive_messages_websocket(self):
        """Connect to WebSocket and receive real-time messages including media."""
        uri = f"ws://localhost:8000/ws?token={self.token}"

        print(f"🔌 Connecting to WebSocket...")

        async with websockets.connect(uri) as websocket:
            print(f" Connected to WebSocket!")

            # Send heartbeat periodically
            async def send_heartbeat():
                while True:
                    await asyncio.sleep(30)
                    await websocket.send(json.dumps({"type": "heartbeat"}))

            # Start heartbeat task
            heartbeat_task = asyncio.create_task(send_heartbeat())

            try:
                # Receive messages
                async for message in websocket:
                    data = json.loads(message)
                    print("\n" + "=" * 60)
                    print(f" Received: {data['type']}")

                    if data["type"] == "new_message":
                        msg = data["message"]
                        print(f"   From: {msg['sender_id']}")
                        print(f"   Type: {msg['type']}")

                        if msg["type"] == "TEXT":
                            print(f"   Content: {msg['content']}")
                        elif msg.get("media"):
                            # Media message
                            media = msg["media"]
                            print(f"   Media URL: {media['url']}")
                            print(f"   MIME Type: {media['mime_type']}")
                            print(f"   Filename: {media['filename']}")
                            print(f"   Size: {media['size']} bytes")
                            if media.get("thumbnail_url"):
                                print(f"   Thumbnail: {media['thumbnail_url']}")
                            if msg.get("content"):
                                print(f"   Caption: {msg['content']}")

                    elif data["type"] == "typing_indicator":
                        user_id = data.get("user_id")
                        is_typing = data.get("is_typing")
                        print(
                            f"   User {user_id} is {'typing...' if is_typing else 'stopped typing'}"
                        )

                    elif data["type"] == "presence_update":
                        user_id = data.get("user_id")
                        is_online = data.get("is_online")
                        print(
                            f"   User {user_id} is {'online' if is_online else 'offline'}"
                        )

                    print("=" * 60)

            except websockets.exceptions.ConnectionClosed:
                print(" WebSocket connection closed")
            finally:
                heartbeat_task.cancel()

    async def get_conversation_messages(self, conversation_id: str, limit: int = 50):
        """Get messages from a conversation (includes media details)."""
        headers = {"Authorization": f"Bearer {self.token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/conversations/{conversation_id}/messages",
                headers=headers,
                params={"limit": limit},
            )

            if response.status_code == 200:
                messages = response.json()
                print(f" Retrieved {len(messages)} messages")

                for msg in messages:
                    print(f"\n--- Message {msg['id'][:8]}... ---")
                    print(f"Type: {msg['type']}")
                    print(f"Status: {msg['status']}")

                    if msg["type"] == "TEXT":
                        print(f"Content: {msg['content']}")
                    elif msg.get("media"):
                        media = msg["media"]
                        print(f"Media: {media['filename']}")
                        print(f"URL: {media['url']}")
                        print(f"Size: {media['size']} bytes")
                        if msg.get("content"):
                            print(f"Caption: {msg['content']}")

                return messages
            else:
                print(f" Failed to get messages: {response.text}")

    async def download_media(self, media_url: str, save_path: str):
        """Download media file from URL."""
        print(f"⬇  Downloading from {media_url}...")

        async with httpx.AsyncClient() as client:
            response = await client.get(media_url)

            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                print(f" Saved to {save_path}")
            else:
                print(f" Download failed: {response.status_code}")


async def main():
    """Main example function."""
    example = MediaSharingExample()

    # Authenticate
    await example.authenticate(
        phone_number="+1234567890",  # Replace with your phone number
        otp_code="123456",  # Replace with actual OTP
    )

    # Example 1: Send an image with caption
    conversation_id = "your-conversation-id-here"  # Replace with actual conversation ID

    print("\n" + "=" * 60)
    print("Example 1: Send Image")
    print("=" * 60)
    # await example.send_image(
    #     conversation_id=conversation_id,
    #     file_path="path/to/image.jpg",
    #     caption="Check out this image! "
    # )

    # Example 2: Send a video
    print("\n" + "=" * 60)
    print("Example 2: Send Video")
    print("=" * 60)
    # await example.send_video(
    #     conversation_id=conversation_id,
    #     file_path="path/to/video.mp4",
    #     caption="Amazing video! "
    # )

    # Example 3: Send audio
    print("\n" + "=" * 60)
    print("Example 3: Send Audio")
    print("=" * 60)
    # await example.send_audio(
    #     conversation_id=conversation_id,
    #     file_path="path/to/audio.mp3"
    # )

    # Example 4: Send document
    print("\n" + "=" * 60)
    print("Example 4: Send Document")
    print("=" * 60)
    # await example.send_document(
    #     conversation_id=conversation_id,
    #     file_path="path/to/document.pdf",
    #     caption="Important document "
    # )

    # Example 5: Get conversation messages with media
    print("\n" + "=" * 60)
    print("Example 5: Get Messages")
    print("=" * 60)
    # await example.get_conversation_messages(conversation_id=conversation_id)

    # Example 6: Receive messages via WebSocket (includes media)
    print("\n" + "=" * 60)
    print("Example 6: WebSocket - Receive Real-time Messages")
    print("=" * 60)
    await example.receive_messages_websocket()


if __name__ == "__main__":
    asyncio.run(main())
