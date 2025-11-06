"""
Test Product Enrichment from StockX Catalog

Tests the StockX Catalog enrichment functionality by:
1. Searching for a product by SKU
2. Fetching product details
3. Fetching all variants
4. Fetching market data for a specific size
5. Updating the database with enriched data
"""

import asyncio
import os
import structlog
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from domains.integration.services.stockx_service import StockXService
from domains.integration.services.stockx_catalog_service import StockXCatalogService

load_dotenv()

logger = structlog.get_logger(__name__)


async def test_enrichment():
    """Test product enrichment with a known SKU"""

    # Test with adidas Campus 00s (from allike invoice)
    test_sku = "JH9768"
    test_size = "38"

    logger.info(f"Testing product enrichment for SKU: {test_sku}, Size: {test_size}")

    # Create database session first
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    engine = create_async_engine(database_url)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        # Initialize services with DB session
        stockx_service = StockXService(db_session=session)
        catalog_service = StockXCatalogService(stockx_service=stockx_service)
        try:
            # Step 1: Search catalog
            logger.info(f"Step 1: Searching StockX catalog for SKU: {test_sku}")
            search_results = await catalog_service.search_catalog(query=test_sku, page_size=3)

            print("\n=== SEARCH RESULTS ===")
            print(f"Total results: {search_results.get('count', 0)}")
            print(f"Products found: {len(search_results.get('products', []))}")

            if not search_results.get("products"):
                print(f"\n[ERROR] No products found for SKU: {test_sku}")
                return

            # Show all found products
            for idx, product in enumerate(search_results.get("products", [])):
                print(f"\nProduct {idx + 1}:")
                print(f"  - Product ID: {product.get('productId')}")
                print(f"  - Title: {product.get('title')}")
                print(f"  - Brand: {product.get('brand')}")
                print(f"  - Style ID: {product.get('styleId')}")

            # Use first product
            product_summary = search_results["products"][0]
            product_id = product_summary["productId"]

            # Step 2: Get product details
            logger.info(f"Step 2: Getting product details for ID: {product_id}")
            product_details = await catalog_service.get_product_details(product_id)

            print("\n=== PRODUCT DETAILS ===")
            print(f"Product ID: {product_details.get('productId')}")
            print(f"Title: {product_details.get('title')}")
            print(f"Brand: {product_details.get('brand')}")
            print(f"Style ID: {product_details.get('styleId')}")
            print(f"Product Type: {product_details.get('productType')}")
            print(f"URL Key: {product_details.get('urlKey')}")

            # Step 3: Get all variants
            logger.info("Step 3: Getting all variants")
            variants = await catalog_service.get_product_variants(product_id)

            print("\n=== VARIANTS ===")
            print(f"Total variants: {len(variants)}")

            # Show first 5 variants
            for variant in variants[:5]:
                print(f"  - {variant.get('variantValue')} (ID: {variant.get('variantId')})")

            # Find matching variant for our size
            matching_variant = next(
                (v for v in variants if v.get("variantValue") == test_size), None
            )

            if not matching_variant:
                print(f"\n[WARNING] No variant found for size: {test_size}")
                print(f"Available sizes: {[v.get('variantValue') for v in variants[:10]]}")
                # Use first variant as fallback
                matching_variant = variants[0]
                test_size = matching_variant.get("variantValue")
                print(f"Using size: {test_size} instead")

            # Step 4: Get market data
            logger.info(f"Step 4: Getting market data for variant: {test_size}")
            variant_id = matching_variant["variantId"]
            market_data = await catalog_service.get_market_data(
                product_id=product_id, variant_id=variant_id, currency_code="EUR"
            )

            print(f"\n=== MARKET DATA (Size: {test_size}) ===")
            print(f"Currency: {market_data.get('currencyCode')}")
            print(f"Lowest Ask: {market_data.get('lowestAskAmount')} EUR")
            print(f"Highest Bid: {market_data.get('highestBidAmount')} EUR")
            print(f"Sell Faster: {market_data.get('sellFasterAmount')} EUR")
            print(f"Earn More: {market_data.get('earnMoreAmount')} EUR")

            # Step 5: Complete enrichment
            logger.info("Step 5: Running complete enrichment workflow")
            enriched_data = await catalog_service.enrich_product_by_sku(
                sku=test_sku, size=test_size, db_session=session
            )

            print("\n=== ENRICHMENT COMPLETE ===")
            print(f"SKU: {test_sku}")
            print(f"StockX Product ID: {enriched_data.get('stockx_product_id')}")
            print(f"Variants: {len(enriched_data.get('variants', []))}")
            print(f"Market Data Available: {enriched_data.get('market_data') is not None}")

            print("\n[SUCCESS] Product enrichment completed successfully!")

        except Exception as e:
            logger.error("Enrichment test failed", error=str(e), exc_info=True)
            print(f"\n[ERROR] {e}")
            raise


if __name__ == "__main__":
    asyncio.run(test_enrichment())
