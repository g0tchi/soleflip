"""
StockX Catalog Service for Product Enrichment

Provides methods to search and enrich products from StockX catalog API.
Fetches detailed product information, market data, and variant details.
"""

import asyncio
from typing import Dict, List, Optional, Any
from decimal import Decimal
from uuid import UUID
from datetime import datetime

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
        """Create or update product in database with enriched data"""
        import json

        product_details = enriched_data.get('product_details', {})
        market_data = enriched_data.get('market_data', {})

        # Extract key fields
        stockx_product_id = enriched_data.get('stockx_product_id')
        brand_name = product_details.get('brand')
        title = product_details.get('title')
        style_id = product_details.get('styleId')
        product_type = product_details.get('productType', 'sneakers')
        retail_price = product_details.get('productAttributes', {}).get('retailPrice')

        # Parse release date string to datetime
        release_date_str = product_details.get('productAttributes', {}).get('releaseDate')
        release_date = None
        if release_date_str:
            try:
                release_date = datetime.strptime(release_date_str, '%Y-%m-%d')
            except (ValueError, TypeError):
                logger.warning(f"Invalid release date format", date=release_date_str)
                release_date = None

        # Market data fields
        lowest_ask = market_data.get('lowestAskAmount') if market_data else None
        highest_bid = market_data.get('highestBidAmount') if market_data else None
        sell_faster_amount = market_data.get('sellFasterAmount') if market_data else None
        earn_more_amount = market_data.get('earnMoreAmount') if market_data else None

        try:
            # Generate slug from brand name
            brand_slug = brand_name.lower().replace(' ', '-').replace('&', 'and')

            # Get or create brand
            brand_query = text("""
                INSERT INTO catalog.brand (id, name, slug, created_at, updated_at)
                VALUES (gen_random_uuid(), :brand_name, :brand_slug, NOW(), NOW())
                ON CONFLICT (name) DO UPDATE SET updated_at = NOW()
                RETURNING id
            """)
            brand_result = await session.execute(brand_query, {
                "brand_name": brand_name,
                "brand_slug": brand_slug
            })
            brand_id = brand_result.scalar_one()

            # Get or create category (using product type)
            category_slug = product_type.lower().replace(' ', '-').replace('&', 'and')

            category_query = text("""
                INSERT INTO catalog.category (id, name, slug, created_at, updated_at)
                VALUES (gen_random_uuid(), :category_name, :category_slug, NOW(), NOW())
                ON CONFLICT (slug) DO UPDATE SET updated_at = NOW()
                RETURNING id
            """)
            category_result = await session.execute(category_query, {
                "category_name": product_type,
                "category_slug": category_slug
            })
            category_id = category_result.scalar_one()

            # UPSERT product (create if not exists, update if exists)
            query = text("""
                INSERT INTO catalog.product (
                    id, sku, brand_id, category_id, name, retail_price, release_date,
                    stockx_product_id, style_code, enrichment_data,
                    lowest_ask, highest_bid, recommended_sell_faster, recommended_earn_more,
                    last_enriched_at, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :sku, :brand_id, :category_id, :name, :retail_price, :release_date,
                    :stockx_product_id, :style_code, CAST(:enrichment_data AS jsonb),
                    :lowest_ask, :highest_bid, :sell_faster, :earn_more,
                    NOW(), NOW(), NOW()
                )
                ON CONFLICT (sku) DO UPDATE SET
                    brand_id = EXCLUDED.brand_id,
                    category_id = EXCLUDED.category_id,
                    name = EXCLUDED.name,
                    retail_price = EXCLUDED.retail_price,
                    release_date = EXCLUDED.release_date,
                    stockx_product_id = EXCLUDED.stockx_product_id,
                    style_code = EXCLUDED.style_code,
                    enrichment_data = EXCLUDED.enrichment_data,
                    lowest_ask = EXCLUDED.lowest_ask,
                    highest_bid = EXCLUDED.highest_bid,
                    recommended_sell_faster = EXCLUDED.recommended_sell_faster,
                    recommended_earn_more = EXCLUDED.recommended_earn_more,
                    last_enriched_at = NOW(),
                    updated_at = NOW()
            """)

            await session.execute(query, {
                "sku": sku,
                "brand_id": brand_id,
                "category_id": category_id,
                "name": title,
                "retail_price": Decimal(retail_price) if retail_price else None,
                "release_date": release_date,
                "stockx_product_id": stockx_product_id,
                "style_code": style_id,
                "enrichment_data": json.dumps(enriched_data),
                "lowest_ask": Decimal(lowest_ask) if lowest_ask else None,
                "highest_bid": Decimal(highest_bid) if highest_bid else None,
                "sell_faster": Decimal(sell_faster_amount) if sell_faster_amount else None,
                "earn_more": Decimal(earn_more_amount) if earn_more_amount else None
            })

            await session.commit()

            logger.info(
                f"Product created/updated in database",
                sku=sku,
                stockx_product_id=stockx_product_id,
                brand=brand_name,
                title=title
            )

            # Step 6: Create product variants with size validation
            product_query = text("SELECT id, category_id FROM catalog.product WHERE sku = :sku")
            product_result = await session.execute(product_query, {"sku": sku})
            product_row = product_result.first()

            if product_row and enriched_data.get('variants'):
                await self._create_variants_from_stockx(
                    product_id=product_row.id,
                    category_id=product_row.category_id,
                    stockx_product_id=stockx_product_id,
                    variants_data=enriched_data['variants'],
                    session=session
                )

            await session.commit()

            logger.info(
                f"Product created/updated in database",
                sku=sku,
                stockx_product_id=stockx_product_id,
                brand=brand_name,
                title=title
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create/update product in database", sku=sku, error=str(e))
            raise

    def _parse_size_value(self, size_str: str) -> Optional[float]:
        """Extract numeric size value from size string (e.g., 'US W 9' -> 9.0, 'EU 41 1/3' -> 41.33)"""
        import re

        if not size_str:
            return None

        # Remove common prefixes
        size_str = size_str.replace('US W', '').replace('US M', '').replace('UK', '').replace('EU', '').replace('CM', '').replace('KR', '').strip()

        # Handle fractions (e.g., "41 1/3" -> 41.33)
        if '/' in size_str:
            parts = size_str.split()
            if len(parts) >= 2:
                whole = float(parts[0])
                fraction_match = re.search(r'(\d+)/(\d+)', size_str)
                if fraction_match:
                    numerator = float(fraction_match.group(1))
                    denominator = float(fraction_match.group(2))
                    return round(whole + (numerator / denominator), 2)

        # Extract first number
        number_match = re.search(r'\d+\.?\d*', size_str)
        if number_match:
            return float(number_match.group())

        return None

    async def _get_or_create_size_master(
        self,
        us_size: float,
        eu_size: Optional[float],
        uk_size: Optional[float],
        cm_size: Optional[float],
        kr_size: Optional[float],
        gender: str,
        category_id: UUID,
        stockx_product_id: str,
        stockx_variant_id: str,
        session: AsyncSession
    ) -> UUID:
        """
        Get or create size_master entry with StockX validation.
        StockX is always the source of truth - updates existing entries if conflicts found.
        """

        # Check for existing entry
        existing_query = text("""
            SELECT id, us_size, eu_size, uk_size, cm_size, kr_size, gender
            FROM core.size_master
            WHERE us_size = :us_size
              AND gender = :gender
              AND (category_id = :category_id OR category_id IS NULL)
            LIMIT 1
        """)

        result = await session.execute(existing_query, {
            'us_size': us_size,
            'gender': gender,
            'category_id': category_id
        })
        existing = result.first()

        stockx_data = {
            'us_size': us_size,
            'eu_size': eu_size,
            'uk_size': uk_size,
            'cm_size': cm_size,
            'kr_size': kr_size,
            'gender': gender
        }

        if not existing:
            # CREATE new size_master from StockX data
            insert_query = text("""
                INSERT INTO core.size_master (
                    id, gender, us_size, eu_size, uk_size, cm_size, kr_size,
                    category_id, validation_source, last_validated_at,
                    created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :gender, :us_size, :eu_size, :uk_size,
                    :cm_size, :kr_size, :category_id, 'stockx', NOW(),
                    NOW(), NOW()
                )
                RETURNING id
            """)

            result = await session.execute(insert_query, {
                **stockx_data,
                'category_id': category_id
            })
            size_master_id = result.scalar_one()

            # Log creation
            await self._log_size_validation(
                session=session,
                size_master_id=size_master_id,
                validation_status='created',
                stockx_product_id=stockx_product_id,
                stockx_variant_id=stockx_variant_id,
                conflicts_found=[],
                action_taken='created',
                before_data=None,
                after_data=stockx_data
            )

            logger.info(
                "Size master created from StockX data",
                size_master_id=str(size_master_id),
                us_size=us_size,
                gender=gender
            )

            return size_master_id

        else:
            # VALIDATE existing entry against StockX data
            size_master_id = existing.id
            conflicts = []
            needs_update = False

            # Check each field
            for field in ['eu_size', 'uk_size', 'cm_size', 'kr_size']:
                db_value = getattr(existing, field)
                stockx_value = stockx_data.get(field)

                if stockx_value is None:
                    continue  # StockX doesn't have this field

                if db_value is None:
                    # DB missing this field, add it
                    conflicts.append({
                        'field': field,
                        'type': 'missing_in_db',
                        'db_value': None,
                        'stockx_value': stockx_value,
                        'severity': 'low'
                    })
                    needs_update = True

                elif abs(float(db_value) - float(stockx_value)) > 0.5:
                    # Significant mismatch
                    diff = abs(float(db_value) - float(stockx_value))
                    conflicts.append({
                        'field': field,
                        'type': 'mismatch',
                        'db_value': float(db_value),
                        'stockx_value': float(stockx_value),
                        'difference': diff,
                        'severity': 'high' if diff > 1.0 else 'medium'
                    })
                    needs_update = True

            if needs_update:
                # UPDATE with StockX data (source of truth)
                before_data = {
                    'us_size': existing.us_size,
                    'eu_size': existing.eu_size,
                    'uk_size': existing.uk_size,
                    'cm_size': existing.cm_size,
                    'kr_size': existing.kr_size
                }

                update_query = text("""
                    UPDATE core.size_master
                    SET
                        eu_size = COALESCE(:eu_size, eu_size),
                        uk_size = COALESCE(:uk_size, uk_size),
                        cm_size = COALESCE(:cm_size, cm_size),
                        kr_size = COALESCE(:kr_size, kr_size),
                        validation_source = 'stockx',
                        last_validated_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :size_master_id
                """)

                await session.execute(update_query, {
                    'size_master_id': size_master_id,
                    **stockx_data
                })

                # Log validation with conflicts
                await self._log_size_validation(
                    session=session,
                    size_master_id=size_master_id,
                    validation_status='updated',
                    stockx_product_id=stockx_product_id,
                    stockx_variant_id=stockx_variant_id,
                    conflicts_found=conflicts,
                    action_taken='updated',
                    before_data=before_data,
                    after_data=stockx_data
                )

                logger.warning(
                    "Size master updated with StockX data (conflicts resolved)",
                    size_master_id=str(size_master_id),
                    us_size=us_size,
                    gender=gender,
                    conflicts_count=len(conflicts),
                    conflicts=conflicts
                )

            else:
                # No conflicts, just update validation timestamp
                await session.execute(text("""
                    UPDATE core.size_master
                    SET last_validated_at = NOW()
                    WHERE id = :size_master_id
                """), {'size_master_id': size_master_id})

                # Log successful validation
                await self._log_size_validation(
                    session=session,
                    size_master_id=size_master_id,
                    validation_status='valid',
                    stockx_product_id=stockx_product_id,
                    stockx_variant_id=stockx_variant_id,
                    conflicts_found=[],
                    action_taken='no_change',
                    before_data=stockx_data,
                    after_data=stockx_data
                )

                logger.debug(
                    "Size master validated (no conflicts)",
                    size_master_id=str(size_master_id),
                    us_size=us_size,
                    gender=gender
                )

            return size_master_id

    async def _create_variants_from_stockx(
        self,
        product_id: UUID,
        category_id: UUID,
        stockx_product_id: str,
        variants_data: List[Dict],
        session: AsyncSession
    ):
        """Create product variants from StockX data and populate size_master"""
        import json

        for variant in variants_data:
            size_chart = variant.get('sizeChart', {})
            conversions = size_chart.get('availableConversions', [])

            # Extract all size standards
            us_size = None
            eu_size = None
            uk_size = None
            cm_size = None
            kr_size = None
            gender = None

            for conv in conversions:
                size_type = conv.get('type', '').lower()
                size_value = self._parse_size_value(conv.get('size', ''))

                if size_value is None:
                    continue

                if 'us w' in size_type:
                    us_size = size_value
                    gender = 'women'
                elif 'us m' in size_type:
                    if not us_size:  # Prefer primary gender
                        us_size = size_value
                        gender = 'men'
                elif size_type == 'eu':
                    eu_size = size_value
                elif size_type == 'uk':
                    uk_size = size_value
                elif size_type == 'cm':
                    cm_size = size_value
                elif size_type == 'kr':
                    kr_size = size_value

            if us_size is None or gender is None:
                logger.warning(
                    "Skipping variant - no US size or gender detected",
                    variant_id=variant.get('variantId'),
                    variant_value=variant.get('variantValue')
                )
                continue

            # Get or create size_master entry with validation
            size_master_id = await self._get_or_create_size_master(
                us_size=us_size,
                eu_size=eu_size,
                uk_size=uk_size,
                cm_size=cm_size,
                kr_size=kr_size,
                gender=gender,
                category_id=category_id,
                stockx_product_id=stockx_product_id,
                stockx_variant_id=variant.get('variantId'),
                session=session
            )

            # Create product variant
            variant_query = text("""
                INSERT INTO catalog.product_variant (
                    id, product_id, size_master_id,
                    stockx_variant_id, stockx_variant_name,
                    variant_data, is_flex_eligible, is_direct_eligible,
                    created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :product_id, :size_master_id,
                    :stockx_variant_id, :stockx_variant_name,
                    CAST(:variant_data AS jsonb), :is_flex, :is_direct,
                    NOW(), NOW()
                )
                ON CONFLICT (stockx_variant_id) DO UPDATE SET
                    size_master_id = EXCLUDED.size_master_id,
                    variant_data = EXCLUDED.variant_data,
                    is_flex_eligible = EXCLUDED.is_flex_eligible,
                    is_direct_eligible = EXCLUDED.is_direct_eligible,
                    updated_at = NOW()
            """)

            await session.execute(variant_query, {
                "product_id": product_id,
                "size_master_id": size_master_id,
                "stockx_variant_id": variant.get('variantId'),
                "stockx_variant_name": variant.get('variantName'),
                "variant_data": json.dumps(variant),
                "is_flex": variant.get('isFlexEligible', False),
                "is_direct": variant.get('isDirectEligible', False)
            })

        logger.info(
            "Product variants created/updated",
            product_id=str(product_id),
            variant_count=len(variants_data)
        )

    async def _log_size_validation(
        self,
        session: AsyncSession,
        size_master_id: UUID,
        validation_status: str,
        stockx_product_id: str,
        stockx_variant_id: str,
        conflicts_found: List[Dict],
        action_taken: str,
        before_data: Optional[Dict],
        after_data: Dict
    ):
        """Log size validation to audit table"""
        import json
        from decimal import Decimal

        def convert_decimals(obj):
            """Convert Decimal objects to float for JSON serialization"""
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj

        log_query = text("""
            INSERT INTO core.size_validation_log (
                id, size_master_id, validation_source, validation_status,
                stockx_product_id, stockx_variant_id,
                conflicts_found, action_taken,
                before_data, after_data,
                validated_at
            )
            VALUES (
                gen_random_uuid(), :size_master_id, 'stockx', :validation_status,
                :stockx_product_id, :stockx_variant_id,
                CAST(:conflicts_found AS jsonb), :action_taken,
                CAST(:before_data AS jsonb), CAST(:after_data AS jsonb),
                NOW()
            )
        """)

        await session.execute(log_query, {
            'size_master_id': size_master_id,
            'validation_status': validation_status,
            'stockx_product_id': stockx_product_id,
            'stockx_variant_id': stockx_variant_id,
            'conflicts_found': json.dumps(convert_decimals(conflicts_found)),
            'action_taken': action_taken,
            'before_data': json.dumps(convert_decimals(before_data)) if before_data else None,
            'after_data': json.dumps(convert_decimals(after_data))
        })
