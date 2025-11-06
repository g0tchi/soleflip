"""
API Router for Product-related endpoints
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.stockx_service import StockXService
from domains.integration.services.stockx_catalog_service import StockXCatalogService
from domains.inventory.services.inventory_service import InventoryService
from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)


def get_stockx_service(db: AsyncSession = Depends(get_db_session)) -> StockXService:
    return StockXService(db)


def get_catalog_service(db: AsyncSession = Depends(get_db_session)) -> StockXCatalogService:
    stockx_service = StockXService(db)
    return StockXCatalogService(stockx_service)


@router.post(
    "/{product_id}/sync-variants-from-stockx",
    status_code=202,
    summary="Sync Product Variants from StockX",
    description="Triggers a background task to sync all product variants from StockX, creating or updating inventory items.",
)
async def sync_product_variants(product_id: UUID, background_tasks: BackgroundTasks):
    logger.info("Received request to sync product variants from StockX", product_id=str(product_id))

    async def run_sync_task(product_id: UUID):
        from shared.database.connection import db_manager

        async with db_manager.get_session() as bg_session:
            try:
                inventory_service = InventoryService(bg_session)
                await inventory_service.sync_inventory_from_stockx(product_id)
            except Exception as e:
                logger.error(
                    "StockX variant sync background task failed",
                    product_id=str(product_id),
                    error=str(e),
                    exc_info=True,
                )

    background_tasks.add_task(run_sync_task, product_id)

    return {"message": "Product variant synchronization has been queued."}


@router.get(
    "/{product_id}/stockx-details",
    summary="Get Product Details from StockX",
    description="Fetches real-time product details for a given product ID directly from the StockX Catalog API.",
    response_model=Dict[str, Any],
)
async def get_stockx_product_details(
    product_id: str, stockx_service: StockXService = Depends(get_stockx_service)
):
    logger.info("Received request to fetch product details from StockX", product_id=product_id)

    details = await stockx_service.get_product_details(product_id)

    if not details:
        raise HTTPException(
            status_code=404, detail=f"Product with ID '{product_id}' not found on StockX."
        )

    return details


@router.get(
    "/search-stockx",
    summary="Search for Products on StockX",
    description="Performs a search against the StockX Catalog API using a query string.",
    response_model=Dict[str, Any],
)
async def search_stockx_products(
    query: str = Query(
        ..., min_length=1, max_length=100, description="Keyword, GTIN, or Style ID to search for."
    ),
    page: int = Query(1, alias="pageNumber", ge=1, description="Requested page number."),
    page_size: int = Query(
        10, alias="pageSize", ge=1, le=50, description="Number of products to return per page."
    ),
    stockx_service: StockXService = Depends(get_stockx_service),
):
    logger.info(
        "Received request to search StockX catalog", query=query, page=page, page_size=page_size
    )

    search_results = await stockx_service.search_stockx_catalog(
        query=query, page=page, page_size=page_size
    )

    if search_results is None:
        # This can happen if there was an HTTP error in the service
        raise HTTPException(
            status_code=502, detail="Failed to retrieve search results from StockX."
        )

    return search_results


@router.get(
    "/{product_id}/stockx-market-data",
    summary="Get Market Data from StockX",
    description="Fetches real-time market data (highest bid, lowest ask) for all variants of a product from the StockX API.",
    response_model=List[Dict[str, Any]],
)
async def get_stockx_market_data(
    product_id: str,
    currency: Optional[str] = Query(
        None, alias="currencyCode", description="ISO 4217 currency code."
    ),
    stockx_service: StockXService = Depends(get_stockx_service),
):
    logger.info(
        "Received request to fetch market data from StockX",
        product_id=product_id,
        currency=currency,
    )

    market_data = await stockx_service.get_market_data_from_stockx(
        product_id=product_id, currency_code=currency
    )

    if market_data is None:
        raise HTTPException(
            status_code=404, detail=f"Product with ID '{product_id}' not found on StockX."
        )

    return market_data


@router.post(
    "/enrich",
    status_code=202,
    summary="Enrich Product Data",
    description="Enriches product data with information from StockX API (runs in background)",
)
async def enrich_product_data(
    background_tasks: BackgroundTasks,
    product_ids: Optional[List[str]] = Query(
        None,
        description="Specific product IDs to enrich (if none provided, enriches all products needing enrichment)",
    ),
):
    """Enrich product data with StockX information"""
    logger.info("Received request to enrich product data", product_ids=product_ids)

    async def run_enrichment_task(product_ids: Optional[List[str]] = None):
        from sqlalchemy import text

        from shared.database.connection import db_manager

        async with db_manager.get_session() as bg_session:
            try:
                stockx_service = StockXService(bg_session)

                # Get products that need enrichment
                if product_ids:
                    # Enrich specific products
                    products_query = text(
                        """
                        SELECT p.id, p.name, p.sku, b.name as brand_name
                        FROM catalog.product p
                        LEFT JOIN catalog.brand b ON p.brand_id = b.id
                        WHERE p.id = ANY(:product_ids)
                    """
                    )
                    result = await bg_session.execute(products_query, {"product_ids": product_ids})
                else:
                    # Get all products needing enrichment
                    products_query = text(
                        """
                        SELECT p.id, p.name, p.sku, b.name as brand_name
                        FROM catalog.product p  
                        LEFT JOIN catalog.brand b ON p.brand_id = b.id
                        WHERE p.sku IS NULL OR p.sku = '' 
                        OR p.description IS NULL 
                        OR p.retail_price IS NULL
                        OR p.release_date IS NULL
                        LIMIT 50
                    """
                    )
                    result = await bg_session.execute(products_query)

                products = result.fetchall()
                enriched_count = 0

                for product in products:
                    try:
                        # Search StockX for this product
                        search_query = (
                            f"{product.brand_name} {product.name}"
                            if product.brand_name
                            else product.name
                        )
                        search_results = await stockx_service.search_stockx_catalog(
                            search_query, page=1, page_size=5
                        )

                        if search_results and search_results.get("products"):
                            # Take the first matching result
                            stockx_product = search_results["products"][0]

                            # Update product with enriched data
                            update_query = text(
                                """
                                UPDATE catalog.product 
                                SET 
                                    sku = COALESCE(sku, :sku),
                                    description = COALESCE(description, :description),
                                    retail_price = COALESCE(retail_price, :retail_price),
                                    release_date = COALESCE(release_date, :release_date),
                                    updated_at = NOW()
                                WHERE id = :product_id
                            """
                            )

                            await bg_session.execute(
                                update_query,
                                {
                                    "product_id": product.id,
                                    "sku": stockx_product.get("id"),
                                    "description": stockx_product.get("description", "")[
                                        :500
                                    ],  # Limit description length
                                    "retail_price": stockx_product.get("retailPrice"),
                                    "release_date": stockx_product.get("releaseDate"),
                                },
                            )

                            enriched_count += 1
                            logger.info(
                                "Enriched product",
                                product_id=product.id,
                                sku=stockx_product.get("id"),
                            )

                    except Exception as e:
                        logger.warning(
                            "Failed to enrich product", product_id=product.id, error=str(e)
                        )
                        continue

                await bg_session.commit()
                logger.info(
                    "Product enrichment completed",
                    enriched_count=enriched_count,
                    total_processed=len(products),
                )

            except Exception as e:
                logger.error(
                    "Product enrichment background task failed", error=str(e), exc_info=True
                )

    background_tasks.add_task(run_enrichment_task, product_ids)

    return {
        "message": "Product enrichment has been queued.",
        "target_products": "specific" if product_ids else "all_needing_enrichment",
    }


@router.get(
    "/enrichment/status",
    summary="Get Product Enrichment Status",
    description="Get statistics about product enrichment status",
    response_model=Dict[str, Any],
)
async def get_enrichment_status(
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get product enrichment statistics"""
    logger.info("Fetching product enrichment status")

    try:
        # Get enrichment statistics
        stats_query = text(
            """
            SELECT 
                COUNT(*) as total_products,
                COUNT(sku) as products_with_sku,
                COUNT(description) as products_with_description,
                COUNT(retail_price) as products_with_retail_price,
                COUNT(release_date) as products_with_release_date,
                COUNT(CASE WHEN sku IS NULL OR sku = '' THEN 1 END) as products_needing_sku,
                COUNT(CASE WHEN description IS NULL OR description = '' THEN 1 END) as products_needing_description,
                COUNT(CASE WHEN retail_price IS NULL THEN 1 END) as products_needing_retail_price,
                COUNT(CASE WHEN release_date IS NULL THEN 1 END) as products_needing_release_date
            FROM catalog.product
        """
        )

        result = await db.execute(stats_query)
        stats = result.fetchone()

        # Calculate completion percentages
        total = stats.total_products if stats.total_products > 0 else 1

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_products": stats.total_products,
            "enrichment_stats": {
                "sku": {
                    "completed": stats.products_with_sku,
                    "missing": stats.products_needing_sku,
                    "completion_percentage": round((stats.products_with_sku / total) * 100, 1),
                },
                "description": {
                    "completed": stats.products_with_description,
                    "missing": stats.products_needing_description,
                    "completion_percentage": round(
                        (stats.products_with_description / total) * 100, 1
                    ),
                },
                "retail_price": {
                    "completed": stats.products_with_retail_price,
                    "missing": stats.products_needing_retail_price,
                    "completion_percentage": round(
                        (stats.products_with_retail_price / total) * 100, 1
                    ),
                },
                "release_date": {
                    "completed": stats.products_with_release_date,
                    "missing": stats.products_needing_release_date,
                    "completion_percentage": round(
                        (stats.products_with_release_date / total) * 100, 1
                    ),
                },
            },
            "overall_completion": round(
                (
                    (
                        stats.products_with_sku
                        + stats.products_with_description
                        + stats.products_with_retail_price
                        + stats.products_with_release_date
                    )
                    / (total * 4)
                )
                * 100,
                1,
            ),
        }

    except Exception as e:
        logger.error("Failed to fetch enrichment status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch enrichment status")


