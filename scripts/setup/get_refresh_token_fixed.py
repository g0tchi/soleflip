import asyncio
import getpass
import os
import sys
import urllib.parse

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.database.connection import db_manager
from shared.database.models import SystemConfig

STOCKX_AUTH_URL = "https://accounts.stockx.com/oauth/token"
STOCKX_AUTHORIZE_URL = "https://accounts.stockx.com/authorize"


def get_input(prompt: str) -> str:
    """Robust input function that handles copy-paste issues."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    value = sys.stdin.readline().strip()
    return value


async def main():
    """
    An interactive, all-in-one script to guide the user through:
    1. Generating an authorization URL.
    2. Exchanging the resulting code for a refresh token.
    3. Securely saving all required credentials to the database.
    """
    print("=" * 80)
    print("StockX API Setup: All-in-One Credential Manager")
    print("=" * 80)
    print("This script will guide you through the complete setup process.")
    print("-" * 80)
    print()

    # --- Step 1: Get required info and generate URL ---
    print("Step 1: Enter your StockX API credentials")
    print("-" * 80)
    client_id = get_input("Enter your Client ID from the StockX developer portal: ")

    if not client_id:
        print("\n❌ Error: Client ID is required. Please try again.")
        return

    print(f"✓ Client ID received: {client_id[:20]}...")
    print()

    callback_uri = get_input("Enter your Callback/Redirect URI (e.g., https://localhost/callback): ")

    if not callback_uri:
        print("\n❌ Error: Callback URI is required. Please try again.")
        return

    print(f"✓ Callback URI received: {callback_uri}")
    print()

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_uri,
        "scope": "offline_access openid",
        "audience": "gateway.stockx.com",
        "state": "soleflipper-setup",
    }

    auth_url = f"{STOCKX_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    print("=" * 80)
    print("Step 2: Authorize the application")
    print("=" * 80)
    print("Open the following URL in your browser:")
    print()
    print(f"   {auth_url}")
    print()
    print("After authorizing, StockX will redirect you. Find the 'code' parameter:")
    print("- If using localhost, it will be in your browser's address bar")
    print("- If using n8n webhook, it will be in the webhook execution data")
    print("=" * 80)
    print()

    # --- Step 2: Get the authorization code ---
    authorization_code = get_input("Paste the 'code' value here: ")

    if not authorization_code:
        print("\n❌ Error: Authorization code cannot be empty.")
        return

    print(f"✓ Authorization code received: {authorization_code[:20]}...")
    print()

    # --- Step 3: Get client secret and exchange code for token ---
    print("=" * 80)
    print("Step 3: Enter Client Secret")
    print("=" * 80)
    client_secret = getpass.getpass("Enter your Client Secret (input hidden): ").strip()

    if not client_secret:
        print("\n❌ Error: Client Secret is required.")
        return

    print("✓ Client Secret received (hidden)")
    print()

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "redirect_uri": callback_uri,
    }

    print("=" * 80)
    print("Step 4: Exchanging authorization code for refresh token")
    print("=" * 80)
    print(f"Sending request to: {STOCKX_AUTH_URL}")
    print()

    try:
        response = requests.post(STOCKX_AUTH_URL, data=payload)
        response.raise_for_status()
        token_data = response.json()
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            print("\n❌ Error: Could not retrieve refresh token from StockX.")
            print("Response from server:", token_data)
            return

        print("✓ Refresh Token received successfully")
        print(f"  Token preview: {refresh_token[:20]}...")
        print()

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return

    # --- Step 4: Get final credential and save everything to DB ---
    print("=" * 80)
    print("Step 5: Enter API Key and save credentials")
    print("=" * 80)
    api_key = get_input("Enter your StockX API Key (for the x-api-key header): ")

    if not api_key:
        print("\n❌ Error: API Key is required.")
        return

    print(f"✓ API Key received: {api_key[:20]}...")
    print()

    try:
        print("=" * 80)
        print("Step 6: Saving credentials to database")
        print("=" * 80)
        print("Initializing database connection...")
        await db_manager.initialize()
        print("✓ Database connected")
        print()

        async with db_manager.get_session() as session:
            credentials_to_save = {
                "stockx_client_id": client_id,
                "stockx_client_secret": client_secret,
                "stockx_refresh_token": refresh_token,
                "stockx_api_key": api_key,
            }

            print("Saving credentials (values will be encrypted)...")
            for key, value in credentials_to_save.items():
                config_entry = await session.get(SystemConfig, key)
                if not config_entry:
                    config_entry = SystemConfig(key=key)
                    session.add(config_entry)
                config_entry.set_value(value)
                print(f"  ✓ {key}")

            await session.commit()
            print()
            print("✓ All credentials committed to database")

    except Exception as e:
        print(f"\n❌ Error saving to database: {e}")
        print("Please ensure your DATABASE_URL is correct in your .env file.")
        import traceback
        traceback.print_exc()
        return
    finally:
        await db_manager.close()
        print("✓ Database connection closed")

    print()
    print("=" * 80)
    print("  ✅ SUCCESS! All credentials have been securely saved.")
    print("=" * 80)
    print()
    print("You can now:")
    print("  1. Run the API: make dev")
    print("  2. Test credentials: python scripts/check_stockx_credentials.py")
    print("  3. Refresh token: python scripts/refresh_stockx_token.py")
    print()


if __name__ == "__main__":
    # Load .env file to get DATABASE_URL and FIELD_ENCRYPTION_KEY
    from dotenv import load_dotenv

    load_dotenv()

    # Check for encryption key before running
    if not os.getenv("FIELD_ENCRYPTION_KEY"):
        print("=" * 80)
        print("❌ FATAL ERROR: The 'FIELD_ENCRYPTION_KEY' environment variable is not set.")
        print("=" * 80)
        print()
        print("Please set it in your .env file before running this script.")
        print()
        print("You can generate one with:")
        print('  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
        print()
    else:
        asyncio.run(main())
