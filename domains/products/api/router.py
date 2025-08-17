"""
API Router for Product-related endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from shared.database.connection import get_db_session
from domains.inventory.services.inventory_service import InventoryService
from shared.database.models import Product

logger = structlog.get_logger(__name__)

router = APIRouter()

def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)

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
