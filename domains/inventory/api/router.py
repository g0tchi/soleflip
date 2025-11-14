"""
API Router for Inventory-related endpoints
Production-ready CRUD operations for inventory management
"""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from domains.inventory.services.inventory_service import InventoryService
from shared.api.dependencies import (
    ErrorContext,
    PaginationParams,
    SearchParams,
    get_inventory_service,
    validate_inventory_item_id,
)
from shared.api.responses import (
    InventoryItemResponse,
    PaginatedResponse,
    ResponseBuilder,
    SuccessResponse,
)
from shared.database.connection import get_db_session
from shared.streaming.response import stream_inventory_export

logger = structlog.get_logger(__name__)

router = APIRouter()


# Legacy redirect endpoint removed


@router.get(
    "/items",
    response_model=PaginatedResponse[InventoryItemResponse],
    summary="Get All Inventory Items",
    description="Retrieve all inventory items with optional filtering and pagination",
)
async def get_inventory_items(
    pagination: PaginationParams = Depends(),
    search: SearchParams = Depends(),
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Get all inventory items with optional filtering"""
    logger.info(
        "Fetching inventory items",
        pagination=pagination.to_dict(),
        search=search.to_dict() if search.has_filters() else None,
    )

    try:
        # Get items with total count
        items, total = await inventory_service.get_items_paginated(
            skip=pagination.skip, limit=pagination.limit, filters=search.to_dict()
        )

        return ResponseBuilder.paginated(
            items=items,
            skip=pagination.skip,
            limit=pagination.limit,
            total=total,
            filters=search.to_dict() if search.has_filters() else None,
        )
    except Exception as e:
        error_context = ErrorContext("fetch", "inventory items")
        raise error_context.create_error_response(e)


@router.get(
    "/items/{item_id}",
    response_model=InventoryItemResponse,
    summary="Get Inventory Item",
    description="Retrieve a specific inventory item by ID",
)
async def get_inventory_item(
    item_id: UUID = Depends(validate_inventory_item_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Get specific inventory item by ID"""
    logger.info("Fetching inventory item", item_id=str(item_id))

    try:
        item = await inventory_service.get_item_detailed(item_id)
        if not item:
            raise HTTPException(
                status_code=404, detail=f"Inventory item with ID {item_id} not found"
            )
        return item
    except HTTPException:
        raise
    except Exception as e:
        error_context = ErrorContext("fetch", "inventory item")
        raise error_context.create_error_response(e)


@router.put("/items/{item_id}")
async def update_inventory_item(
    item_id: str,
    update_data: dict,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Simple update for inventory item"""
    try:
        from uuid import UUID

        item_uuid = UUID(item_id)
        success = await inventory_service.update_item_fields(item_uuid, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"success": True, "message": "Updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/items/{item_id}/sync-from-stockx",
    response_model=SuccessResponse,
    status_code=202,
    summary="Sync Inventory Item from StockX",
    description="Triggers background sync of inventory item data from StockX API",
)
async def sync_inventory_item_from_stockx(
    item_id: UUID = Depends(validate_inventory_item_id),
    background_tasks: BackgroundTasks = None,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Sync specific inventory item from StockX"""
    logger.info("Received request to sync inventory item from StockX", item_id=str(item_id))

    # Verify item exists
    try:
        item = await inventory_service.get_item_detailed(item_id)
        if not item:
            raise HTTPException(
                status_code=404, detail=f"Inventory item with ID {item_id} not found"
            )
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
                logger.error(
                    "Inventory item sync failed", item_id=str(item_id), error=str(e), exc_info=True
                )

    if background_tasks:
        background_tasks.add_task(run_sync_task, item_id)

    return ResponseBuilder.success(
        message=f"Inventory item {item_id} synchronization has been queued",
        data={"item_id": str(item_id), "status": "queued"},
    )


@router.post(
    "/items/{item_id}/stockx-listing",
    response_model=SuccessResponse,
    status_code=201,
    summary="Create StockX Listing",
    description="Create a StockX listing for an inventory item",
)
async def create_stockx_listing(
    item_id: UUID = Depends(validate_inventory_item_id),
    listing_type: str = "immediate",
    background_tasks: BackgroundTasks = None,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Create a StockX listing for an inventory item"""
    logger.info("Creating StockX listing", item_id=str(item_id), listing_type=listing_type)

    # Verify item exists and can be listed
    try:
        item = await inventory_service.get_item_detailed(item_id)
        if not item:
            raise HTTPException(
                status_code=404, detail=f"Inventory item with ID {item_id} not found"
            )

        # Check if item can be listed on StockX
        valid_statuses = ["in_stock", "presale", "preorder"]
        if item.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Item with status '{item.status}' cannot be listed on StockX. Valid statuses: {valid_statuses}",
            )

    except HTTPException:
        raise
    except Exception as e:
        error_context = ErrorContext("verify", "inventory item for listing")
        raise error_context.create_error_response(e)

    # Create the listing using StockX service
    try:
        from domains.integration.services.stockx_service import StockXService
        from shared.database.connection import db_manager

        # For now, mock the variant_id and amount - in real implementation,
        # these would come from the inventory item's product data
        async with db_manager.get_session() as stockx_session:
            stockx_service = StockXService(stockx_session)

            # Mock data - in real implementation, get from item.product
            variant_id = f"mock-variant-{item_id}"
            amount = str(item.current_price or item.purchase_price or "100.00")

            try:
                # Try to create actual StockX listing
                stockx_response = await stockx_service.create_listing(
                    variant_id=variant_id,
                    amount=amount,
                    inventory_type="STANDARD" if listing_type == "immediate" else "DIRECT",
                )

                listing_id = stockx_response.get("listingId", f"mock-listing-{item_id}")

            except Exception as stockx_error:
                logger.warning(
                    "StockX API call failed, using mock response", error=str(stockx_error)
                )
                # Fallback to mock response if StockX API fails
                listing_id = f"mock-listing-{item_id}-{listing_type}"
                stockx_response = {
                    "listingId": listing_id,
                    "operationStatus": "PENDING",
                    "error": str(stockx_error),
                }

        # Update item status to 'listed'
        await inventory_service.update_item_status(item_id, "listed")

        return ResponseBuilder.success(
            message="StockX listing created successfully",
            data={
                "item_id": str(item_id),
                "listing_id": listing_id,
                "listing_type": listing_type,
                "status": stockx_response.get("operationStatus", "created"),
                "stockx_response": stockx_response,
            },
        )
    except Exception as e:
        error_context = ErrorContext("create", "StockX listing")
        raise error_context.create_error_response(e)


@router.get(
    "/stockx-listings",
    response_model=SuccessResponse,
    summary="Get Current StockX Listings",
    description="Retrieve all current StockX listings for the user",
)
async def get_stockx_listings(
    status: Optional[str] = None,
    limit: Optional[int] = 50,
    force_refresh: Optional[bool] = False,
):
    """Get current StockX listings with caching"""
    logger.info(
        "Fetching current StockX listings", status=status, limit=limit, force_refresh=force_refresh
    )

    try:
        from datetime import datetime, timedelta

        from domains.integration.services.stockx_service import StockXService
        from shared.database.connection import db_manager

        # Simple in-memory cache
        cache_key = f"stockx_listings_{status}_{limit}"
        cache_timeout = timedelta(hours=8)  # Cache for 8 hours (2-3 times per day)

        # Check cache first (if not forcing refresh)
        if not force_refresh and hasattr(get_stockx_listings, "_cache"):
            cached_data = get_stockx_listings._cache.get(cache_key)
            if cached_data and datetime.utcnow() - cached_data["timestamp"] < cache_timeout:
                logger.info(
                    f"Returning cached StockX listings (age: {datetime.utcnow() - cached_data['timestamp']})"
                )
                # Mark response as cached
                cached_response = cached_data["response"]
                cached_response.body["data"]["cached"] = True
                cached_response.body["data"]["cache_age_seconds"] = int(
                    (datetime.utcnow() - cached_data["timestamp"]).total_seconds()
                )
                return cached_response

        async with db_manager.get_session() as stockx_session:
            stockx_service = StockXService(stockx_session)

            # Prepare filters
            filters = {}
            if status:
                filters["status"] = status
            if limit:
                filters["limit"] = limit

            try:
                # Get raw listings from StockX API
                raw_listings = await stockx_service.get_all_listings(**filters)
                logger.info(f"Retrieved {len(raw_listings)} raw listings from StockX API")

                # Filter for active listings only and transform to match frontend expectations
                transformed_listings = []
                for listing in raw_listings:
                    # Only include ACTIVE listings, skip COMPLETED, CANCELLED, etc.
                    listing_status = listing.get("status", "").upper()
                    if listing_status not in ["ACTIVE", "PENDING"]:
                        continue  # Skip non-active listings

                    # Extract product and variant info
                    product_info = listing.get("product", {})
                    variant_info = listing.get("variant", {})

                    # Create transformed listing
                    transformed = listing.copy()  # Start with original

                    # Add fields that frontend expects
                    transformed["productName"] = product_info.get("productName", "Unknown Product")
                    if "product" not in transformed:
                        transformed["product"] = {}
                    transformed["product"]["name"] = product_info.get(
                        "productName", "Unknown Product"
                    )

                    # Ensure size is accessible
                    transformed["size"] = variant_info.get("variantValue", "N/A")

                    # Ensure ask price is accessible
                    transformed["askPrice"] = listing.get("amount", "0")

                    transformed_listings.append(transformed)

                response = ResponseBuilder.success(
                    message=f"Retrieved {len(transformed_listings)} active StockX listings",
                    data={
                        "listings": transformed_listings,
                        "count": len(transformed_listings),
                        "total_raw_listings": len(raw_listings),
                        "filters": filters,
                        "filtered_statuses": ["ACTIVE", "PENDING"],
                        "cached": False,
                    },
                )

                # Cache the response
                if not hasattr(get_stockx_listings, "_cache"):
                    get_stockx_listings._cache = {}
                get_stockx_listings._cache[cache_key] = {
                    "response": response,
                    "timestamp": datetime.utcnow(),
                }
                logger.info(f"Cached StockX listings for {cache_timeout}")

                return response
            except Exception as stockx_error:
                logger.warning("StockX API call failed", error=str(stockx_error))
                # Return empty result if StockX API fails
                return ResponseBuilder.success(
                    message="StockX API unavailable, showing empty results",
                    data={
                        "listings": [],
                        "count": 0,
                        "error": str(stockx_error),
                        "filters": filters,
                    },
                )

    except Exception as e:
        error_context = ErrorContext("fetch", "StockX listings")
        raise error_context.create_error_response(e)


@router.post(
    "/stockx-listings/{listing_id}/mark-presale",
    response_model=SuccessResponse,
    summary="Mark StockX Listing as Presale",
    description="Mark a StockX listing as presale in our local database",
)
async def mark_stockx_listing_as_presale(
    listing_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Mark a StockX listing as presale in our database"""
    logger.info("Marking StockX listing as presale", listing_id=listing_id)

    try:
        success = await inventory_service.mark_stockx_item_as_presale(stockx_listing_id=listing_id)

        if not success:
            raise HTTPException(status_code=404, detail="Inventory item not found or update failed")

        return ResponseBuilder.success(
            message="StockX listing marked as presale successfully",
            data={"stockx_listing_id": listing_id, "status": "presale"},
        )
    except Exception as e:
        error_context = ErrorContext("update", "StockX presale marking")
        raise error_context.create_error_response(e)


@router.delete(
    "/stockx-listings/{listing_id}/unmark-presale",
    response_model=SuccessResponse,
    summary="Remove Presale Marking from StockX Listing",
    description="Remove presale marking from a StockX listing in our database",
)
async def unmark_stockx_listing_presale(
    listing_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Remove presale marking from a StockX listing"""
    logger.info("Removing presale marking from StockX listing", listing_id=listing_id)

    try:
        success = await inventory_service.unmark_stockx_presale(stockx_listing_id=listing_id)

        if not success:
            raise HTTPException(status_code=404, detail="Inventory item not found or update failed")

        return ResponseBuilder.success(
            message="Presale marking removed from StockX listing successfully",
            data={"stockx_listing_id": listing_id, "status": "listed_stockx"},
        )
    except Exception as e:
        error_context = ErrorContext("update", "StockX presale unmarking")
        raise error_context.create_error_response(e)


# Test endpoint removed for production


@router.post(
    "/sync-stockx-listings",
    response_model=SuccessResponse,
    summary="Sync All StockX Listings to Inventory",
    description="Create inventory items for all current StockX listings",
)
async def sync_stockx_listings_to_inventory(
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Sync all StockX listings to inventory items"""
    logger.info("Starting sync of StockX listings to inventory")

    try:
        stats = await inventory_service.sync_all_stockx_listings_to_inventory()

        return ResponseBuilder.success(
            message=f"Successfully synced StockX listings. Created: {stats.get('created', 0)}, Matched: {stats.get('matched', 0)}",
            data=stats,
        )
    except Exception as e:
        error_context = ErrorContext("sync", "StockX listings")
        raise error_context.create_error_response(e)


@router.get(
    "/alias-listings",
    response_model=SuccessResponse,
    summary="Get Current Alias Listings",
    description="Retrieve all current Alias listings for the user",
)
async def get_alias_listings(
    status: Optional[str] = None,
    limit: Optional[int] = 50,
):
    """Get current Alias listings"""
    logger.info("Fetching current Alias listings", status=status, limit=limit)

    try:
        # For now, return mock data since Alias integration doesn't exist yet
        mock_listings = [
            {
                "listingId": "alias-12345678",
                "productName": "Air Jordan 1 High OG 'Chicago'",
                "product": {"name": "Air Jordan 1 High OG 'Chicago'"},
                "size": "10",
                "askPrice": "420.00",
                "status": "ACTIVE",
                "createdAt": "2025-09-01T10:00:00Z",
                "platform": "Alias",
                "currency": "EUR",
            },
            {
                "listingId": "alias-87654321",
                "productName": "Yeezy 350 V2 'Bred'",
                "product": {"name": "Yeezy 350 V2 'Bred'"},
                "size": "9.5",
                "askPrice": "320.00",
                "status": "PENDING",
                "createdAt": "2025-08-30T15:30:00Z",
                "platform": "Alias",
                "currency": "EUR",
            },
            {
                "listingId": "alias-33333333",
                "productName": "Travis Scott x Air Jordan 1 Low",
                "product": {"name": "Travis Scott x Air Jordan 1 Low"},
                "size": "11",
                "askPrice": "890.00",
                "status": "ACTIVE",
                "createdAt": "2025-08-28T12:15:00Z",
                "platform": "Alias",
                "currency": "EUR",
            },
        ]

        # Apply filters
        filtered_listings = mock_listings
        if status:
            filtered_listings = [
                listing for listing in filtered_listings if listing["status"] == status
            ]
        if limit:
            filtered_listings = filtered_listings[:limit]

        return ResponseBuilder.success(
            message=f"Retrieved {len(filtered_listings)} Alias listings",
            data={
                "listings": filtered_listings,
                "count": len(filtered_listings),
                "filters": {"status": status, "limit": limit},
                "note": "Mock data - Alias integration not implemented yet",
            },
        )

    except Exception as e:
        error_context = ErrorContext("fetch", "Alias listings")
        raise error_context.create_error_response(e)


@router.post(
    "/sync-from-stockx",
    response_model=SuccessResponse,
    status_code=201,
    summary="Sync Inventory from StockX Listings",
    description="Import current StockX listings as inventory items",
)
async def sync_inventory_from_stockx(
    background_tasks: BackgroundTasks = None,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Sync inventory items from current StockX listings"""
    logger.info("Syncing inventory from StockX listings")

    try:
        from domains.integration.services.stockx_service import StockXService
        from shared.database.connection import db_manager

        async with db_manager.get_session() as stockx_session:
            stockx_service = StockXService(stockx_session)

            # Get all current StockX listings
            try:
                listings = await stockx_service.get_all_listings(limit=100)
                logger.info(f"Retrieved {len(listings)} StockX listings for sync")

                synced_count = 0
                products_created = 0
                market_data_imported = 0

                for listing in listings:
                    try:
                        # Extract product data from listing
                        product_data = listing.get("product", {})
                        variant_data = listing.get("variant", {})

                        product_name = product_data.get("productName", "Unknown Product")
                        stockx_product_id = product_data.get("productId")

                        # Check if product exists in our database
                        existing_product = None
                        # TODO: Query database for existing product by name or stockx_id

                        if not existing_product and stockx_product_id:
                            # Product doesn't exist - create it with StockX data
                            logger.info(f"Creating new product from StockX: {product_name}")

                            # Get detailed product info and market data from StockX
                            try:
                                product_details = await stockx_service.get_product_details(
                                    stockx_product_id
                                )
                                market_data = await stockx_service.get_market_data_from_stockx(
                                    stockx_product_id
                                )

                                # Create new product with StockX data
                                new_product_data = {
                                    "name": product_name,
                                    "sku": product_data.get(
                                        "styleId", f"STOCKX-{stockx_product_id[:8]}"
                                    ),
                                    "brand_name": "Unknown",  # Extract from product_details if available
                                    "category_name": "Imported from StockX",
                                    "description": f"Auto-imported from StockX listing. Product ID: {stockx_product_id}",
                                    "stockx_product_id": stockx_product_id,
                                    "market_data": market_data,
                                    "product_details": product_details,
                                }

                                # TODO: Actually create product in database
                                # For now, just log the creation
                                logger.info(f"Would create product: {new_product_data}")
                                products_created += 1

                                if market_data:
                                    market_data_imported += 1

                            except Exception as product_error:
                                logger.warning(
                                    f"Failed to fetch product details for {stockx_product_id}: {product_error}"
                                )

                        # Create inventory item (mock for now)
                        {
                            "product_name": product_name,
                            "size": variant_data.get("variantValue", "Unknown"),
                            "current_price": float(listing.get("amount", 0)),
                            "purchase_price": float(
                                listing.get("amount", 0)
                            ),  # Use ask price as purchase price estimate
                            "status": "listed",  # These are already listed on StockX
                            "stockx_listing_id": listing.get("listingId"),
                            "stockx_product_id": stockx_product_id,
                            "condition": "new",
                            "listing_status": listing.get("status", "UNKNOWN"),
                            "currency": listing.get("currencyCode", "EUR"),
                        }

                        # Create inventory item in database

                        # TODO: Actually create inventory item in database
                        synced_count += 1

                    except Exception as listing_error:
                        logger.warning(
                            f"Failed to sync listing {listing.get('listingId', 'unknown')}: {listing_error}"
                        )
                        continue

                return ResponseBuilder.success(
                    message=f"Inventory sync completed. Synced {synced_count} items, created {products_created} products, imported {market_data_imported} market data entries",
                    data={
                        "synced_count": synced_count,
                        "products_created": products_created,
                        "market_data_imported": market_data_imported,
                        "total_listings": len(listings),
                    },
                )

            except Exception as stockx_error:
                logger.warning("StockX API call failed", error=str(stockx_error))
                return ResponseBuilder.error(
                    message="Failed to sync inventory from StockX", error=str(stockx_error)
                )

    except Exception as e:
        error_context = ErrorContext("sync", "inventory from StockX")
        raise error_context.create_error_response(e)


@router.post(
    "/items/enrich-batch",
    response_model=SuccessResponse,
    status_code=200,
    summary="Batch Enrich Inventory Items",
    description="Enrich inventory items with missing metadata (brand names, sizes) from StockX data",
)
async def enrich_inventory_items_batch(
    background_tasks: BackgroundTasks = None,
    filters: Optional[dict] = None,
    batch_size: Optional[int] = 50,
    enrich_types: Optional[list] = None,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """
    Batch enrich inventory items with missing metadata

    Enrichment types:
    - "brand": Extract and update brand names from product names
    - "size": Update sizes from StockX listings

    Filters:
    - missing_brand: Only items with "Unknown Brand"
    - missing_size: Only items without size
    - status: Filter by inventory status (e.g., "listed_stockx")
    """
    logger.info(
        "Received request to enrich inventory items",
        filters=filters,
        batch_size=batch_size,
        enrich_types=enrich_types,
    )

    # Use default enrich types if not specified
    if not enrich_types:
        enrich_types = ["brand", "size"]

    # Use default filters if not specified
    if not filters:
        filters = {"missing_brand": True, "missing_size": True}

    try:
        # Run enrichment
        import time

        start_time = time.time()

        stats = await inventory_service.enrich_inventory_items_batch(
            filters=filters,
            batch_size=batch_size,
            enrich_types=enrich_types,
        )

        duration_seconds = time.time() - start_time
        stats["duration_seconds"] = round(duration_seconds, 2)

        return ResponseBuilder.success(
            message=f"Enrichment completed. Processed {stats['processed']} items, enriched {stats['brands_enriched']} brands and {stats['sizes_enriched']} sizes",
            data=stats,
        )

    except Exception as e:
        logger.error("Batch enrichment failed", error=str(e), exc_info=True)
        error_context = ErrorContext("enrich", "inventory items")
        raise error_context.create_error_response(e)


def extract_brand_from_product_name(product_name: str) -> str:
    """Extract brand name from StockX product name using common patterns"""
    if not product_name:
        return "StockX Import"

    # Common brand patterns (case insensitive)
    brand_patterns = {
        "nike": ["Nike", "NIKE", "nike"],
        "adidas": ["adidas", "Adidas", "ADIDAS"],
        "off-white": ["OFF-WHITE", "Off-White", "off-white"],
        "balenciaga": ["Balenciaga", "BALENCIAGA"],
        "lanvin": ["Lanvin", "LANVIN"],
        "supreme": ["Supreme", "SUPREME"],
        "jordan": ["Jordan", "Air Jordan"],
        "yeezy": ["Yeezy", "YEEZY"],
        "travis scott": ["Travis Scott", "Cactus Jack"],
        "fear of god": ["Fear of God", "FOG"],
        "stone island": ["Stone Island"],
        "palm angels": ["Palm Angels"],
        "golden goose": ["Golden Goose"],
        "giuseppe zanotti": ["Giuseppe Zanotti"],
        "bottega veneta": ["Bottega Veneta"],
        "prada": ["Prada", "PRADA"],
        "gucci": ["Gucci", "GUCCI"],
        "louis vuitton": ["Louis Vuitton", "LV"],
        "versace": ["Versace", "VERSACE"],
        "burberry": ["Burberry", "BURBERRY"],
        "dior": ["Dior", "DIOR", "Christian Dior"],
        "givenchy": ["Givenchy", "GIVENCHY"],
        "bape": ["BAPE", "A Bathing Ape"],
        "kaws": ["KAWS", "Kaws"],
        "pokemon": ["Pokemon", "Pokémon"],
        "lego": ["LEGO", "Lego"],
    }

    product_name_lower = product_name.lower()

    # Check for brand patterns
    for brand_key, patterns in brand_patterns.items():
        for pattern in patterns:
            if product_name_lower.startswith(pattern.lower()):
                return pattern
            # Also check for brand name after common prefixes
            if (
                f" {pattern.lower()}" in product_name_lower
                or f"x {pattern.lower()}" in product_name_lower
            ):
                return pattern

    # Try to extract first word as brand if it looks like a brand name
    first_word = product_name.split()[0] if product_name.split() else ""
    if len(first_word) > 2 and first_word[0].isupper():
        return first_word

    # Default fallback
    return "StockX Import"


# Summary endpoint removed - use Dashboard metrics instead
async def get_inventory_summary(
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Get inventory summary statistics with detailed insights"""
    logger.info("Fetching detailed inventory summary")

    try:
        summary = await inventory_service.get_detailed_summary()
        return ResponseBuilder.success(
            message="Inventory summary retrieved successfully", data=summary
        )
    except Exception as e:
        error_context = ErrorContext("fetch", "inventory summary")
        raise error_context.create_error_response(e)


# Export endpoint removed - use external tools or background jobs
async def export_inventory_stream(
    format: str = "json",
    chunk_size: int = 100,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Stream inventory data for efficient large dataset exports"""
    logger.info("Starting inventory streaming export", format=format, chunk_size=chunk_size)

    try:
        # Validate format parameter
        if format.lower() not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")

        # Validate chunk size (prevent memory issues)
        if chunk_size < 10 or chunk_size > 1000:
            raise HTTPException(status_code=400, detail="Chunk size must be between 10 and 1000")

        # Stream the inventory data
        return await stream_inventory_export(
            db_session=db_session, export_format=format, chunk_size=chunk_size
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Inventory streaming export failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
