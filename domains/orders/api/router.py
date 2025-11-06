"""
Orders API Router Module
========================

This module provides REST API endpoints for managing marketplace orders from StockX and other platforms.

Endpoints:
    - GET /active: Fetch active orders from StockX marketplace
    - GET /stockx-history: Fetch historical orders within a date range

Key Features:
    - Real-time order status tracking
    - Date range filtering for historical data
    - Multiple filter options (status, product, variant, inventory type)
    - Pagination support
    - StockX webhook integration ready

Order Lifecycle:
    An order progresses through multiple states:
    1. CREATED: Initial order creation
    2. SHIPPED: Product shipped to StockX
    3. AUTHENTICATING: StockX verifying authenticity
    4. COMPLETED: Product authenticated and seller paid
    5. CANCELED: Order canceled

Filtering Options:
    - orderStatus: Filter by specific order status
    - productId: Filter by StockX product ID
    - variantId: Filter by specific size/variant
    - inventoryTypes: STANDARD or DIRECT inventory
    - initiatedShipmentDisplayIds: Filter by shipment IDs
    - sortOrder: Sort results (default: CREATEDAT)

Authentication:
    All endpoints require valid JWT token authentication.
    See shared/auth/ for authentication details.

Example Requests:
    ```
    # Get all active orders
    GET /orders/active

    # Get active orders for specific product
    GET /orders/active?productId=abc123

    # Get completed orders for date range
    GET /orders/stockx-history?fromDate=2025-01-01&toDate=2025-01-31&orderStatus=COMPLETED
    ```

Response Format:
    Returns list of order objects with structure:
    ```json
    [
        {
            "orderId": "ORDER123",
            "orderNumber": "SO-123456",
            "status": "COMPLETED",
            "productId": "abc123",
            "variantId": "variant-456",
            "price": {"amount": "150.00", "currencyCode": "USD"},
            "createdAt": "2025-01-15T10:30:00Z",
            ...
        }
    ]
    ```

Error Handling:
    - 400: Invalid query parameters
    - 401: Unauthorized (missing/invalid token)
    - 500: Internal server error

Dependencies:
    - StockXService: For fetching orders from StockX API
    - fastapi: Web framework
    - structlog: Structured logging

Related Modules:
    - domains.integration.services.stockx_service: StockX API client
    - domains.orders.services: Order processing services
    - shared.auth: Authentication and authorization

See Also:
    - docs/api/endpoints/orders.md: Detailed API documentation
    - context/api_audit/: StockX API audit reports
"""

from datetime import date
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from domains.integration.api.webhooks import get_stockx_service
from domains.integration.services.stockx_service import StockXService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_orders(
    orderStatus: Optional[str] = Query(None, description="Filter by order status."),
    productId: Optional[str] = Query(None, description="Filter by product ID."),
    variantId: Optional[str] = Query(None, description="Filter by variant ID."),
    sortOrder: Optional[str] = Query("CREATEDAT", description="Sort order for the results."),
    inventoryTypes: Optional[str] = Query(
        None, description="Comma-separated list of inventory types."
    ),
    initiatedShipmentDisplayIds: Optional[str] = Query(
        None, description="Filter by shipment display IDs."
    ),
    stockx_service: StockXService = Depends(get_stockx_service),
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
            initiatedShipmentDisplayIds=initiatedShipmentDisplayIds,
        )
        return active_orders
    except Exception:
        logger.exception("Failed to get active orders")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred. See logs for details."
        )


@router.get("/stockx-history", response_model=List[Dict[str, Any]])
async def get_historical_orders(
    fromDate: date,
    toDate: date,
    orderStatus: Optional[str] = Query(
        None, description="Filter by order status. e.g. COMPLETED, CANCELED"
    ),
    productId: Optional[str] = Query(None, description="Filter by product ID."),
    variantId: Optional[str] = Query(None, description="Filter by variant ID."),
    inventoryTypes: Optional[str] = Query(
        None, description="Comma-separated list of inventory types. e.g. STANDARD,FLEX"
    ),
    initiatedShipmentDisplayIds: Optional[str] = Query(
        None, description="Filter by shipment display IDs."
    ),
    stockx_service: StockXService = Depends(get_stockx_service),
):
    """
    Get all historical orders from the StockX marketplace, with optional filters.
    """
    logger.info("Historical orders endpoint called", from_date=fromDate, to_date=toDate)

    try:
        historical_orders = await stockx_service.get_historical_orders(
            from_date=fromDate,
            to_date=toDate,
            order_status=orderStatus,
            product_id=productId,
            variant_id=variantId,
            inventory_types=inventoryTypes,
            initiated_shipment_display_ids=initiatedShipmentDisplayIds,
        )
        return historical_orders
    except Exception:
        logger.exception("Failed to get historical orders")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred. See logs for details."
        )
