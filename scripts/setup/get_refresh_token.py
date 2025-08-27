import requests
import getpass
import urllib.parse
import asyncio
import os

# This script needs to import from the application's shared modules.
# We add the project root to the Python path to make this possible.
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.database.connection import db_manager
from shared.database.models import SystemConfig

STOCKX_AUTH_URL = "https://accounts.stockx.com/oauth/token"
STOCKX_AUTHORIZE_URL = "https://accounts.stockx.com/authorize"

async def main():
    """
    An interactive, all-in-one script to guide the user through:
    1. Generating an authorization URL.
    2. Exchanging the resulting code for a refresh token.
    3. Securely saving all required credentials to the database.
    """
    print("--- StockX API Setup: All-in-One Credential Manager ---")
    print("This script will guide you through the complete setup process.")
    print("-" * 60)

    # --- Step 1: Get required info and generate URL ---
    client_id = input("1. Enter your Client ID from the StockX developer portal: ").strip()
    callback_uri = input("2. Enter your Callback/Redirect URI (e.g., https://localhost/callback or your n8n webhook): ").strip()

    if not all([client_id, callback_uri]):
        print("\n❌ Error: Client ID and Callback URI are required. Please try again.")
        return

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_uri,
        "scope": "offline_access openid",
        "audience": "gateway.stockx.com",
        "state": "soleflipper-setup"
    }

    auth_url = f"{STOCKX_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    print("\n" + "=" * 70)
    print("3. Open the following URL in your browser to authorize the application:")
    print(f"\n   {auth_url}\n")
    print("After authorizing, StockX will redirect you. Find the 'code' parameter.")
    print("- If using localhost, it will be in your browser's address bar.")
    print("- If using n8n, it will be in the webhook's execution data.")
    print("=" * 70)

    # --- Step 2: Get the authorization code ---
    authorization_code = input("\n4. Paste the 'code' value here: ").strip()

    if not authorization_code:
        print("\n❌ Error: Authorization code cannot be empty.")
        return

    # --- Step 3: Get client secret and exchange code for token ---
    client_secret = getpass.getpass("5. Enter your Client Secret: ").strip()

    if not client_secret:
        print("\n❌ Error: Client Secret is required.")
        return

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "redirect_uri": callback_uri,
    }

    print("\n   -> Sending request to StockX to get your refresh token...")

    try:
        response = requests.post(STOCKX_AUTH_URL, data=payload)
        response.raise_for_status()
        token_data = response.json()
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            print("\n❌ Error: Could not retrieve refresh token from StockX.")
            print("   Response from server:", token_data)
            return

        print("   -> Refresh Token received successfully.")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code} - {e.response.text}")
        return
    except Exception as e:
        print(f"\n❌ An Unexpected Error Occurred: {e}")
        return

    # --- Step 4: Get final credential and save everything to DB ---
    print("\n" + "-" * 60)
    print("Final step: Saving all credentials to the database.")

    api_key = input("6. Enter your general StockX API Key (for the x-api-key header): ").strip()
    if not api_key:
        print("\n❌ Error: API Key is required.")
        return

    try:
        print("   -> Initializing database connection...")
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            credentials_to_save = {
                "stockx_client_id": client_id,
                "stockx_client_secret": client_secret,
                "stockx_refresh_token": refresh_token,
                "stockx_api_key": api_key,
            }

            print("   -> Saving credentials (values will be encrypted)...")
            for key, value in credentials_to_save.items():
                config_entry = await session.get(SystemConfig, key)
                if not config_entry:
                    config_entry = SystemConfig(key=key)
                    session.add(config_entry)
                config_entry.set_value(value)

            print("   -> Changes prepared. The session will now be committed.")

    except Exception as e:
        print(f"\n❌ Error saving to database: {e}")
        print("   Please ensure your DATABASE_URL is correct in your .env file.")
        return
    finally:
        await db_manager.close()
        print("   -> Database connection closed.")

    print("\n" + "=" * 50)
    print("  ✅ SUCCESS! All credentials have been securely saved.")
    print("=" * 50)
    print("\nYou can now run the main application.")


if __name__ == "__main__":
    # Load .env file to get DATABASE_URL and FIELD_ENCRYPTION_KEY
    from dotenv import load_dotenv
    load_dotenv()

    # Check for encryption key before running
    if not os.getenv("FIELD_ENCRYPTION_KEY"):
        print("❌ FATAL ERROR: The 'FIELD_ENCRYPTION_KEY' environment variable is not set.")
        print("   Please set it in your .env file before running this script.")
    else:
        asyncio.run(main())
