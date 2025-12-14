import asyncio
import websockets
import json
from datetime import datetime


async def test_websocket_connection(token: str):
    """
    Test WebSocket connection and real-time messaging.

    Args:
        token: JWT authentication token
    """
    uri = f"ws://localhost:8000/ws?token={token}"

    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print(" Connected!")

        # Receive welcome message
        welcome = await websocket.recv()
        print(f" Received: {welcome}")

        # Send heartbeat
        print("\n Sending heartbeat...")
        await websocket.send(json.dumps({"type": "heartbeat"}))

        # Receive heartbeat acknowledgment
        response = await websocket.recv()
        print(f" Received: {response}")

        # Send typing indicator
        print("\n  Sending typing indicator...")
        conversation_id = input("Enter conversation_id: ")

        await websocket.send(
            json.dumps(
                {
                    "type": "typing_indicator",
                    "conversation_id": conversation_id,
                    "is_typing": True,
                }
            )
        )

        print(" Typing indicator sent")

        # Wait for messages
        print("\n Listening for messages (Press Ctrl+C to stop)...")

        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)

                print(f"\n New event received:")
                print(f"   Type: {data.get('type')}")
                print(f"   Data: {json.dumps(data, indent=2)}")

        except KeyboardInterrupt:
            print("\n\n Closing connection...")

            # Stop typing before disconnect
            await websocket.send(
                json.dumps(
                    {
                        "type": "typing_indicator",
                        "conversation_id": conversation_id,
                        "is_typing": False,
                    }
                )
            )


async def test_multiple_events(token: str, conversation_id: str):
    """
    Test sending multiple WebSocket events.

    Args:
        token: JWT authentication token
        conversation_id: Conversation ID for testing
    """
    uri = f"ws://localhost:8000/ws?token={token}"

    async with websockets.connect(uri) as websocket:
        # Receive welcome
        welcome = await websocket.recv()
        print(f"Connected: {json.loads(welcome)}")

        # Test 1: Typing indicator
        print("\n1️ Testing typing indicator...")
        await websocket.send(
            json.dumps(
                {
                    "type": "typing_indicator",
                    "conversation_id": conversation_id,
                    "is_typing": True,
                }
            )
        )
        await asyncio.sleep(2)

        await websocket.send(
            json.dumps(
                {
                    "type": "typing_indicator",
                    "conversation_id": conversation_id,
                    "is_typing": False,
                }
            )
        )
        print(" Typing indicator test complete")

        # Test 2: Heartbeat
        print("\n2️ Testing heartbeat...")
        await websocket.send(json.dumps({"type": "heartbeat"}))

        response = await websocket.recv()
        print(f" Heartbeat response: {json.loads(response)}")

        # Test 3: Mark message as read
        print("\n3️ Testing message read receipt...")
        message_id = input("Enter message_id to mark as read: ")

        if message_id:
            await websocket.send(
                json.dumps({"type": "message_read", "message_id": message_id})
            )
            print(" Read receipt sent")

        # Listen for incoming events
        print("\n4️ Listening for events for 10 seconds...")

        try:
            await asyncio.wait_for(listen_for_events(websocket), timeout=10.0)
        except asyncio.TimeoutError:
            print(" Timeout reached")


async def listen_for_events(websocket):
    """Listen for incoming WebSocket events."""
    while True:
        message = await websocket.recv()
        data = json.loads(message)
        print(f" Event: {data.get('type')} | {data}")


def main():
    """Main function to run WebSocket tests."""
    print("=" * 60)
    print("WhatsApp Clone - WebSocket Client Test")
    print("=" * 60)

    # Get token from user
    token = input("\nEnter your JWT token: ").strip()

    if not token:
        print(" Token is required!")
        return

    print("\nSelect test mode:")
    print("1. Interactive mode (listen for events)")
    print("2. Automated test mode")

    choice = input("\nEnter choice (1 or 2): ").strip()

    try:
        if choice == "1":
            asyncio.run(test_websocket_connection(token))
        elif choice == "2":
            conversation_id = input("Enter conversation_id: ").strip()
            if conversation_id:
                asyncio.run(test_multiple_events(token, conversation_id))
            else:
                print(" Conversation ID is required for automated tests!")
        else:
            print(" Invalid choice!")
    except Exception as e:
        print(f"\n Error: {e}")


if __name__ == "__main__":
    main()
