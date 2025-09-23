"""
StockX API Client
Low-level client for StockX API operations
"""

import asyncio
from typing import Dict, List, Optional, Any

import structlog
import aiohttp

logger = structlog.get_logger(__name__)


class StockXAPIClient:
    """StockX API client for selling operations"""

    def __init__(self, api_token: str, base_url: str = "https://gateway.stockx.com/api"):
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def create_listing(self, product_id: str, variant_id: str, amount: float, expires_at: str = None) -> Dict[str, Any]:
        """Create a new listing on StockX"""
        url = f"{self.base_url}/selling/listings"
        payload = {
            "productId": product_id,
            "variantId": variant_id,
            "amount": amount
        }
        if expires_at:
            payload["expiresAt"] = expires_at

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error("Failed to create listing", status=response.status, error=error_text)
                    raise Exception(f"StockX API error: {error_text}")

    async def create_bulk_listings(self, listings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple listings at once"""
        url = f"{self.base_url}/selling/batch/create-listing"
        payload = {"listings": listings}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error("Failed to create bulk listings", status=response.status, error=error_text)
                    raise Exception(f"StockX API error: {error_text}")

    async def update_listing_price(self, listing_id: str, amount: float) -> Dict[str, Any]:
        """Update the price of an existing listing"""
        url = f"{self.base_url}/selling/listings/{listing_id}"
        payload = {"amount": amount}

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error("Failed to update listing", listing_id=listing_id, status=response.status, error=error_text)
                    raise Exception(f"StockX API error: {error_text}")

    async def activate_listing(self, listing_id: str) -> bool:
        """Activate a listing"""
        url = f"{self.base_url}/selling/listings/{listing_id}/activate"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers) as response:
                return response.status == 200

    async def deactivate_listing(self, listing_id: str) -> bool:
        """Deactivate a listing"""
        url = f"{self.base_url}/selling/listings/{listing_id}/deactivate"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers) as response:
                return response.status == 200

    async def get_all_listings(self, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all my listings"""
        url = f"{self.base_url}/selling/listings"
        params = {"limit": limit}
        if status:
            params["status"] = status

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("listings", [])
                else:
                    logger.error("Failed to get listings", status=response.status)
                    return []

    async def get_active_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get active sales orders"""
        url = f"{self.base_url}/selling/orders/active"
        params = {"limit": limit}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("orders", [])
                else:
                    logger.error("Failed to get active orders", status=response.status)
                    return []

    async def get_order_history(self, start_date: str = None, end_date: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get sales history"""
        url = f"{self.base_url}/selling/orders/history"
        params = {"limit": limit}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("orders", [])
                else:
                    logger.error("Failed to get order history", status=response.status)
                    return []

    async def get_product_market_data(self, product_id: str, variant_id: str = None) -> Dict[str, Any]:
        """Get current market data for pricing decisions"""
        if variant_id:
            url = f"{self.base_url}/catalog/products/{product_id}/variants/{variant_id}/market-data"
        else:
            url = f"{self.base_url}/catalog/products/{product_id}/market-data"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error("Failed to get market data", product_id=product_id, status=response.status)
                    return {}

    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generic GET request for API endpoints"""
        url = f"{self.base_url}{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error("API GET request failed", endpoint=endpoint, status=response.status, error=error_text)
                    raise Exception(f"StockX API error: {error_text}")