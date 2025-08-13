import httpx
import asyncio
import structlog
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select
from datetime import date, datetime, timedelta, timezone

from shared.database.connection import db_manager
from shared.database.models import SystemConfig

logger = structlog.get_logger(__name__)

STOCKX_API_BASE_URL = "https://api.stockx.com/v2"
STOCKX_AUTH_URL = "https://accounts.stockx.com/oauth/token"

class StockXCredentials:
    """A data class for holding all necessary StockX credentials."""
    def __init__(self, client_id: str, client_secret: str, refresh_token: str, api_key: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.api_key = api_key

from sqlalchemy.ext.asyncio import AsyncSession

class StockXService:
    """
    A service to interact with the StockX Public API, handling the OAuth2 refresh token flow.
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._credentials: Optional[StockXCredentials] = None
        self._lock = asyncio.Lock()

    async def _load_credentials(self) -> StockXCredentials:
        """
        Fetches StockX API credentials from the database. Caches them in memory.
        """
        if self._credentials:
            return self._credentials

        logger.info("Loading StockX credentials from database for current request.")
        keys = ["stockx_client_id", "stockx_client_secret", "stockx_refresh_token", "stockx_api_key"]
        results = await self.db_session.execute(
            select(SystemConfig).where(SystemConfig.key.in_(keys))
        )
        configs = {row.key: row.get_value() for row in results.scalars()}

        for key in keys:
            if key not in configs:
                raise ValueError(f"Missing required StockX credential in system_config: {key}")

        self._credentials = StockXCredentials(
            client_id=configs["stockx_client_id"],
            client_secret=configs["stockx_client_secret"],
            refresh_token=configs["stockx_refresh_token"],
            api_key=configs["stockx_api_key"]
        )
        return self._credentials

    async def _refresh_access_token(self) -> None:
        """
        Uses the refresh token to get a new access token from StockX Auth service.
        """
        creds = await self._load_credentials()
        logger.info("Attempting to refresh StockX access token.")

        payload = {
            "grant_type": "refresh_token",
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "refresh_token": creds.refresh_token,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(STOCKX_AUTH_URL, data=payload)
                response.raise_for_status()
                token_data = response.json()

                self._access_token = token_data["access_token"]
                # Set expiry with a 60-second buffer for safety
                expires_in = token_data.get("expires_in", 3600) - 60
                self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                logger.info("Successfully refreshed StockX access token.", expires_at=self._token_expiry)

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Failed to refresh StockX access token",
                    status_code=e.response.status_code,
                    response=e.response.text
                )
                # If refresh fails, credentials might be bad. Clear local cache.
                self._access_token = None
                self._token_expiry = None
                raise Exception("Could not refresh StockX access token. Please check your credentials.") from e

    async def _get_valid_access_token(self) -> str:
        """
        Ensures a valid, non-expired access token is available, refreshing if necessary.
        This method is thread-safe using an async lock.
        """
        async with self._lock:
            if self._access_token and self._token_expiry and self._token_expiry > datetime.now(timezone.utc):
                return self._access_token

            # If token is missing or expired, refresh it
            await self._refresh_access_token()
            if not self._access_token:
                 raise Exception("Failed to obtain a valid access token.")
            return self._access_token

    async def get_historical_orders(self, from_date: date, to_date: date) -> List[Dict[str, Any]]:
        """
        Fetches all historical orders within a given date range, handling authentication and pagination.
        """
        logger.info("Fetching historical orders from StockX API.", from_date=from_date, to_date=to_date)
        params = {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
        }
        return await self._make_paginated_get_request("/selling/orders/history", params)

    async def _make_paginated_get_request(self, endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        A generic helper to make paginated GET requests to the StockX API.
        """
        access_token = await self._get_valid_access_token()
        api_key = (await self._load_credentials()).api_key

        headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "SoleFlipperApp/1.0"
        }

        all_items = []
        page = 1

        async with httpx.AsyncClient(base_url=STOCKX_API_BASE_URL) as client:
            while True:
                # Add pagination params to the request
                request_params = params.copy()
                request_params["pageNumber"] = page
                request_params["pageSize"] = 100

                try:
                    response = await client.get(endpoint, params=request_params, headers=headers, timeout=30.0)

                    if response.status_code == 401:
                        logger.warning(f"Received 401 on {endpoint}. Retrying after token refresh.")
                        access_token = await self._get_valid_access_token() # Force refresh
                        headers["Authorization"] = f"Bearer {access_token}"
                        response = await client.get(endpoint, params=request_params, headers=headers, timeout=30.0)

                    response.raise_for_status()

                    data = response.json()
                    # The API uses the key "orders" for both active and historical orders
                    items = data.get("orders", [])
                    all_items.extend(items)

                    logger.info(f"Fetched page from {endpoint}", page=page, count=len(items))

                    if not data.get("hasNextPage") or not items:
                        break

                    page += 1
                    await asyncio.sleep(1)

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error on {endpoint}", status_code=e.response.status_code, response=e.response.text)
                    raise
                except httpx.RequestError as e:
                    logger.error(f"Request error on {endpoint}", error=str(e))
                    raise

        logger.info(f"Finished fetching all items from {endpoint}", total_items=len(all_items))
        return all_items

    async def get_active_orders(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches all active orders, handling authentication and pagination.
        Accepts any valid query parameters for the /selling/orders/active endpoint.
        """
        logger.info("Fetching active orders from StockX API.", filters=kwargs)

        # Filter out None values so they aren't sent as query params
        params = {key: value for key, value in kwargs.items() if value is not None}

        return await self._make_paginated_get_request("/selling/orders/active", params)
