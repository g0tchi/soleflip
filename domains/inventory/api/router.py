"""
API Router for Inventory-related endpoints
Production-ready CRUD operations for inventory management
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
from uuid import UUID
import structlog

from shared.api.dependencies import (
    get_inventory_service,
    PaginationParams,
    SearchParams,
    validate_inventory_item_id,
    ResponseFormatter,
    ErrorContext
)
from shared.api.responses import (
    InventoryItemResponse,
    InventorySummaryResponse,
    PaginatedResponse,
    SuccessResponse,
    ResponseBuilder
)
from domains.inventory.services.inventory_service import InventoryService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("",
    response_model=PaginatedResponse[InventoryItemResponse], 
    summary="Get All Inventory Items (Legacy)",
    description="Legacy endpoint that redirects to /items. Retrieve all inventory items with optional filtering and pagination"
)
async def get_inventory_items_legacy(
    pagination: PaginationParams = Depends(),
    search: SearchParams = Depends(),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Legacy inventory endpoint - redirects to /items"""
    return await get_inventory_items(pagination, search, inventory_service)


@router.get("/items", 
    response_model=PaginatedResponse[InventoryItemResponse],
    summary="Get All Inventory Items",
    description="Retrieve all inventory items with optional filtering and pagination"
)
async def get_inventory_items(
    pagination: PaginationParams = Depends(),
    search: SearchParams = Depends(),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Get all inventory items with optional filtering"""
    logger.info(
        "Fetching inventory items",
        pagination=pagination.to_dict(),
        search=search.to_dict() if search.has_filters() else None
    )
    
    try:
        # Get items with total count
        items, total = await inventory_service.get_items_paginated(
            skip=pagination.skip,
            limit=pagination.limit,
            filters=search.to_dict()
        )
        
        return ResponseBuilder.paginated(
            items=items,
            skip=pagination.skip,
            limit=pagination.limit,
            total=total,
            filters=search.to_dict() if search.has_filters() else None
        )
    except Exception as e:
        error_context = ErrorContext("fetch", "inventory items")
        raise error_context.create_error_response(e)


@router.get("/items/{item_id}", 
    response_model=InventoryItemResponse,
    summary="Get Inventory Item",
    description="Retrieve a specific inventory item by ID"
)
async def get_inventory_item(
    item_id: UUID = Depends(validate_inventory_item_id),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Get specific inventory item by ID"""
    logger.info("Fetching inventory item", item_id=str(item_id))
    
    try:
        item = await inventory_service.get_item_detailed(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Inventory item with ID {item_id} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        error_context = ErrorContext("fetch", "inventory item")
        raise error_context.create_error_response(e)


@router.post("/items/{item_id}/sync-from-stockx",
    response_model=SuccessResponse,
    status_code=202,
    summary="Sync Inventory Item from StockX",
    description="Triggers background sync of inventory item data from StockX API"
)
async def sync_inventory_item_from_stockx(
    item_id: UUID = Depends(validate_inventory_item_id),
    background_tasks: BackgroundTasks = None,
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Sync specific inventory item from StockX"""
    logger.info("Received request to sync inventory item from StockX", item_id=str(item_id))
    
    # Verify item exists
    try:
        item = await inventory_service.get_item_detailed(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Inventory item with ID {item_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        error_context = ErrorContext("verify", "inventory item")
        raise error_context.create_error_response(e)
    
    async def run_sync_task(item_id: UUID):
        from shared.database.connection import db_manager
        async with db_manager.get_session() as bg_session:
            try:
                bg_inventory_service = InventoryService(bg_session)
                await bg_inventory_service.sync_item_from_stockx(item_id)
                logger.info("Inventory item sync completed", item_id=str(item_id))
            except Exception as e:
                logger.error("Inventory item sync failed", item_id=str(item_id), error=str(e), exc_info=True)
    
    if background_tasks:
        background_tasks.add_task(run_sync_task, item_id)
    
    return ResponseBuilder.success(
        message=f"Inventory item {item_id} synchronization has been queued",
        data={"item_id": str(item_id), "status": "queued"}
    )


@router.get("/summary",
    response_model=InventorySummaryResponse,
    summary="Get Inventory Summary",
    description="Get high-level inventory statistics and summary"
)
async def get_inventory_summary(
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Get inventory summary statistics"""
    logger.info("Fetching inventory summary")
    
    try:
        summary = await inventory_service.get_detailed_summary()
        return summary
    except Exception as e:
        error_context = ErrorContext("fetch", "inventory summary")
        raise error_context.create_error_response(e)