# ============================================================================
# StockX Catalog API v2 Endpoints (NEW - Uses StockXCatalogService)
# ============================================================================


@router.post(
    "/catalog/enrich-by-sku",
    status_code=200,
    summary="Enrich Product by SKU using Catalog API v2",
    description="Enriches a product by searching StockX Catalog API v2 by SKU, fetching complete details, variants, and market data. Updates database with enriched data.",
    response_model=Dict[str, Any],
)
async def enrich_product_by_sku(
    sku: str = Query(..., description="Product SKU to search and enrich"),
    size: Optional[str] = Query(None, description="Specific size to get market data for"),
    catalog_service: StockXCatalogService = Depends(get_catalog_service),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Complete product enrichment workflow:
    1. Search catalog by SKU
    2. Get product details
    3. Get all variants (sizes)
    4. Get market data for specific size (if provided)
    5. Update database with enriched data
    """
    logger.info("Received request to enrich product by SKU", sku=sku, size=size)

    try:
        enriched_data = await catalog_service.enrich_product_by_sku(
            sku=sku, size=size, db_session=db
        )

        if enriched_data.get("error"):
            raise HTTPException(status_code=404, detail=enriched_data["error"])

        return {
            "success": True,
            "message": "Product enrichment completed successfully",
            "data": {
                "sku": enriched_data.get("sku"),
                "stockx_product_id": enriched_data.get("stockx_product_id"),
                "product_title": enriched_data.get("product_details", {}).get("title"),
                "brand": enriched_data.get("product_details", {}).get("brand"),
                "total_variants": len(enriched_data.get("variants", [])),
                "market_data_available": enriched_data.get("market_data") is not None,
                "lowest_ask": (
                    enriched_data.get("market_data", {}).get("lowestAskAmount")
                    if enriched_data.get("market_data")
                    else None
                ),
                "enrichment_timestamp": enriched_data.get("enrichment_timestamp"),
            },
            "full_data": enriched_data,  # Complete enriched data for debugging
        }

    except Exception as e:
        logger.error("Failed to enrich product by SKU", sku=sku, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.get(
    "/catalog/search",
    summary="Search StockX Catalog API v2",
    description="Search StockX Catalog API v2 by SKU, GTIN, styleId, or freeform text query. Returns paginated results.",
    response_model=Dict[str, Any],
)
async def search_catalog(
    query: str = Query(..., min_length=1, description="SKU, GTIN, styleId, or product name"),
    page_number: int = Query(1, ge=1, le=100, description="Page number (starts at 1)"),
    page_size: int = Query(10, ge=1, le=50, description="Results per page (max 50)"),
    catalog_service: StockXCatalogService = Depends(get_catalog_service),
):
    """
    Search StockX catalog - useful for:
    - Finding products by SKU before enrichment
    - Exploring product catalog
    - Verifying product existence
    """
    logger.info(
        "Received catalog search request", query=query, page_number=page_number, page_size=page_size
    )

    try:
        results = await catalog_service.search_catalog(
            query=query, page_number=page_number, page_size=page_size
        )

        return {
            "success": True,
            "query": query,
            "pagination": {
                "page_number": results.get("pageNumber"),
                "page_size": results.get("pageSize"),
                "total_results": results.get("count"),
                "has_next_page": results.get("hasNextPage"),
            },
            "products": results.get("products", []),
        }

    except Exception as e:
        logger.error("Catalog search failed", query=query, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/catalog/products/{product_id}",
    summary="Get Product Details from Catalog API v2",
    description="Get detailed product information including brand, title, style ID, product attributes, size chart, and eligibility flags.",
    response_model=Dict[str, Any],
)
async def get_catalog_product_details(
    product_id: str,
    catalog_service: StockXCatalogService = Depends(get_catalog_service),
):
    """Get detailed product information from StockX Catalog API v2"""
    logger.info("Received request for catalog product details", product_id=product_id)

    try:
        details = await catalog_service.get_product_details(product_id)
        return {"success": True, "product": details}

    except Exception as e:
        logger.error(
            "Failed to get product details", product_id=product_id, error=str(e), exc_info=True
        )
        raise HTTPException(status_code=404, detail=f"Product not found: {str(e)}")


@router.get(
    "/catalog/products/{product_id}/variants",
    summary="Get Product Variants from Catalog API v2",
    description="Get all variants (sizes) for a product with complete size information, GTINs, and eligibility flags.",
    response_model=Dict[str, Any],
)
async def get_catalog_product_variants(
    product_id: str,
    catalog_service: StockXCatalogService = Depends(get_catalog_service),
):
    """Get all variants (sizes) for a product"""
    logger.info("Received request for catalog product variants", product_id=product_id)

    try:
        variants = await catalog_service.get_product_variants(product_id)
        return {
            "success": True,
            "product_id": product_id,
            "total_variants": len(variants),
            "variants": variants,
        }

    except Exception as e:
        logger.error(
            "Failed to get product variants", product_id=product_id, error=str(e), exc_info=True
        )
        raise HTTPException(status_code=404, detail=f"Variants not found: {str(e)}")


@router.get(
    "/catalog/products/{product_id}/variants/{variant_id}/market-data",
    summary="Get Market Data for Variant from Catalog API v2",
    description="Get real-time market data for a specific variant including lowest ask, highest bid, and StockX pricing recommendations.",
    response_model=Dict[str, Any],
)
async def get_catalog_variant_market_data(
    product_id: str,
    variant_id: str,
    currency_code: str = Query("EUR", description="Currency code (EUR, USD, GBP, etc.)"),
    catalog_service: StockXCatalogService = Depends(get_catalog_service),
):
    """Get market data for a specific variant (size)"""
    logger.info(
        "Received request for variant market data",
        product_id=product_id,
        variant_id=variant_id,
        currency=currency_code,
    )

    try:
        market_data = await catalog_service.get_market_data(
            product_id=product_id, variant_id=variant_id, currency_code=currency_code
        )

        return {
            "success": True,
            "product_id": product_id,
            "variant_id": variant_id,
            "currency": market_data.get("currencyCode"),
            "market_data": {
                "lowest_ask": market_data.get("lowestAskAmount"),
                "highest_bid": market_data.get("highestBidAmount"),
                "sell_faster_price": market_data.get("sellFasterAmount"),
                "earn_more_price": market_data.get("earnMoreAmount"),
                "flex_lowest_ask": market_data.get("flexLowestAskAmount"),
            },
            "full_data": market_data,  # Complete market data for advanced use
        }

    except Exception as e:
        logger.error(
            "Failed to get market data",
            product_id=product_id,
            variant_id=variant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=404, detail=f"Market data not found: {str(e)}")


# ============================================================================
# Legacy Stats Endpoint (Removed - Redundant with Dashboard)
# ============================================================================


# Stats endpoint removed - redundant with Dashboard
async def get_product_stats(
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get product statistics and insights"""
    logger.info("Fetching product statistics")

    try:
        # Get real transaction-based analytics data
        from sqlalchemy import text

        # Get sales analytics from transactions
        sales_query = text(
            """
            SELECT
                COUNT(*) as total_transactions,
                SUM(amount) as total_revenue,
                AVG(amount) as avg_sale_price,
                SUM(net_profit) as total_profit
            FROM sales.order
            WHERE amount IS NOT NULL
        """
        )
        sales_result = await db.execute(sales_query)
        sales_data = sales_result.fetchone()

        # Get top brands with transaction data
        brands_query = text(
            """
            SELECT 
                b.name as brand_name,
                COUNT(t.id) as total_items,
                COUNT(DISTINCT p.id) as total_products,
                AVG(t.amount) as avg_price,
                SUM(t.amount) as total_value
            FROM sales.order t
            JOIN inventory.stock i ON t.inventory_item_id = i.id
            JOIN catalog.product p ON i.product_id = p.id
            LEFT JOIN catalog.brand b ON p.brand_id = b.id
            WHERE t.amount IS NOT NULL AND b.name IS NOT NULL
            GROUP BY b.name
            ORDER BY total_value DESC
            LIMIT 10
        """
        )
        brands_result = await db.execute(brands_query)
        brands_data = [
            {
                "name": row.brand_name,
                "total_products": row.total_products,
                "total_items": row.total_items,
                "avg_price": float(row.avg_price or 0),
                "total_value": float(row.total_value or 0),
            }
            for row in brands_result.fetchall()
        ]

        # Get category data
        categories_query = text(
            """
            SELECT 
                c.name as category_name,
                COUNT(t.id) as item_count,
                AVG(t.amount) as avg_price
            FROM sales.order t
            JOIN inventory.stock i ON t.inventory_item_id = i.id
            JOIN catalog.product p ON i.product_id = p.id
            LEFT JOIN catalog.category c ON p.category_id = c.id
            WHERE t.amount IS NOT NULL AND c.name IS NOT NULL
            GROUP BY c.name
            ORDER BY item_count DESC
            LIMIT 5
        """
        )
        categories_result = await db.execute(categories_query)
        categories_data = [
            {
                "name": row.category_name,
                "item_count": row.item_count,
                "avg_price": float(row.avg_price or 0),
            }
            for row in categories_result.fetchall()
        ]

        # Calculate profit margin
        avg_profit_margin = 0
        if sales_data and sales_data.total_revenue and sales_data.total_profit:
            avg_profit_margin = (
                float(sales_data.total_profit) / float(sales_data.total_revenue)
            ) * 100

        # Get inventory counts for status breakdown
        inventory_summary = await inventory_service.get_detailed_summary()
        inventory_summary if isinstance(inventory_summary, dict) else {}

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_products": sales_data.total_transactions if sales_data else 0,
            "total_inventory_value": float(sales_data.total_revenue or 0) if sales_data else 0.0,
            "total_brands": len(brands_data),
            "avg_profit_margin": avg_profit_margin,
            "top_brands": brands_data,
            "top_categories": categories_data,
            "status_breakdown": {
                "in_stock": 0,
                "sold": sales_data.total_transactions if sales_data else 0,
                "listed": 0,
            },
            "recent_activity": [],  # Can be added later if needed
        }

    except Exception as e:
        logger.error("Failed to fetch product statistics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch product statistics")
