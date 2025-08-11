import httpx
import asyncio
import structlog
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from datetime import date

from shared.database.connection import db_manager
from shared.database.models import SystemConfig

logger = structlog.get_logger(__name__)

STOCKX_API_BASE_URL = "https://api.stockx.com/v2"

class StockXCredentials:
    """A simple data class for holding StockX credentials."""
    def __init__(self, api_key: str, jwt_token: str):
        self.api_key = api_key
        self.jwt_token = jwt_token

class StockXService:
    """
    A service to interact with the StockX Public API.
    Handles credential management, API requests, pagination, and error handling.
    """

    async def _get_credentials(self) -> StockXCredentials:
        """
        Fetches StockX API credentials from the database.
        """
        logger.info("Fetching StockX credentials from database...")
        async with db_manager.get_session() as session:
            # Fetch API Key
            api_key_result = await session.execute(
                select(SystemConfig).where(SystemConfig.key == "stockx_api_key")
            )
            api_key_config = api_key_result.scalar_one_or_none()
            if not api_key_config:
                logger.error("StockX API key not found in system_config table.")
                raise ValueError("StockX API key ('stockx_api_key') is not configured in the database.")

            # Fetch JWT
            jwt_result = await session.execute(
                select(SystemConfig).where(SystemConfig.key == "stockx_jwt_token")
            )
            jwt_config = jwt_result.scalar_one_or_none()
            if not jwt_config:
                logger.error("StockX JWT token not found in system_config table.")
                raise ValueError("StockX JWT token ('stockx_jwt_token') is not configured in the database.")

            credentials = StockXCredentials(
                api_key=api_key_config.get_value(),
                jwt_token=jwt_config.get_value()
            )
            logger.info("Successfully fetched StockX credentials.")
            return credentials

    async def get_historical_orders(self, from_date: date, to_date: date) -> List[Dict[str, Any]]:
        """
        Fetches all historical orders within a given date range, handling pagination.
        """
        creds = await self._get_credentials()
        all_orders = []
        page = 1

        headers = {
            "x-api-key": creds.api_key,
            "Authorization": f"Bearer {creds.jwt_token}",
            "User-Agent": "SoleFlipperApp/1.0"
        }

        logger.info("Starting to fetch historical orders from StockX", from_date=from_date, to_date=to_date)

        async with httpx.AsyncClient(base_url=STOCKX_API_BASE_URL) as client:
            while True:
                params = {
                    "fromDate": from_date.isoformat(),
                    "toDate": to_date.isoformat(),
                    "pageNumber": page,
                    "pageSize": 100  # Max page size as per docs
                }

                try:
                    response = await client.get(
                        "/selling/orders/history",
                        params=params,
                        headers=headers,
                        timeout=30.0
                    )
                    response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

                    data = response.json()
                    orders = data.get("orders", [])
                    all_orders.extend(orders)

                    logger.info(
                        "Fetched StockX orders page",
                        page=page,
                        count=len(orders)
                    )

                    if not data.get("hasNextPage") or not orders:
                        break  # Exit loop if no more pages or no orders on current page

                    page += 1
                    await asyncio.sleep(1)  # Be a good API citizen, avoid hitting rate limits

                except httpx.HTTPStatusError as e:
                    logger.error(
                        "HTTP error fetching StockX orders",
                        status_code=e.response.status_code,
                        response_body=e.response.text,
                        page=page
                    )
                    # Re-raise the exception to be handled by the caller (e.g., the API endpoint)
                    raise
                except httpx.RequestError as e:
                    logger.error("Request error fetching StockX orders", error=str(e), page=page)
                    raise

        logger.info("Finished fetching all StockX orders", total_orders=len(all_orders), from_date=from_date, to_date=to_date)
        return all_orders

# Singleton instance for easy import and use in other parts of the application
stockx_service = StockXService()
