import requests
import getpass

STOCKX_AUTH_URL = "https://accounts.stockx.com/oauth/token"

def get_refresh_token():
    """
    An interactive script to guide the user through exchanging an
    authorization code for a refresh token.
    """
    print("--- StockX Refresh Token Generator ---")
    print("This script will help you get your initial refresh token.")
    print("Please follow the steps in docs/guides/stockx_auth_setup.md first.")
    print("-" * 30)

    # Get credentials from user input
    client_id = input("Enter your Client ID: ").strip()
    client_secret = getpass.getpass("Enter your Client Secret: ").strip()
    authorization_code = input("Enter the Authorization Code (from the URL): ").strip()
    callback_uri = input("Enter your Callback/Redirect URI: ").strip()

    if not all([client_id, client_secret, authorization_code, callback_uri]):
        print("\nError: All fields are required. Please try again.")
        return

    # Prepare the request payload
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "redirect_uri": callback_uri,
    }

    print("\nSending request to StockX to get tokens...")

    try:
        response = requests.post(STOCKX_AUTH_URL, data=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        token_data = response.json()
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            print("\nError: Could not retrieve refresh token from StockX.")
            print("Response from server:", token_data)
            return

        print("\n" + "=" * 50)
        print("  SUCCESS!")
        print(f"  Your Refresh Token is: {refresh_token}")
        print("=" * 50)
        print("\nStore this value securely in the 'core.system_config' table")
        print("with the key 'stockx_refresh_token'.")

    except requests.exceptions.HTTPError as e:
        print(f"\n--- HTTP Error ---")
        print(f"Status Code: {e.response.status_code}")
        print(f"Response Body: {e.response.text}")
        print("Please check your credentials and authorization code and try again.")
    except requests.exceptions.RequestException as e:
        print(f"\n--- Network Error ---")
        print(f"An error occurred: {e}")
        print("Please check your internet connection and try again.")
    except Exception as e:
        print(f"\n--- An Unexpected Error Occurred ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    get_refresh_token()
