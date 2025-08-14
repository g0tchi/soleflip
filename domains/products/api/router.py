"""
API Router for Product-related endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from shared.database.connection import get_db_session
from domains.products.services.product_processor import ProductProcessor
from shared.database.models import Product

logger = structlog.get_logger(__name__)

router = APIRouter()

def get_product_processor(db: AsyncSession = Depends(get_db_session)) -> ProductProcessor:
    return ProductProcessor(db)

@router.post(
    "/{product_id}/enrich-from-stockx",
    status_code=202,
    summary="Enrich Product Data from StockX",
    description="Triggers a background task to enrich a product's data using the StockX Catalog API."
)
async def enrich_product(
    product_id: UUID,
    background_tasks: BackgroundTasks,
    product_processor: ProductProcessor = Depends(get_product_processor)
):
    logger.info("Received request to enrich product", product_id=str(product_id))

    # Run the enrichment in the background to provide an immediate response
    background_tasks.add_task(product_processor.enrich_product_from_stockx, product_id)

    return {"message": "Product enrichment has been queued."}
