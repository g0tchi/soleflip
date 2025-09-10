import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import structlog
from sqlalchemy import select

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
        keys = [
            "stockx_client_id",
            "stockx_client_secret",
            "stockx_refresh_token",
            "stockx_api_key",
        ]
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
            api_key=configs["stockx_api_key"],
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

                logger.info(
                    "Successfully refreshed StockX access token.", expires_at=self._token_expiry
                )

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Failed to refresh StockX access token",
                    status_code=e.response.status_code,
                    response=e.response.text,
                )
                # If refresh fails, credentials might be bad. Clear local cache.
                self._access_token = None
                self._token_expiry = None
                raise Exception(
                    "Could not refresh StockX access token. Please check your credentials."
                ) from e

    async def _get_valid_access_token(self) -> str:
        """
        Ensures a valid, non-expired access token is available, refreshing if necessary.
        This method is thread-safe using an async lock.
        """
        async with self._lock:
            if (
                self._access_token
                and self._token_expiry
                and self._token_expiry > datetime.now(timezone.utc)
            ):
                return self._access_token

            # If token is missing or expired, refresh it
            await self._refresh_access_token()
            if not self._access_token:
                raise Exception("Failed to obtain a valid access token.")
            return self._access_token

    async def get_historical_orders(
        self,
        from_date: date,
        to_date: date,
        order_status: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        inventory_types: Optional[str] = None,
        initiated_shipment_display_ids: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches all historical orders within a given date range, handling authentication,
        pagination, and optional filters.
        """
        logger.info(
            "Fetching historical orders from StockX API.",
            from_date=from_date,
            to_date=to_date,
            filters={
                "orderStatus": order_status,
                "productId": product_id,
                "variantId": variant_id,
                "inventoryTypes": inventory_types,
                "initiatedShipmentDisplayIds": initiated_shipment_display_ids,
            },
        )

        params = {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "orderStatus": order_status,
            "productId": product_id,
            "variantId": variant_id,
            "inventoryTypes": inventory_types,
            "initiatedShipmentDisplayIds": initiated_shipment_display_ids,
        }

        # Filter out None values so they aren't sent as query params
        filtered_params = {key: value for key, value in params.items() if value is not None}

        return await self._make_paginated_get_request(
            "/selling/orders/history", filtered_params, "orders"
        )

    async def _make_paginated_get_request(
        self, endpoint: str, params: Dict[str, Any], data_key: str
    ) -> List[Dict[str, Any]]:
        """
        A generic helper to make paginated GET requests to the StockX API.
        """
        access_token = await self._get_valid_access_token()
        api_key = (await self._load_credentials()).api_key

        headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "SoleFlipperApp/1.0",
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
                    response = await client.get(
                        endpoint, params=request_params, headers=headers, timeout=30.0
                    )

                    if response.status_code == 401:
                        logger.warning(f"Received 401 on {endpoint}. Retrying after token refresh.")
                        access_token = await self._get_valid_access_token()  # Force refresh
                        headers["Authorization"] = f"Bearer {access_token}"
                        response = await client.get(
                            endpoint, params=request_params, headers=headers, timeout=30.0
                        )

                    response.raise_for_status()

                    data = response.json()
                    items = data.get(data_key, [])
                    all_items.extend(items)

                    logger.info(
                        f"Fetched page from {endpoint}",
                        page=page,
                        count=len(items),
                        data_key=data_key,
                    )

                    if not data.get("hasNextPage") or not items:
                        break

                    page += 1
                    await asyncio.sleep(0.1)

                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"HTTP error on {endpoint}",
                        status_code=e.response.status_code,
                        response=e.response.text,
                    )
                    raise
                except httpx.RequestError as e:
                    logger.error(f"Request error on {endpoint}", error=str(e))
                    raise
                except asyncio.TimeoutError:
                    logger.error(f"Request timeout on {endpoint}")
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

        return await self._make_paginated_get_request("/selling/orders/active", params, "orders")

    async def get_all_listings(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches all of the seller's listings, handling authentication and pagination.
        Accepts any valid query parameters for the /selling/listings endpoint.
        """
        logger.info("Fetching all listings from StockX API.", filters=kwargs)

        # Filter out None values so they aren't sent as query params
        params = {key: value for key, value in kwargs.items() if value is not None}

        return await self._make_paginated_get_request("/selling/listings", params, "listings")

    async def get_order_details(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Fetches details for a single order from the StockX API.
        """
        logger.info("Fetching order details from StockX API.", order_number=order_number)
        endpoint = f"/selling/orders/{order_number}"

        try:
            response_data = await self._make_get_request(endpoint)
            return response_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Order not found in StockX.", order_number=order_number)
                return None
            else:
                # Re-raise other HTTP errors
                raise

    async def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches details for a single product from the StockX Catalog API.
        """
        logger.info("Fetching product details from StockX Catalog API.", product_id=product_id)
        endpoint = f"/catalog/products/{product_id}"

        try:
            response_data = await self._make_get_request(endpoint)
            return response_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Product not found in StockX catalog.", product_id=product_id)
                return None
            else:
                # Re-raise other HTTP errors
                raise

    async def get_all_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Fetches all variants for a single product from the StockX Catalog API.
        """
        logger.info("Fetching all product variants from StockX Catalog API.", product_id=product_id)
        endpoint = f"/catalog/products/{product_id}/variants"

        try:
            # This endpoint returns a list directly, which matches the expected output type.
            response_data = await self._make_get_request(endpoint)
            return response_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "Product not found in StockX catalog when fetching variants.",
                    product_id=product_id,
                )
                return []  # Return empty list if the product itself is not found
            else:
                raise

    async def search_stockx_catalog(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Searches the StockX catalog using a freeform query.
        """
        logger.info("Searching StockX catalog.", query=query, page=page, page_size=page_size)
        endpoint = "/catalog/search"
        params = {"query": query, "pageNumber": page, "pageSize": page_size}

        try:
            response_data = await self._make_get_request(endpoint, params=params)
            return response_data
        except httpx.HTTPStatusError:
            # A 404 is not expected for a search, but we'll log it.
            # Other errors will be re-raised by the helper.
            raise

    async def create_listing(
        self,
        variant_id: str,
        amount: str,
        currency_code: str = "USD",
        expires_at: Optional[str] = None,
        active: bool = True,
        inventory_type: str = "STANDARD"
    ) -> Dict[str, Any]:
        """
        Creates a new listing (ask) on StockX for the specified variant.
        
        Args:
            variant_id: StockX variant ID to create listing for
            amount: Price amount as string
            currency_code: Currency code (default: USD)
            expires_at: UTC timestamp when listing expires (ISO 8601 format)
            active: Whether listing should be active (default: True)
            inventory_type: STANDARD or DIRECT (default: STANDARD)
        
        Returns:
            Dict containing listing creation response
        """
        logger.info(
            "Creating StockX listing", 
            variant_id=variant_id, 
            amount=amount, 
            currency_code=currency_code,
            inventory_type=inventory_type
        )
        
        endpoint = "/selling/listings"
        payload = {
            "variantId": variant_id,
            "amount": amount,
            "currencyCode": currency_code,
            "active": active,
            "inventoryType": inventory_type
        }
        
        if expires_at:
            payload["expiresAt"] = expires_at
        
        try:
            response_data = await self._make_post_request(endpoint, json=payload)
            logger.info("StockX listing created successfully", listing_id=response_data.get("listingId"))
            return response_data
        except httpx.HTTPStatusError as e:
            logger.error("Failed to create StockX listing", 
                        status_code=e.response.status_code, 
                        response=e.response.text)
            raise
            logger.warning(
                "Received an unexpected HTTP status error during StockX catalog search.",
                status_code=e.response.status_code,
                query=query,
            )
            return None

    async def get_market_data_from_stockx(
        self, product_id: str, currency_code: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches market data (highest bid, lowest ask) for all variants of a given product.
        """
        logger.info(
            "Fetching market data from StockX.", product_id=product_id, currency=currency_code
        )
        endpoint = f"/catalog/products/{product_id}/market-data"
        params = {}
        if currency_code:
            params["currencyCode"] = currency_code

        try:
            # The API returns a list of variants with market data
            response_data = await self._make_get_request(endpoint, params=params)
            return response_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "Product not found on StockX when fetching market data.", product_id=product_id
                )
                return None
            else:
                logger.error(
                    "Received an unexpected HTTP status error during StockX market data fetch.",
                    status_code=e.response.status_code,
                    product_id=product_id,
                )
                raise

    async def _make_get_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        A generic helper to make a single, non-paginated GET request to the StockX API.
        """
        access_token = await self._get_valid_access_token()
        api_key = (await self._load_credentials()).api_key

        headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "SoleFlipperApp/1.0",
        }

        async with httpx.AsyncClient(base_url=STOCKX_API_BASE_URL) as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers, timeout=30.0)

                if response.status_code == 401:
                    logger.warning(f"Received 401 on {endpoint}. Retrying after token refresh.")
                    access_token = await self._get_valid_access_token()  # Force refresh
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = await client.get(
                        endpoint, params=params, headers=headers, timeout=30.0
                    )

                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error on {endpoint}",
                    status_code=e.response.status_code,
                    response=e.response.text,
                )
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error on {endpoint}", error=str(e))
                raise
            except asyncio.TimeoutError:
                logger.error(f"Request timeout on {endpoint}")
                raise

    async def _make_post_request(
        self, endpoint: str, json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        A generic helper to make a POST request to the StockX API.
        """
        access_token = await self._get_valid_access_token()
        api_key = (await self._load_credentials()).api_key

        headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "SoleFlipperApp/1.0",
        }

        async with httpx.AsyncClient(base_url=STOCKX_API_BASE_URL) as client:
            try:
                response = await client.post(endpoint, json=json, headers=headers, timeout=30.0)

                if response.status_code == 401:
                    logger.warning(f"Received 401 on {endpoint}. Retrying after token refresh.")
                    access_token = await self._get_valid_access_token()  # Force refresh
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = await client.post(
                        endpoint, json=json, headers=headers, timeout=30.0
                    )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error during POST request to {endpoint}",
                    status_code=e.response.status_code,
                    response_body=e.response.text,
                )
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error during POST to {endpoint}: {e}")
                raise

    async def get_shipping_document(self, order_number: str, shipping_id: str) -> Optional[bytes]:
        """
        Fetches a shipping document (PDF) for a given order and shipping ID.
        """
        logger.info(
            "Fetching shipping document from StockX API.",
            order_number=order_number,
            shipping_id=shipping_id,
        )
        endpoint = f"/selling/orders/{order_number}/shipping-document/{shipping_id}"

        try:
            response_bytes = await self._make_get_request_for_binary(endpoint)
            return response_bytes
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "Shipping document not found in StockX.",
                    order_number=order_number,
                    shipping_id=shipping_id,
                )
                return None
            else:
                # Re-raise other HTTP errors
                raise

    async def _make_get_request_for_binary(self, endpoint: str) -> bytes:
        """
        A generic helper to make a single GET request for binary content (e.g., PDF).
        """
        access_token = await self._get_valid_access_token()
        api_key = (await self._load_credentials()).api_key

        headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "SoleFlipperApp/1.0",
        }

        async with httpx.AsyncClient(base_url=STOCKX_API_BASE_URL) as client:
            try:
                response = await client.get(endpoint, headers=headers, timeout=30.0)

                if response.status_code == 401:
                    logger.warning(f"Received 401 on {endpoint}. Retrying after token refresh.")
                    access_token = await self._get_valid_access_token()  # Force refresh
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = await client.get(endpoint, headers=headers, timeout=30.0)

                response.raise_for_status()
                # Instead of .json(), we return the raw bytes
                return response.content

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error on {endpoint}",
                    status_code=e.response.status_code,
                    response=e.response.text,
                )
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error on {endpoint}", error=str(e))
                raise
            except asyncio.TimeoutError:
                logger.error(f"Request timeout on {endpoint}")
                raise
