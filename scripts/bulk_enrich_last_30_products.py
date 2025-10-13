"""
Bulk Product Enrichment - Last 30 Products

Enriches the last 30 products in the database using StockX Catalog API v2.
Respects rate limits (1 request/second) and provides detailed progress tracking.
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from domains.integration.services.stockx_service import StockXService
from domains.integration.services.stockx_catalog_service import StockXCatalogService

load_dotenv()

logger = structlog.get_logger(__name__)


async def get_last_30_products(session: AsyncSession) -> List[Dict[str, Any]]:
    """Get the last 30 products from database ordered by created_at"""
    query = text("""
        SELECT
            p.id,
            p.sku,
            p.name,
            b.name as brand_name,
            p.stockx_product_id,
            p.last_enriched_at,
            p.created_at
        FROM products.products p
        LEFT JOIN core.brands b ON p.brand_id = b.id
        WHERE p.sku IS NOT NULL AND p.sku != ''
        ORDER BY p.created_at DESC
        LIMIT 30
    """)

    result = await session.execute(query)
    products = []
    for row in result.fetchall():
        products.append({
            "id": row.id,
            "sku": row.sku,
            "name": row.name,
            "brand_name": row.brand_name,
            "stockx_product_id": row.stockx_product_id,
            "last_enriched_at": row.last_enriched_at,
            "created_at": row.created_at
        })

    return products


async def enrich_single_product(
    catalog_service: StockXCatalogService,
    product: Dict[str, Any],
    session: AsyncSession
) -> Dict[str, Any]:
    """Enrich a single product and return result summary"""

    sku = product["sku"]
    product_name = product["name"]

    try:
        logger.info(f"Starting enrichment", sku=sku, product_name=product_name)

        # Perform enrichment
        enriched_data = await catalog_service.enrich_product_by_sku(
            sku=sku,
            size=None,  # No specific size, just get all variants
            db_session=session
        )

        if enriched_data.get("error"):
            logger.warning(f"Product not found on StockX", sku=sku, error=enriched_data["error"])
            return {
                "sku": sku,
                "status": "not_found",
                "error": enriched_data["error"]
            }

        # Success
        stockx_product_id = enriched_data.get("stockx_product_id")
        variants_count = len(enriched_data.get("variants", []))

        logger.info(
            f"Product enriched successfully",
            sku=sku,
            stockx_product_id=stockx_product_id,
            variants_count=variants_count
        )

        return {
            "sku": sku,
            "status": "success",
            "stockx_product_id": stockx_product_id,
            "variants_count": variants_count,
            "product_title": enriched_data.get("product_details", {}).get("title")
        }

    except Exception as e:
        logger.error(f"Failed to enrich product", sku=sku, error=str(e), exc_info=True)
        return {
            "sku": sku,
            "status": "error",
            "error": str(e)
        }


async def bulk_enrich_products():
    """Main function to enrich last 30 products"""

    start_time = datetime.now()

    print("=" * 80)
    print("StockX Catalog Bulk Enrichment - Last 30 Products")
    print("=" * 80)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Database setup
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    engine = create_async_engine(database_url)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Initialize services
        stockx_service = StockXService(db_session=session)
        catalog_service = StockXCatalogService(stockx_service=stockx_service)

        # Get products to enrich
        print("Fetching last 30 products from database...")
        products = await get_last_30_products(session)

        print(f"Found {len(products)} products to enrich")
        print()

        if not products:
            print("No products found with SKU. Exiting.")
            return

        # Show products overview
        print("Products to enrich:")
        print("-" * 80)
        for i, product in enumerate(products, 1):
            enriched_status = "[Y]" if product["last_enriched_at"] else "[ ]"
            print(f"{i:2d}. {enriched_status} {product['sku']:15s} | {product['name'][:50]}")
        print()

        # Auto-start (no confirmation needed when run from script)
        print()
        print(f"Starting enrichment of {len(products)} products...")
        print()
        print("Rate limit: 1 request/second (with 1.2s delay for safety)")
        print("=" * 80)
        print()

        # Track results
        results = []
        success_count = 0
        not_found_count = 0
        error_count = 0

        # Enrich each product
        for i, product in enumerate(products, 1):
            print(f"[{i}/{len(products)}] Enriching: {product['sku']} - {product['name'][:40]}...")

            result = await enrich_single_product(catalog_service, product, session)
            results.append(result)

            # Update counters
            if result["status"] == "success":
                success_count += 1
                print(f"  [OK] SUCCESS: {result.get('product_title', 'N/A')}")
                print(f"    StockX ID: {result.get('stockx_product_id')}")
                print(f"    Variants: {result.get('variants_count')}")
            elif result["status"] == "not_found":
                not_found_count += 1
                print(f"  [X] NOT FOUND: {result.get('error')}")
            else:
                error_count += 1
                print(f"  [X] ERROR: {result.get('error')}")

            print()

            # Rate limiting: 1 request per second + 20% buffer = 1.2 seconds
            if i < len(products):  # Don't wait after last product
                await asyncio.sleep(1.2)

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("=" * 80)
        print("ENRICHMENT COMPLETE")
        print("=" * 80)
        print(f"Total products processed: {len(products)}")
        print(f"  [OK] Successfully enriched: {success_count}")
        print(f"  [X] Not found on StockX: {not_found_count}")
        print(f"  [X] Errors: {error_count}")
        print()
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"Average: {duration/len(products):.1f} seconds per product")
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Show errors if any
        if error_count > 0:
            print("=" * 80)
            print("ERRORS DETAIL")
            print("=" * 80)
            for result in results:
                if result["status"] == "error":
                    print(f"SKU: {result['sku']}")
                    print(f"  Error: {result['error']}")
                    print()

        # Show not found if any
        if not_found_count > 0:
            print("=" * 80)
            print("NOT FOUND ON STOCKX")
            print("=" * 80)
            for result in results:
                if result["status"] == "not_found":
                    print(f"SKU: {result['sku']}")
            print()

        print("=" * 80)
        print("Done! Check the database to verify enriched data.")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(bulk_enrich_products())
