"""
API Router for Product-related endpoints
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
import structlog

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from domains.inventory.services.inventory_service import InventoryService
from domains.integration.services.stockx_service import StockXService
from shared.database.models import Product

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
    description="Triggers a background task to sync all product variants from StockX, creating or updating inventory items."
)
async def sync_product_variants(
    product_id: UUID,
    background_tasks: BackgroundTasks
):
    logger.info("Received request to sync product variants from StockX", product_id=str(product_id))

    async def run_sync_task(product_id: UUID):
        from shared.database.connection import db_manager
        async with db_manager.get_session() as bg_session:
            try:
                inventory_service = InventoryService(bg_session)
                await inventory_service.sync_inventory_from_stockx(product_id)
            except Exception as e:
                logger.error("StockX variant sync background task failed", product_id=str(product_id), error=str(e), exc_info=True)

    background_tasks.add_task(run_sync_task, product_id)

    return {"message": "Product variant synchronization has been queued."}


@router.get(
    "/{product_id}/stockx-details",
    summary="Get Product Details from StockX",
    description="Fetches real-time product details for a given product ID directly from the StockX Catalog API.",
    response_model=Dict[str, Any]
)
async def get_stockx_product_details(
    product_id: str,
    stockx_service: StockXService = Depends(get_stockx_service)
):
    logger.info("Received request to fetch product details from StockX", product_id=product_id)

    details = await stockx_service.get_product_details(product_id)

    if not details:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID '{product_id}' not found on StockX."
        )

    return details


@router.get(
    "/search-stockx",
    summary="Search for Products on StockX",
    description="Performs a search against the StockX Catalog API using a query string.",
    response_model=Dict[str, Any]
)
async def search_stockx_products(
    query: str = Query(..., min_length=1, max_length=100, description="Keyword, GTIN, or Style ID to search for."),
    page: int = Query(1, alias="pageNumber", ge=1, description="Requested page number."),
    page_size: int = Query(10, alias="pageSize", ge=1, le=50, description="Number of products to return per page."),
    stockx_service: StockXService = Depends(get_stockx_service)
):
    logger.info("Received request to search StockX catalog", query=query, page=page, page_size=page_size)

    search_results = await stockx_service.search_stockx_catalog(
        query=query, page=page, page_size=page_size
    )

    if search_results is None:
        # This can happen if there was an HTTP error in the service
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve search results from StockX."
        )

    return search_results


@router.get(
    "/{product_id}/stockx-market-data",
    summary="Get Market Data from StockX",
    description="Fetches real-time market data (highest bid, lowest ask) for all variants of a product from the StockX API.",
    response_model=List[Dict[str, Any]]
)
async def get_stockx_market_data(
    product_id: str,
    currency: Optional[str] = Query(None, alias="currencyCode", description="ISO 4217 currency code."),
    stockx_service: StockXService = Depends(get_stockx_service)
):
    logger.info("Received request to fetch market data from StockX", product_id=product_id, currency=currency)

    market_data = await stockx_service.get_market_data_from_stockx(
        product_id=product_id, currency_code=currency
    )

    if market_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID '{product_id}' not found on StockX."
        )

    return market_data
