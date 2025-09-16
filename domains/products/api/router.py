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
from domains.inventory.services.inventory_service import InventoryService
from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)


def get_stockx_service(db: AsyncSession = Depends(get_db_session)) -> StockXService:
    return StockXService(db)


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
                        FROM products.products p
                        LEFT JOIN core.brands b ON p.brand_id = b.id
                        WHERE p.id = ANY(:product_ids)
                    """
                    )
                    result = await bg_session.execute(products_query, {"product_ids": product_ids})
                else:
                    # Get all products needing enrichment
                    products_query = text(
                        """
                        SELECT p.id, p.name, p.sku, b.name as brand_name
                        FROM products.products p  
                        LEFT JOIN core.brands b ON p.brand_id = b.id
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
                                UPDATE products.products 
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
            FROM products.products
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
                SUM(sale_price) as total_revenue,
                AVG(sale_price) as avg_sale_price,
                SUM(net_profit) as total_profit
            FROM sales.transactions 
            WHERE sale_price IS NOT NULL
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
                AVG(t.sale_price) as avg_price,
                SUM(t.sale_price) as total_value
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE t.sale_price IS NOT NULL AND b.name IS NOT NULL
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
                AVG(t.sale_price) as avg_price
            FROM sales.transactions t
            JOIN products.inventory i ON t.inventory_id = i.id
            JOIN products.products p ON i.product_id = p.id
            LEFT JOIN core.categories c ON p.category_id = c.id
            WHERE t.sale_price IS NOT NULL AND c.name IS NOT NULL
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
        inventory_summary_dict = inventory_summary if isinstance(inventory_summary, dict) else {}

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
