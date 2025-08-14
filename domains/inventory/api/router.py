"""
API Router for Inventory-related endpoints
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from shared.database.connection import get_db_session
from domains.inventory.services.inventory_service import InventoryService

logger = structlog.get_logger(__name__)

router = APIRouter()

def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)

@router.post(
    "/{item_id}/enrich-from-stockx",
    status_code=202,
    summary="Enrich Inventory Item Data from StockX",
    description="Triggers a background task to enrich an inventory item's data using the StockX Catalog API."
)
async def enrich_inventory_item(
    item_id: UUID,
    background_tasks: BackgroundTasks,
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    logger.info("Received request to enrich inventory item", item_id=str(item_id))

    background_tasks.add_task(inventory_service.enrich_inventory_item_from_stockx, item_id)

    return {"message": "Inventory item enrichment has been queued."}
