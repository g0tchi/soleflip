"""
StockX Catalog Service for Product Enrichment

Provides methods to search and enrich products from StockX catalog API.
Fetches detailed product information, market data, and variant details.
"""

import asyncio
from typing import Dict, List, Optional, Any
from decimal import Decimal
from uuid import UUID

import structlog
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from domains.integration.services.stockx_service import StockXService

logger = structlog.get_logger(__name__)


class StockXCatalogService:
    """Service for interacting with StockX Catalog API"""

    def __init__(self, stockx_service: StockXService):
        self.stockx_service = stockx_service
        self.base_url = "https://api.stockx.com/v2"

    async def search_catalog(
        self,
        query: str,
        page_number: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Search StockX catalog by SKU, GTIN, styleId, or freeform text

        Args:
            query: Search term (SKU, GTIN, styleId, or product name)
            page_number: Page number (starts at 1)
            page_size: Number of results per page (1-50)

        Returns:
            Dict containing:
            - count: Total number of results
            - pageSize: Results in current page
            - pageNumber: Current page number
            - hasNextPage: Whether more pages exist
            - products: List of product objects
        """
        endpoint = f"{self.base_url}/catalog/search"
        params = {
            "query": query,
            "pageNumber": page_number,
            "pageSize": min(page_size, 50)  # Max 50
        }

        try:
            response = await self.stockx_service._make_get_request(endpoint, params=params)
            logger.info(
                f"Catalog search successful",
                query=query,
                results_count=response.get('count', 0)
            )
            return response
        except Exception as e:
            logger.error(f"Catalog search failed", query=query, error=str(e))
            raise

    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """
        Get detailed product information

        Args:
            product_id: StockX product ID

        Returns:
            Dict containing:
            - productId, urlKey, styleId, productType
            - title, brand
            - productAttributes (object)
            - sizeChart (object)
            - isFlexEligible, isDirectEligible
        """
        endpoint = f"{self.base_url}/catalog/products/{product_id}"

        try:
            response = await self.stockx_service._make_get_request(endpoint)
            logger.info(f"Product details retrieved", product_id=product_id)
            return response
        except Exception as e:
            logger.error(f"Failed to get product details", product_id=product_id, error=str(e))
            raise

    async def get_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Get all variants (sizes) for a product

        Args:
            product_id: StockX product ID

        Returns:
            List of variant objects containing:
            - productId, variantId
            - variantName, variantValue (e.g., "Size", "38")
            - sizeChart, gtins
            - isFlexEligible, isDirectEligible
        """
        endpoint = f"{self.base_url}/catalog/products/{product_id}/variants"

        try:
            response = await self.stockx_service._make_get_request(endpoint)
            logger.info(
                f"Product variants retrieved",
                product_id=product_id,
                variant_count=len(response)
            )
            return response
        except Exception as e:
            logger.error(
                f"Failed to get product variants",
                product_id=product_id,
                error=str(e)
            )
            raise

    async def get_market_data(
        self,
        product_id: str,
        variant_id: str,
        currency_code: str = "EUR"
    ) -> Dict[str, Any]:
        """
        Get market data for a specific variant (size)

        Args:
            product_id: StockX product ID
            variant_id: StockX variant ID
            currency_code: Currency (EUR, USD, GBP, etc.)

        Returns:
            Dict containing:
            - lowestAskAmount: Current lowest ask
            - highestBidAmount: Current highest bid
            - sellFasterAmount: Recommended price for faster sale
            - earnMoreAmount: Recommended price for maximum earnings
            - flexLowestAskAmount
            - standardMarketData (object)
            - flexMarketData (object)
            - directMarketData (object)
        """
        endpoint = f"{self.base_url}/catalog/products/{product_id}/variants/{variant_id}/market-data"
        params = {"currencyCode": currency_code}

        try:
            response = await self.stockx_service._make_get_request(endpoint, params=params)
            logger.info(
                f"Market data retrieved",
                product_id=product_id,
                variant_id=variant_id,
                lowest_ask=response.get('lowestAskAmount'),
                highest_bid=response.get('highestBidAmount')
            )
            return response
        except Exception as e:
            logger.error(
                f"Failed to get market data",
                product_id=product_id,
                variant_id=variant_id,
                error=str(e)
            )
            raise

    async def enrich_product_by_sku(
        self,
        sku: str,
        size: Optional[str] = None,
        db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Complete product enrichment workflow by SKU

        1. Search catalog by SKU
        2. Get product details
        3. Get all variants
        4. Get market data for specific size (if provided)
        5. Update database (if session provided)

        Args:
            sku: Product SKU to search for
            size: Optional size to get market data for
            db_session: Optional database session to update product

        Returns:
            Dict containing enriched product data
        """
        try:
            # Step 1: Search catalog
            search_results = await self.search_catalog(query=sku, page_size=1)

            if not search_results.get('products'):
                logger.warning(f"No products found for SKU", sku=sku)
                return {"error": "Product not found", "sku": sku}

            product_summary = search_results['products'][0]
            product_id = product_summary['productId']

            # Step 2: Get detailed product info
            product_details = await self.get_product_details(product_id)

            # Step 3: Get all variants
            variants = await self.get_product_variants(product_id)

            # Step 4: Get market data for specific size
            market_data = None
            if size and variants:
                # Find matching variant
                matching_variant = next(
                    (v for v in variants if v.get('variantValue') == size),
                    None
                )

                if matching_variant:
                    variant_id = matching_variant['variantId']
                    market_data = await self.get_market_data(
                        product_id=product_id,
                        variant_id=variant_id,
                        currency_code="EUR"
                    )

            # Compile enriched data
            enriched_data = {
                "sku": sku,
                "stockx_product_id": product_id,
                "product_details": product_details,
                "variants": variants,
                "market_data": market_data,
                "enrichment_timestamp": "now()"
            }

            # Step 5: Update database if session provided
            if db_session:
                await self._update_product_in_db(
                    sku=sku,
                    enriched_data=enriched_data,
                    session=db_session
                )

            logger.info(
                f"Product enrichment completed",
                sku=sku,
                product_id=product_id,
                variant_count=len(variants),
                has_market_data=market_data is not None
            )

            return enriched_data

        except Exception as e:
            logger.error(f"Product enrichment failed", sku=sku, error=str(e))
            raise

    async def _update_product_in_db(
        self,
        sku: str,
        enriched_data: Dict[str, Any],
        session: AsyncSession
    ):
        """Update product in database with enriched data"""
        import json

        product_details = enriched_data.get('product_details', {})
        market_data = enriched_data.get('market_data', {})

        # Extract key fields
        stockx_product_id = enriched_data.get('stockx_product_id')
        brand = product_details.get('brand')
        title = product_details.get('title')
        style_id = product_details.get('styleId')
        product_attributes = product_details.get('productAttributes', {})

        # Market data fields
        lowest_ask = market_data.get('lowestAskAmount') if market_data else None
        highest_bid = market_data.get('highestBidAmount') if market_data else None
        sell_faster_amount = market_data.get('sellFasterAmount') if market_data else None
        earn_more_amount = market_data.get('earnMoreAmount') if market_data else None

        try:
            # Update product table (using CAST instead of :: for parameter safety)
            query = text("""
                UPDATE products.products
                SET
                    stockx_product_id = :stockx_product_id,
                    style_code = :style_code,
                    enrichment_data = CAST(:enrichment_data AS jsonb),
                    lowest_ask = :lowest_ask,
                    highest_bid = :highest_bid,
                    recommended_sell_faster = :sell_faster,
                    recommended_earn_more = :earn_more,
                    last_enriched_at = NOW(),
                    updated_at = NOW()
                WHERE sku = :sku
            """)

            await session.execute(query, {
                "sku": sku,
                "stockx_product_id": stockx_product_id,
                "style_code": style_id,
                "enrichment_data": json.dumps(enriched_data),  # Convert to JSON string
                "lowest_ask": Decimal(lowest_ask) if lowest_ask else None,
                "highest_bid": Decimal(highest_bid) if highest_bid else None,
                "sell_faster": Decimal(sell_faster_amount) if sell_faster_amount else None,
                "earn_more": Decimal(earn_more_amount) if earn_more_amount else None
            })

            await session.commit()

            logger.info(
                f"Product updated in database",
                sku=sku,
                stockx_product_id=stockx_product_id
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update product in database", sku=sku, error=str(e))
            raise
