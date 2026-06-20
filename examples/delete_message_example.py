import os
import requests
import argparse
from urllib.parse import urljoin
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings


def delete_message_for_everyone(api_base_url: str, token: str, message_id: str):
    """
    Calls the API to delete a message for everyone in the conversation.

    Args:
        api_base_url (str): The base URL of the API.
        token (str): The authentication token.
        message_id (str): The UUID of the message to delete.

    Returns:
        bool: True if the request was successful (204 No Content), False otherwise.
    """
    headers = {"Authorization": f"Bearer {token}"}
    # The endpoint is /messages/{message_id}
    endpoint = f"messages/{message_id}"
    url = urljoin(api_base_url, endpoint)

    # Add the query parameter to delete for everyone
    params = {"delete_for_everyone": "true"}

    print(f"Sending DELETE request to: {url}")
    print(f"  - Headers: {headers}")
    print(f"  - Params: {params}")

    try:
        response = requests.delete(url, headers=headers, params=params)

        if response.status_code == 204:
            print("\nSuccess: Message deleted for everyone.")
            print("Server responded with 204 No Content as expected.")
            return True
        else:
            print(f"\nError: Failed to delete message.")
            print(f"  - Status Code: {response.status_code}")
            try:
                # Try to print JSON error detail if available
                print(f"  - Response Body: {response.json()}")
            except requests.exceptions.JSONDecodeError:
                print(f"  - Response Body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred during the request: {e}")
        return False


def main():
    """
    Main function to parse arguments and execute the delete message script.
    """
    parser = argparse.ArgumentParser(
        description="Delete a specific message for ALL participants in a conversation.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "message_id", type=str, help="The UUID of the message to be deleted."
    )
    parser.add_argument(
        "-t",
        "--token",
        type=str,
        required=True,
        help="The authentication JWT token for the user sending the message.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost",
        help="The host of the API server.",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="The port of the API server."
    )

    args = parser.parse_args()

    api_base_url = f"{args.host}:{args.port}/"
    print("-----------------------------------")
    print("--- Delete Message for Everyone ---")
    print("-----------------------------------")
    print(f"API Server: {api_base_url}")
    print(f"User Token: {args.token[:15]}...")  # Show partial token
    print(f"Message ID: {args.message_id}")
    print("-----------------------------------\n")

    delete_message_for_everyone(
        api_base_url=api_base_url, token=args.token, message_id=args.message_id
    )


if __name__ == "__main__":
    main()
