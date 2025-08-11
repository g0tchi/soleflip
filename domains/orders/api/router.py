from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional, Dict, Any
import structlog

from domains.integration.services.stockx_service import stockx_service

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_orders(
    orderStatus: Optional[str] = Query(None, description="Filter by order status."),
    productId: Optional[str] = Query(None, description="Filter by product ID."),
    variantId: Optional[str] = Query(None, description="Filter by variant ID."),
    sortOrder: Optional[str] = Query("CREATEDAT", description="Sort order for the results."),
    inventoryTypes: Optional[str] = Query(None, description="Comma-separated list of inventory types."),
    initiatedShipmentDisplayIds: Optional[str] = Query(None, description="Filter by shipment display IDs.")
):
    """
    Get all active orders from the StockX marketplace.

    An order is considered active from the time it was created to the time the product
    was received and authenticated by StockX and the seller is paid out.
    """
    logger.info("Active orders endpoint called", **locals())

    try:
        # Pass all query parameters to the service method
        active_orders = await stockx_service.get_active_orders(
            orderStatus=orderStatus,
            productId=productId,
            variantId=variantId,
            sortOrder=sortOrder,
            inventoryTypes=inventoryTypes,
            initiatedShipmentDisplayIds=initiatedShipmentDisplayIds
        )
        return active_orders
    except Exception as e:
        logger.error("Failed to get active orders", error=str(e))
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
