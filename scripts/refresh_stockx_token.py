"""
Refresh StockX OAuth Access Token
This script manually refreshes the StockX access token using the refresh token stored in the database.
"""

import asyncio

import httpx
import structlog
from sqlalchemy import select

from shared.database.connection import db_manager
from shared.database.models import SystemConfig

logger = structlog.get_logger(__name__)

STOCKX_AUTH_URL = "https://accounts.stockx.com/oauth/token"


async def refresh_stockx_token():
    """Refresh StockX access token using refresh token from database."""

    print("\n" + "=" * 80)
    print("StockX Token Refresh Script")
    print("=" * 80 + "\n")

    try:
        # Initialize database
        await db_manager.initialize()
        print("[OK] Database connection established\n")

        # Load credentials from database
        async with db_manager.get_session() as session:
            print("Loading StockX credentials from core.system_config...")

            keys = [
                "stockx_client_id",
                "stockx_client_secret",
                "stockx_refresh_token",
                "stockx_api_key",
            ]

            result = await session.execute(select(SystemConfig).where(SystemConfig.key.in_(keys)))
            configs = {row.key: row.get_value() for row in result.scalars()}

            # Check if all required credentials are present
            missing = [key for key in keys if key not in configs]
            if missing:
                print(f"\n[ERROR] Missing credentials in database: {', '.join(missing)}")
                return

            print("[OK] All credentials loaded from database")
            print(f"   - Client ID: {configs['stockx_client_id'][:20]}...")
            print(f"   - Client Secret: {'*' * 40}")
            print(f"   - Refresh Token: {configs['stockx_refresh_token'][:20]}...")
            print(f"   - API Key: {configs['stockx_api_key'][:20]}...\n")

            # Prepare OAuth2 refresh token request
            payload = {
                "grant_type": "refresh_token",
                "client_id": configs["stockx_client_id"],
                "client_secret": configs["stockx_client_secret"],
                "refresh_token": configs["stockx_refresh_token"],
            }

            print(f"Sending refresh token request to: {STOCKX_AUTH_URL}")

            # Make request to StockX OAuth server
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(STOCKX_AUTH_URL, data=payload)

                    print(f"Response Status: {response.status_code}")

                    if response.status_code == 200:
                        token_data = response.json()

                        print("\n[SUCCESS] Token refresh successful!\n")
                        print("New token details:")
                        print(f"   - Access Token: {token_data.get('access_token', '')[:40]}...")
                        print(f"   - Token Type: {token_data.get('token_type', 'N/A')}")
                        print(f"   - Expires In: {token_data.get('expires_in', 'N/A')} seconds")

                        if "scope" in token_data:
                            print(f"   - Scope: {token_data['scope']}")

                        print(
                            "\n[NOTE] Access token is temporary and cached in memory by StockXService"
                        )
                        print("   The refresh token in database remains valid and can be reused.")

                    else:
                        print("\n[ERROR] Token refresh failed!")
                        print(f"Status Code: {response.status_code}")
                        print(f"Response: {response.text}\n")

                        # Try to parse error details
                        try:
                            error_data = response.json()
                            if "error" in error_data:
                                print(f"Error: {error_data['error']}")
                            if "error_description" in error_data:
                                print(f"Description: {error_data['error_description']}")
                        except Exception:
                            pass

                except httpx.TimeoutException:
                    print("\n[ERROR] Request timeout - StockX OAuth server not responding")
                except httpx.RequestError as e:
                    print(f"\n[ERROR] Network error: {e}")
                except Exception as e:
                    print(f"\n[ERROR] Unexpected error during token refresh: {e}")

    except Exception as e:
        print(f"\n[ERROR] Failed to refresh token: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await db_manager.close()
        print("\n" + "=" * 80)


async def test_stockx_api_call():
    """Test if we can make an API call with current credentials."""

    print("\n" + "=" * 80)
    print("Testing StockX API Call")
    print("=" * 80 + "\n")

    try:
        from domains.integration.services.stockx_service import StockXService

        await db_manager.initialize()

        async with db_manager.get_session() as session:
            stockx_service = StockXService(session)

            print("Attempting to fetch active orders from StockX...")

            try:
                orders = await stockx_service.get_active_orders()
                print(f"\n[SUCCESS] Successfully fetched {len(orders)} active orders!")

                if orders:
                    print("\nFirst order preview:")
                    first_order = orders[0]
                    for key, value in list(first_order.items())[:5]:
                        print(f"   {key}: {value}")
                else:
                    print("   No active orders found (this is normal if you have no pending sales)")

            except Exception as e:
                print(f"\n[ERROR] API call failed: {e}")
                print("\nThis likely means:")
                print("   1. Credentials are invalid or expired")
                print("   2. Refresh token needs to be updated in database")
                print("   3. StockX API permissions have changed")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await db_manager.close()
        print("\n" + "=" * 80)


async def main():
    """Main execution function."""

    print("\n>>> StockX Token Management")
    print("\nOptions:")
    print("1. Refresh access token (recommended)")
    print("2. Test API call with current credentials")
    print("3. Both (refresh then test)")

    # For automation, just run option 3
    choice = "3"

    if choice in ["1", "3"]:
        await refresh_stockx_token()

    if choice in ["2", "3"]:
        await test_stockx_api_call()


if __name__ == "__main__":
    asyncio.run(main())
