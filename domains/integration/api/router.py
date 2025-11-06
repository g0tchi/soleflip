"""
API Router for Integration-related endpoints (Awin, StockX matching, etc.)
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.awin_feed_service import AwinFeedImportService
from domains.integration.services.awin_stockx_enrichment_service import AwinStockXEnrichmentService
from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_awin_service(db: AsyncSession = Depends(get_db_session)) -> AwinFeedImportService:
    return AwinFeedImportService(db)


@router.get(
    "/awin/stats",
    summary="Get Awin Product Statistics",
    description="Get overview statistics of imported Awin products",
    response_model=Dict[str, Any],
)
async def get_awin_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """Get Awin product import statistics"""
    logger.info("Fetching Awin product statistics")

    try:
        stats_query = text("""
            SELECT
                COUNT(*) as total_products,
                COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock_count,
                COUNT(DISTINCT brand_name) as unique_brands,
                AVG(retail_price_cents) / 100.0 as avg_price_eur,
                MIN(retail_price_cents) / 100.0 as min_price_eur,
                MAX(retail_price_cents) / 100.0 as max_price_eur,
                COUNT(CASE WHEN ean IS NOT NULL AND ean != '' THEN 1 END) as products_with_ean,
                COUNT(CASE WHEN matched_product_id IS NOT NULL THEN 1 END) as matched_products
            FROM integration.awin_products
        """)

        result = await db.execute(stats_query)
        stats = result.fetchone()

        if not stats or stats.total_products == 0:
            return {
                "success": True,
                "message": "No Awin products found in database",
                "stats": {
                    "total_products": 0,
                    "in_stock": 0,
                    "brands": 0,
                }
            }

        # Get brand breakdown
        brands_query = text("""
            SELECT
                brand_name,
                COUNT(*) as product_count,
                COUNT(CASE WHEN in_stock = true THEN 1 END) as in_stock_count,
                AVG(retail_price_cents) / 100.0 as avg_price
            FROM integration.awin_products
            WHERE brand_name IS NOT NULL
            GROUP BY brand_name
            ORDER BY product_count DESC
        """)

        brands_result = await db.execute(brands_query)
        brands = [
            {
                "brand": row.brand_name,
                "total": row.product_count,
                "in_stock": row.in_stock_count,
                "avg_price_eur": float(row.avg_price) if row.avg_price else 0,
            }
            for row in brands_result.fetchall()
        ]

        ean_coverage = (stats.products_with_ean / stats.total_products * 100) if stats.total_products > 0 else 0
        match_rate = (stats.matched_products / stats.total_products * 100) if stats.total_products > 0 else 0

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "stats": {
                "total_products": stats.total_products,
                "in_stock": stats.in_stock_count,
                "out_of_stock": stats.total_products - stats.in_stock_count,
                "in_stock_percentage": round((stats.in_stock_count / stats.total_products * 100), 1) if stats.total_products > 0 else 0,
                "unique_brands": stats.unique_brands,
                "price_range": {
                    "min_eur": float(stats.min_price_eur) if stats.min_price_eur else 0,
                    "max_eur": float(stats.max_price_eur) if stats.max_price_eur else 0,
                    "avg_eur": float(stats.avg_price_eur) if stats.avg_price_eur else 0,
                },
                "ean_coverage": {
                    "products_with_ean": stats.products_with_ean,
                    "percentage": round(ean_coverage, 1),
                },
                "stockx_matching": {
                    "matched_products": stats.matched_products,
                    "match_rate_percentage": round(match_rate, 1),
                },
            },
            "brands": brands,
        }

    except Exception as e:
        logger.error("Failed to fetch Awin statistics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")


@router.get(
    "/awin/products",
    summary="List Awin Products",
    description="List Awin products with filtering and pagination",
    response_model=Dict[str, Any],
)
async def list_awin_products(
    in_stock: Optional[bool] = Query(None, description="Filter by stock status"),
    brand: Optional[str] = Query(None, description="Filter by brand name"),
    min_price_eur: Optional[float] = Query(None, description="Minimum price in EUR"),
    max_price_eur: Optional[float] = Query(None, description="Maximum price in EUR"),
    has_ean: Optional[bool] = Query(None, description="Filter products with EAN codes"),
    is_matched: Optional[bool] = Query(None, description="Filter by StockX match status"),
    limit: int = Query(50, ge=1, le=200, description="Number of products to return"),
    offset: int = Query(0, ge=0, description="Number of products to skip"),
    db: AsyncSession = Depends(get_db_session),
):
    """List Awin products with optional filters"""
    logger.info("Fetching Awin products", filters={
        "in_stock": in_stock, "brand": brand, "min_price": min_price_eur,
        "max_price": max_price_eur, "has_ean": has_ean, "is_matched": is_matched
    })

    try:
        # Build dynamic WHERE clause
        where_clauses = []
        params = {"limit": limit, "offset": offset}

        if in_stock is not None:
            where_clauses.append("in_stock = :in_stock")
            params["in_stock"] = in_stock

        if brand:
            where_clauses.append("brand_name ILIKE :brand")
            params["brand"] = f"%{brand}%"

        if min_price_eur:
            where_clauses.append("retail_price_cents >= :min_price")
            params["min_price"] = int(min_price_eur * 100)

        if max_price_eur:
            where_clauses.append("retail_price_cents <= :max_price")
            params["max_price"] = int(max_price_eur * 100)

        if has_ean is not None:
            if has_ean:
                where_clauses.append("ean IS NOT NULL AND ean != ''")
            else:
                where_clauses.append("(ean IS NULL OR ean = '')")

        if is_matched is not None:
            if is_matched:
                where_clauses.append("matched_product_id IS NOT NULL")
            else:
                where_clauses.append("matched_product_id IS NULL")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Get products
        query = text(f"""
            SELECT
                awin_product_id,
                product_name,
                brand_name,
                size,
                ean,
                retail_price_cents / 100.0 as retail_price_eur,
                stock_quantity,
                in_stock,
                merchant_product_id,
                short_description,
                image_url,
                matched_product_id,
                match_confidence,
                affiliate_link,
                updated_at
            FROM integration.awin_products
            {where_sql}
            ORDER BY retail_price_cents ASC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(query, params)
        products = [
            {
                "awin_product_id": row.awin_product_id,
                "product_name": row.product_name,
                "brand": row.brand_name,
                "size": row.size,
                "ean": row.ean,
                "retail_price_eur": float(row.retail_price_eur) if row.retail_price_eur else 0,
                "stock_quantity": row.stock_quantity,
                "in_stock": row.in_stock,
                "merchant_product_id": row.merchant_product_id,
                "description": row.short_description,
                "image_url": row.image_url,
                "matched_stockx_product_id": str(row.matched_product_id) if row.matched_product_id else None,
                "match_confidence": float(row.match_confidence) if row.match_confidence else None,
                "affiliate_link": row.affiliate_link,
                "last_updated": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in result.fetchall()
        ]

        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM integration.awin_products
            {where_sql}
        """)

        count_result = await db.execute(count_query, params)
        total_count = count_result.fetchone().total

        return {
            "success": True,
            "total_count": total_count,
            "returned_count": len(products),
            "limit": limit,
            "offset": offset,
            "products": products,
        }

    except Exception as e:
        logger.error("Failed to list Awin products", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get(
    "/awin/profit-opportunities",
    summary="Find Profit Opportunities (Awin vs StockX)",
    description="Compare Awin retail prices with StockX resale prices to find arbitrage opportunities. The MONEY PRINTER!",
    response_model=Dict[str, Any],
)
async def get_profit_opportunities(
    min_profit_eur: float = Query(20.0, ge=0, description="Minimum profit in EUR"),
    min_profit_percentage: float = Query(10.0, ge=0, description="Minimum profit margin percentage"),
    limit: int = Query(50, ge=1, le=200, description="Number of opportunities to return"),
    currency: str = Query("EUR", description="Currency for StockX prices"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Find profit opportunities by matching Awin products with StockX prices.
    This is the MONEY PRINTER - shows where you can buy from Awin and resell on StockX for profit!
    """
    logger.info("Finding profit opportunities", min_profit_eur=min_profit_eur, limit=limit)

    try:
        # First check if we have product table
        check_products_query = text("""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_name = 'product'
              AND table_schema = 'catalog'
        """)

        check_result = await db.execute(check_products_query)
        products_table_exists = check_result.fetchone().count > 0

        if not products_table_exists:
            return {
                "success": False,
                "message": "StockX products table not found. Please import StockX product data first.",
                "opportunities": [],
                "total_opportunities": 0,
            }

        # Use catalog schema (products are now in catalog.product)
        schema = 'catalog'

        # Check if products table has the columns we need
        columns_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'product'
              AND table_schema = :schema
              AND column_name IN ('ean', 'lowest_ask', 'name', 'brand_id', 'price', 'product_name')
        """)

        columns_result = await db.execute(columns_query, {"schema": schema})
        available_columns = {row.column_name for row in columns_result.fetchall()}

        if 'ean' not in available_columns:
            return {
                "success": False,
                "message": f"Products table in schema '{schema}' does not have 'ean' column for matching",
                "opportunities": [],
                "total_opportunities": 0,
            }

        # SECURITY: Whitelist validation for column names
        ALLOWED_PRICE_COLUMNS = {'lowest_ask', 'price'}
        ALLOWED_NAME_COLUMNS = {'name', 'product_name'}

        price_column = 'lowest_ask' if 'lowest_ask' in available_columns else 'price'
        name_column = 'name' if 'name' in available_columns else 'product_name'

        if price_column not in ALLOWED_PRICE_COLUMNS or name_column not in ALLOWED_NAME_COLUMNS:
            return {
                "success": False,
                "message": "Invalid column configuration detected",
                "opportunities": [],
                "total_opportunities": 0,
            }

        min_profit_cents = int(min_profit_eur * 100)

        # SECURITY: Use identifier() for schema/table/column names or parameterize the entire query
        # Build safe query with validated identifiers

        # For complex queries with dynamic schema/columns, use string building but with whitelisted values
        # This is now safe because schema, price_column, and name_column are validated against whitelists
        query = text(f"""
            SELECT
                ap.awin_product_id,
                ap.product_name as awin_product_name,
                ap.brand_name,
                ap.size,
                ap.ean,
                ap.retail_price_cents / 100.0 as retail_price_eur,
                ap.stock_quantity,
                ap.affiliate_link,
                ap.alternate_image,
                p.id as stockx_product_id,
                p.{name_column} as stockx_product_name,
                p.{price_column} as stockx_price_cents,
                p.{price_column} / 100.0 as stockx_price_eur,
                (p.{price_column} - ap.retail_price_cents) as profit_cents,
                (p.{price_column} - ap.retail_price_cents) / 100.0 as profit_eur,
                ROUND(((p.{price_column} - ap.retail_price_cents)::numeric / NULLIF(ap.retail_price_cents, 0)::numeric * 100), 1) as profit_percentage
            FROM integration.awin_products ap
            INNER JOIN {schema}.product p ON ap.ean = p.ean
            WHERE ap.ean IS NOT NULL
              AND ap.ean != ''
              AND ap.in_stock = true
              AND ap.stockx_product_id IS NOT NULL
              AND ap.enrichment_status = 'matched'
              AND p.{price_column} IS NOT NULL
              AND (p.{price_column} - ap.retail_price_cents) >= :min_profit_cents
              AND ROUND(((p.{price_column} - ap.retail_price_cents)::numeric / NULLIF(ap.retail_price_cents, 0)::numeric * 100), 1) >= :min_profit_percentage
            ORDER BY profit_eur DESC
            LIMIT :limit
        """)

        result = await db.execute(query, {
            "min_profit_cents": min_profit_cents,
            "min_profit_percentage": min_profit_percentage,
            "limit": limit
        })

        opportunities = [
            {
                "awin": {
                    "product_id": row.awin_product_id,
                    "product_name": row.awin_product_name,
                    "brand": row.brand_name,
                    "size": row.size,
                    "ean": row.ean,
                    "retail_price_eur": float(row.retail_price_eur),
                    "stock_quantity": row.stock_quantity,
                    "affiliate_link": row.affiliate_link,
                    "image_url": row.alternate_image,
                },
                "stockx": {
                    "product_id": str(row.stockx_product_id),
                    "product_name": row.stockx_product_name,
                    "resale_price_eur": float(row.stockx_price_eur),
                },
                "profit": {
                    "amount_eur": float(row.profit_eur),
                    "percentage": float(row.profit_percentage),
                    "roi": float(row.profit_percentage),
                },
                "opportunity_score": float(row.profit_eur * row.profit_percentage / 100),  # Combined score
            }
            for row in result.fetchall()
        ]

        # Get total count of opportunities
        # SECURITY: schema and price_column are validated against whitelists above
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM integration.awin_products ap
            INNER JOIN {schema}.product p ON ap.ean = p.ean
            WHERE ap.ean IS NOT NULL
              AND ap.ean != ''
              AND ap.in_stock = true
              AND ap.stockx_product_id IS NOT NULL
              AND ap.enrichment_status = 'matched'
              AND p.{price_column} IS NOT NULL
              AND (p.{price_column} - ap.retail_price_cents) >= :min_profit_cents
              AND ROUND(((p.{price_column} - ap.retail_price_cents)::numeric / NULLIF(ap.retail_price_cents, 0)::numeric * 100), 1) >= :min_profit_percentage
        """)

        count_result = await db.execute(count_query, {
            "min_profit_cents": min_profit_cents,
            "min_profit_percentage": min_profit_percentage,
        })
        total_opportunities = count_result.fetchone().total

        # Calculate summary statistics
        total_potential_profit = sum(opp["profit"]["amount_eur"] for opp in opportunities)
        avg_profit = total_potential_profit / len(opportunities) if opportunities else 0
        avg_roi = sum(opp["profit"]["percentage"] for opp in opportunities) / len(opportunities) if opportunities else 0

        return {
            "success": True,
            "message": f"Found {total_opportunities} profit opportunities! 🤑",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "filters": {
                "min_profit_eur": min_profit_eur,
                "min_profit_percentage": min_profit_percentage,
                "currency": currency,
            },
            "summary": {
                "total_opportunities": total_opportunities,
                "returned_count": len(opportunities),
                "total_potential_profit_eur": round(total_potential_profit, 2),
                "avg_profit_eur": round(avg_profit, 2),
                "avg_roi_percentage": round(avg_roi, 1),
                "best_opportunity_eur": round(opportunities[0]["profit"]["amount_eur"], 2) if opportunities else 0,
            },
            "opportunities": opportunities,
            "note": "Prices are StockX lowest ask. Factor in fees: Awin commission (~5-15%), StockX seller fees (~10%), shipping costs.",
        }

    except Exception as e:
        logger.error("Failed to find profit opportunities", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find opportunities: {str(e)}")


@router.post(
    "/awin/match-products",
    summary="Match Awin Products with StockX by EAN",
    description="Automatically match Awin products to StockX products using EAN codes",
    response_model=Dict[str, Any],
)
async def match_awin_products(
    awin_service: AwinFeedImportService = Depends(get_awin_service),
):
    """Match Awin products with StockX products by EAN"""
    logger.info("Starting Awin-StockX product matching")

    try:
        matched_count = await awin_service.match_products_by_ean()

        return {
            "success": True,
            "message": f"Successfully matched {matched_count} products",
            "matched_count": matched_count,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }

    except Exception as e:
        logger.error("Failed to match products", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")


@router.get(
    "/debug/products-enrichment",
    summary="[DEBUG] Check Products Enrichment Data",
    description="Debug endpoint to inspect enrichment_data field in products table",
    response_model=Dict[str, Any],
)
async def debug_products_enrichment(
    limit: int = Query(5, ge=1, le=20, description="Number of products to sample"),
    db: AsyncSession = Depends(get_db_session),
):
    """Debug endpoint to check products enrichment data"""
    logger.info("Checking products enrichment data")

    try:
        # Check table structure
        columns_query = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'catalog' AND table_name = 'product'
            AND column_name IN ('id', 'name', 'sku', 'ean', 'enrichment_data')
            ORDER BY column_name
        """)

        result = await db.execute(columns_query)
        columns = {row.column_name: row.data_type for row in result.fetchall()}

        # Get sample products with enrichment data
        sample_query = text("""
            SELECT
                id,
                name,
                sku,
                enrichment_data
            FROM catalog.product
            WHERE enrichment_data IS NOT NULL
            LIMIT :limit
        """)

        result = await db.execute(sample_query, {"limit": limit})
        samples = []

        for row in result.fetchall():
            enrichment = row.enrichment_data if row.enrichment_data else {}

            # Extract EAN-related fields
            ean_fields = {}
            ean_keys = ['ean', 'gtin', 'upc', 'barcode', 'gtins', 'productGtin']
            for key in ean_keys:
                if key in enrichment:
                    ean_fields[key] = enrichment[key]

            samples.append({
                "id": str(row.id),
                "name": row.name,
                "sku": row.sku,
                "enrichment_keys": list(enrichment.keys()) if enrichment else [],
                "ean_fields": ean_fields,
                "has_ean_data": len(ean_fields) > 0,
            })

        # Count products with enrichment
        count_query = text("""
            SELECT
                COUNT(*) as total,
                COUNT(enrichment_data) as with_enrichment
            FROM catalog.product
        """)

        result = await db.execute(count_query)
        counts = result.fetchone()

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "table_columns": columns,
            "stats": {
                "total_products": counts.total,
                "products_with_enrichment": counts.with_enrichment,
                "enrichment_percentage": round((counts.with_enrichment / counts.total * 100), 1) if counts.total > 0 else 0,
            },
            "sample_products": samples,
            "analysis": {
                "products_with_ean_in_enrichment": sum(1 for s in samples if s["has_ean_data"]),
                "sample_size": len(samples),
            }
        }

    except Exception as e:
        logger.error("Failed to check enrichment data", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Debug check failed: {str(e)}")


@router.get(
    "/debug/variants-with-gtin",
    summary="[DEBUG] Check Variants for GTIN/EAN Data",
    description="Debug endpoint to inspect variants array in enrichment_data for GTINs",
    response_model=Dict[str, Any],
)
async def debug_variants_gtin(
    limit: int = Query(3, ge=1, le=10, description="Number of products to sample"),
    db: AsyncSession = Depends(get_db_session),
):
    """Debug endpoint to check variants for GTIN/EAN codes"""
    logger.info("Checking variants for GTIN data")

    try:
        # Get sample products with enrichment and variants
        sample_query = text("""
            SELECT
                id,
                name,
                sku,
                enrichment_data
            FROM catalog.product
            WHERE enrichment_data IS NOT NULL
              AND enrichment_data->'variants' IS NOT NULL
            LIMIT :limit
        """)

        result = await db.execute(sample_query, {"limit": limit})
        samples = []

        for row in result.fetchall():
            enrichment = row.enrichment_data if row.enrichment_data else {}
            variants = enrichment.get('variants', [])

            # Extract GTIN data from variants
            variants_with_gtin = []
            for variant in variants[:5]:  # First 5 variants per product
                gtin_data = {
                    'variant_id': variant.get('id'),
                    'size': variant.get('sizeAllTypes', {}).get('us'),
                    'gtin': variant.get('gtin'),
                    'gtins': variant.get('gtins', []),
                    'hidden': variant.get('hidden'),
                }

                # Check if has any GTIN
                has_gtin = bool(gtin_data['gtin'] or gtin_data['gtins'])
                if has_gtin:
                    variants_with_gtin.append(gtin_data)

            samples.append({
                "id": str(row.id),
                "name": row.name,
                "sku": row.sku,
                "total_variants": len(variants),
                "variants_with_gtin": len(variants_with_gtin),
                "sample_variants": variants_with_gtin[:3],  # Show first 3
            })

        # Count total products with variant GTINs
        count_query = text("""
            SELECT COUNT(*) as count
            FROM catalog.product
            WHERE enrichment_data IS NOT NULL
              AND enrichment_data->'variants' IS NOT NULL
        """)

        result = await db.execute(count_query)
        total_with_variants = result.fetchone().count

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "stats": {
                "products_with_variants": total_with_variants,
                "sample_size": len(samples),
            },
            "samples": samples,
            "recommendation": "If variants contain GTINs, we can extract and match them with Awin EANs!"
        }

    except Exception as e:
        logger.error("Failed to check variants GTIN data", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Variants check failed: {str(e)}")


# ==============================================================================
# BUDIBASE INTEGRATION - Enrichment Job Control Endpoints
# ==============================================================================

@router.post(
    "/awin/enrichment/start",
    summary="Start Enrichment Job",
    description="Start background job to match all Awin products with StockX via EAN. Returns job_id for tracking progress.",
    response_model=Dict[str, Any],
)
async def start_enrichment_job(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Limit for testing (default: process all)"),
    rate_limit: int = Query(60, ge=10, le=120, description="Requests per minute (default: 60)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Start enrichment job to match Awin products with StockX

    This endpoint is designed for Budibase automation:
    - Starts job in background
    - Returns job_id for status tracking
    - Estimated duration based on product count

    Rate limiting:
    - Default: 60 requests/minute (conservative)
    - Increase if no errors (max 120)
    """
    logger.info("Starting enrichment job", limit=limit, rate_limit=rate_limit)

    try:
        service = AwinStockXEnrichmentService(
            db,
            rate_limit_requests_per_minute=rate_limit
        )

        # Create job
        job_id = await service.create_enrichment_job()

        # Count products to process
        # SECURITY: Use parameterized query for limit
        if limit is not None:
            count_query = text("""
                SELECT COUNT(*) as total
                FROM (
                    SELECT 1
                    FROM integration.awin_products
                    WHERE ean IS NOT NULL
                      AND in_stock = true
                      AND (enrichment_status = 'pending' OR enrichment_status IS NULL OR last_enriched_at IS NULL)
                    LIMIT :limit
                ) subquery
            """)
            result = await db.execute(count_query, {"limit": limit})
        else:
            count_query = text("""
                SELECT COUNT(*) as total
                FROM integration.awin_products
                WHERE ean IS NOT NULL
                  AND in_stock = true
                  AND (enrichment_status = 'pending' OR enrichment_status IS NULL OR last_enriched_at IS NULL)
            """)
            result = await db.execute(count_query)

        total_products = result.fetchone().total

        # Calculate estimated duration
        estimated_minutes = (total_products * (60.0 / rate_limit)) / 60.0

        # Start enrichment in background
        async def run_enrichment():
            async with get_db_session() as bg_session:
                bg_service = AwinStockXEnrichmentService(
                    bg_session,
                    rate_limit_requests_per_minute=rate_limit
                )
                await bg_service.enrich_all_products(job_id=job_id, limit=limit)

        background_tasks.add_task(run_enrichment)

        return {
            "success": True,
            "job_id": str(job_id),
            "message": "Enrichment job started",
            "total_products": total_products,
            "rate_limit_per_minute": rate_limit,
            "estimated_duration_minutes": round(estimated_minutes, 1),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }

    except Exception as e:
        logger.error("Failed to start enrichment job", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start enrichment: {str(e)}")


@router.get(
    "/awin/enrichment/status/{job_id}",
    summary="Get Job Status",
    description="Get real-time progress of running enrichment job. Designed for Budibase progress monitoring.",
    response_model=Dict[str, Any],
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get enrichment job progress

    Use this for Budibase:
    - Progress bar component
    - Auto-refresh every 30 seconds
    - Show notifications on completion
    """
    logger.info("Getting job status", job_id=str(job_id))

    try:
        query = text("""
            SELECT
                id,
                job_type,
                status,
                total_products,
                processed_products,
                matched_products,
                failed_products,
                results_summary,
                error_log,
                started_at,
                completed_at,
                updated_at
            FROM integration.awin_enrichment_jobs
            WHERE id = :job_id
        """)

        result = await db.execute(query, {"job_id": str(job_id)})
        job = result.fetchone()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Calculate progress
        progress_percentage = 0
        if job.total_products and job.total_products > 0:
            progress_percentage = round((job.processed_products / job.total_products * 100), 1)

        # Calculate elapsed time and ETA
        elapsed_minutes = None
        estimated_remaining_minutes = None

        if job.started_at:
            elapsed_seconds = (datetime.now(timezone.utc) - job.started_at).total_seconds()
            elapsed_minutes = round(elapsed_seconds / 60, 1)

            if job.processed_products > 0 and job.status == 'running':
                seconds_per_product = elapsed_seconds / job.processed_products
                remaining_products = job.total_products - job.processed_products
                estimated_remaining_seconds = remaining_products * seconds_per_product
                estimated_remaining_minutes = round(estimated_remaining_seconds / 60, 1)

        response = {
            "success": True,
            "job": {
                "id": str(job.id),
                "type": job.job_type,
                "status": job.status,
                "progress": {
                    "total": job.total_products,
                    "processed": job.processed_products,
                    "matched": job.matched_products,
                    "not_found": (job.processed_products - job.matched_products - job.failed_products) if job.processed_products else 0,
                    "errors": job.failed_products,
                    "percentage": progress_percentage,
                },
                "started_at": job.started_at.isoformat() + "Z" if job.started_at else None,
                "completed_at": job.completed_at.isoformat() + "Z" if job.completed_at else None,
                "elapsed_minutes": elapsed_minutes,
                "estimated_remaining_minutes": estimated_remaining_minutes,
            },
        }

        # Add results summary if completed
        if job.status == 'completed' and job.results_summary:
            response["results"] = job.results_summary

        # Add error log if failed
        if job.status == 'failed' and job.error_log:
            response["error"] = job.error_log

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=str(job_id), error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.get(
    "/awin/enrichment/latest",
    summary="Get Latest Enrichment Results",
    description="Get results from most recent completed enrichment job. For Budibase dashboard widgets.",
    response_model=Dict[str, Any],
)
async def get_latest_enrichment(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get latest enrichment job results

    Use this for Budibase:
    - Dashboard summary cards
    - Historical tracking
    - Success/failure notifications
    """
    logger.info("Getting latest enrichment results")

    try:
        query = text("""
            SELECT
                id,
                job_type,
                status,
                total_products,
                processed_products,
                matched_products,
                failed_products,
                results_summary,
                started_at,
                completed_at
            FROM integration.awin_enrichment_jobs
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        """)

        result = await db.execute(query)
        job = result.fetchone()

        if not job:
            return {
                "success": True,
                "message": "No completed enrichment jobs found",
                "job": None,
            }

        # Calculate duration
        duration_minutes = None
        if job.started_at and job.completed_at:
            duration_seconds = (job.completed_at - job.started_at).total_seconds()
            duration_minutes = round(duration_seconds / 60, 1)

        return {
            "success": True,
            "job": {
                "id": str(job.id),
                "type": job.job_type,
                "status": job.status,
                "completed_at": job.completed_at.isoformat() + "Z" if job.completed_at else None,
                "duration_minutes": duration_minutes,
                "results": job.results_summary if job.results_summary else {
                    "total_processed": job.processed_products,
                    "matched": job.matched_products,
                    "failed": job.failed_products,
                    "not_found": job.processed_products - job.matched_products - job.failed_products,
                    "match_rate_percentage": round((job.matched_products / job.processed_products * 100), 1) if job.processed_products > 0 else 0,
                },
            },
        }

    except Exception as e:
        logger.error("Failed to get latest enrichment", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get latest enrichment: {str(e)}")


@router.get(
    "/awin/enrichment/stats",
    summary="Get Enrichment Statistics",
    description="Get current enrichment status overview. Shows how many products are matched, pending, etc.",
    response_model=Dict[str, Any],
)
async def get_enrichment_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current enrichment statistics

    Use this for Budibase:
    - Dashboard KPI cards
    - Data quality monitoring
    - Enrichment coverage tracking
    """
    logger.info("Getting enrichment statistics")

    try:
        service = AwinStockXEnrichmentService(db)
        stats = await service.get_enrichment_stats()

        # Get last enrichment timestamp
        last_enrichment_query = text("""
            SELECT MAX(last_enriched_at) as last_enrichment
            FROM integration.awin_products
            WHERE enrichment_status IS NOT NULL
        """)

        result = await db.execute(last_enrichment_query)
        last_enrichment = result.fetchone().last_enrichment

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "stats": {
                **stats,
                "last_enrichment": last_enrichment.isoformat() + "Z" if last_enrichment else None,
            },
        }

    except Exception as e:
        logger.error("Failed to get enrichment stats", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get enrichment stats: {str(e)}")
