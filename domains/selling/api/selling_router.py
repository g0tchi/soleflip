"""
Selling Router - StockX Selling API Endpoints
Automated selling and listing management endpoints
"""

import os
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
import structlog

from shared.api.dependencies import get_db_session
from shared.auth.dependencies import require_authenticated_user
from shared.auth.models import User
from shared.validation.financial_validators import (
    ListingCreationRequest,
    BulkListingRequest,
    PriceUpdateRequest,
    UUIDPath,
    MarginQuery,
    PricingStrategyQuery,
    validate_price_update,
    validate_bulk_request
)
from shared.error_handling.selling_exceptions import (
    ListingCreationError,
    PriceUpdateError,
    ListingNotFoundError,
    OpportunityNotFoundError,
    StockXAPIError,
    BulkOperationError,
    ConfigurationError,
    ErrorResponse
)
from shared.security.api_security import (
    get_client_ip,
    validate_user_permissions,
    AuditLogger
)
from domains.selling.services.stockx_selling_service import StockXSellingService
from domains.integration.services.quickflip_detection_service import QuickFlipDetectionService

logger = structlog.get_logger(__name__)
audit_logger = AuditLogger()

router = APIRouter()


# Enhanced Response Models with better OpenAPI documentation


class ListingResponse(BaseModel):
    """Response model for StockX listings"""
    id: str
    product_id: str
    stockx_listing_id: str
    stockx_product_id: str
    variant_id: Optional[str]
    ask_price: float
    original_ask_price: Optional[float]
    buy_price: Optional[float]
    expected_profit: Optional[float]
    expected_margin: Optional[float]
    status: str
    is_active: bool
    expires_at: Optional[str]
    current_lowest_ask: Optional[float]
    current_highest_bid: Optional[float]
    created_from: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ListingSummaryResponse(BaseModel):
    """Summary statistics for listings"""
    total_listings: int
    active_listings: int
    inactive_listings: int
    sold_listings: int
    total_expected_profit: float
    avg_expected_margin: float
    most_profitable_listing: Optional[ListingResponse]


def get_selling_service(db: AsyncSession = Depends(get_db_session)) -> StockXSellingService:
    """Dependency to get StockX selling service"""
    api_token = os.getenv("STOCKX_API_TOKEN")
    if not api_token:
        logger.error("StockX API token not configured")
        raise ConfigurationError("StockX API integration not available")

    try:
        return StockXSellingService(db, api_token)
    except Exception as e:
        logger.error("Failed to initialize StockX selling service", error=str(e))
        raise ConfigurationError("Selling service initialization failed")


@router.post(
    "/listings/create-from-opportunity",
    response_model=ListingResponse,
    summary="Create listing from QuickFlip opportunity",
    description="Convert a QuickFlip opportunity into a StockX listing with optimal pricing and comprehensive validation",
    responses={
        200: {"description": "Listing created successfully"},
        422: {"description": "Validation error - invalid input data"},
        404: {"description": "QuickFlip opportunity not found"},
        500: {"description": "Internal server error"}
    }
)
async def create_listing_from_opportunity(
    request: ListingCreationRequest,
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db_session),
    client_ip: str = Depends(get_client_ip),
    http_request: Request = None
):
    """Create a StockX listing from a QuickFlip opportunity"""
    try:
        # Audit log the attempt
        audit_logger.log_security_event(
            "listing_creation_attempt",
            http_request,
            user_id=str(user.id),
            additional_data={
                "opportunity_id": str(request.opportunity_id),
                "pricing_strategy": request.pricing_strategy,
                "client_ip": client_ip
            }
        )

        # Get the opportunity details
        quickflip_service = QuickFlipDetectionService(db)
        opportunity = await quickflip_service.get_opportunity_by_product(request.opportunity_id)

        if not opportunity:
            raise OpportunityNotFoundError(str(request.opportunity_id))

        # Take the first opportunity if multiple exist
        if isinstance(opportunity, list):
            opportunity = opportunity[0]

        # Create the listing
        listing = await selling_service.create_listing_from_opportunity(
            opportunity=opportunity,
            pricing_strategy=request.pricing_strategy,
            margin_buffer=request.margin_buffer
        )

        # Audit log success
        audit_logger.log_security_event(
            "listing_created_successfully",
            http_request,
            user_id=str(user.id),
            additional_data={
                "listing_id": str(listing.id),
                "ask_price": float(listing.ask_price)
            }
        )

        return ListingResponse(**listing.to_dict())

    except (OpportunityNotFoundError, ListingCreationError, StockXAPIError, ConfigurationError):
        raise
    except Exception as e:
        logger.error(
            "Unexpected error creating listing",
            user_id=str(user.id),
            opportunity_id=str(request.opportunity_id),
            error=str(e)
        )
        raise ListingCreationError("Failed to create listing due to internal error")


@router.post(
    "/listings/bulk-create",
    response_model=List[ListingResponse],
    summary="Create multiple listings from opportunities",
    description="Efficiently create multiple StockX listings from QuickFlip opportunities with batch validation",
    responses={
        200: {"description": "Bulk listings created successfully"},
        422: {"description": "Validation error - invalid input data"},
        404: {"description": "One or more opportunities not found"},
        500: {"description": "Internal server error"}
    }
)
async def create_bulk_listings(
    request: BulkListingRequest = Depends(validate_bulk_request),
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create multiple listings from QuickFlip opportunities"""
    try:
        # Get all opportunities
        quickflip_service = QuickFlipDetectionService(db)
        opportunities = []

        for opportunity_id in request.opportunity_ids:
            opportunity = await quickflip_service.get_opportunity_by_product(opportunity_id)
            if opportunity:
                # Take first if multiple exist
                if isinstance(opportunity, list):
                    opportunity = opportunity[0]
                opportunities.append(opportunity)

        if not opportunities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valid opportunities found"
            )

        # Create bulk listings
        listings = await selling_service.create_bulk_listings(opportunities)

        return [ListingResponse(**listing.to_dict()) for listing in listings]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk listings: {str(e)}"
        )


@router.get(
    "/listings",
    response_model=List[ListingResponse],
    summary="Get my StockX listings",
    description="Retrieve all your StockX listings with optional filtering"
)
async def get_my_listings(
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, sold, expired"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    include_product: bool = Query(True, description="Include product details"),
    include_pricing_history: bool = Query(False, description="Include pricing history"),
    include_orders: bool = Query(False, description="Include order information"),
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user)
):
    """Get all my StockX listings with optimized eager loading options"""
    try:
        listings = await selling_service.get_my_listings(
            status=status,
            limit=limit,
            include_product=include_product,
            include_pricing_history=include_pricing_history,
            include_orders=include_orders
        )

        return [ListingResponse(**listing.to_dict()) for listing in listings]

    except (ListingNotFoundError, DatabaseError):
        raise
    except Exception as e:
        logger.error(
            "Unexpected error getting listings",
            user_id=str(user.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve listings"
        )


@router.get(
    "/listings/summary",
    response_model=ListingSummaryResponse,
    summary="Get listings summary",
    description="Get statistical summary of all your listings"
)
async def get_listings_summary(
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user)
):
    """Get summary statistics for all listings using optimized aggregation queries"""
    try:
        summary = await selling_service.get_listings_summary_optimized(
            user_id=str(user.id)
        )

        return ListingSummaryResponse(
            total_listings=summary['total_listings'],
            active_listings=summary['active_listings'],
            inactive_listings=summary['inactive_listings'],
            sold_listings=summary['sold_listings'],
            total_expected_profit=summary['total_expected_profit'],
            avg_expected_margin=summary['avg_expected_margin'],
            most_profitable_listing=(
                ListingResponse(**summary['most_profitable_listing'].to_dict())
                if summary['most_profitable_listing'] else None
            )
        )

    except (DatabaseError, ConfigurationError):
        raise
    except Exception as e:
        logger.error(
            "Unexpected error getting listings summary",
            user_id=str(user.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate listings summary"
        )


@router.put(
    "/listings/{listing_id}/price",
    response_model=ListingResponse,
    summary="Update listing price",
    description="Update the asking price of a specific listing with comprehensive validation",
    responses={
        200: {"description": "Price updated successfully"},
        422: {"description": "Validation error - invalid price data"},
        404: {"description": "Listing not found"},
        500: {"description": "Internal server error"}
    }
)
async def update_listing_price(
    listing_id: Annotated[UUID, UUIDPath(description="Listing ID to update")],
    request: PriceUpdateRequest = Depends(validate_price_update),
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user),
    client_ip: str = Depends(get_client_ip),
    http_request: Request = None
):
    """Update the price of a listing"""
    try:
        # Audit log the attempt
        audit_logger.log_security_event(
            "price_update_attempt",
            http_request,
            user_id=str(user.id),
            additional_data={
                "listing_id": str(listing_id),
                "new_price": float(request.new_price),
                "reason": request.reason,
                "client_ip": client_ip
            }
        )

        listing = await selling_service.update_listing_price(
            listing_id=listing_id,
            new_price=request.new_price,
            reason=request.reason
        )

        # Audit log success
        audit_logger.log_security_event(
            "price_updated_successfully",
            http_request,
            user_id=str(user.id),
            additional_data={
                "listing_id": str(listing_id),
                "new_price": float(request.new_price)
            }
        )

        return ListingResponse(**listing.to_dict())

    except (ListingNotFoundError, PriceUpdateError, StockXAPIError):
        raise
    except Exception as e:
        logger.error(
            "Unexpected error updating listing price",
            user_id=str(user.id),
            listing_id=str(listing_id),
            error=str(e)
        )
        raise PriceUpdateError("Failed to update listing price due to internal error")


@router.post(
    "/listings/{listing_id}/activate",
    summary="Activate listing",
    description="Activate a deactivated listing on StockX"
)
async def activate_listing(
    listing_id: UUID,
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user)
):
    """Activate a listing"""
    try:
        success = await selling_service.activate_listing(listing_id)

        if success:
            return {"success": True, "message": "Listing activated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to activate listing"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate listing: {str(e)}"
        )


@router.post(
    "/listings/{listing_id}/deactivate",
    summary="Deactivate listing",
    description="Deactivate an active listing on StockX"
)
async def deactivate_listing(
    listing_id: UUID,
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user)
):
    """Deactivate a listing"""
    try:
        success = await selling_service.deactivate_listing(listing_id)

        if success:
            return {"success": True, "message": "Listing deactivated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate listing"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate listing: {str(e)}"
        )


@router.post(
    "/sync/listings",
    summary="Sync listing statuses",
    description="Synchronize all listing statuses with StockX"
)
async def sync_listing_statuses(
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user)
):
    """Sync all listing statuses with StockX"""
    try:
        stats = await selling_service.sync_listing_status()

        return {
            "success": True,
            "message": "Listing statuses synchronized",
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync listing statuses: {str(e)}"
        )


# Health check for selling service
@router.get(
    "/health",
    summary="Selling service health check",
    description="Check if the selling service is operational"
)
async def selling_health_check(
    selling_service: StockXSellingService = Depends(get_selling_service)
):
    """Health check for selling service"""
    try:
        # Quick test to ensure service is working
        listings_count = len(await selling_service.get_my_listings(limit=1))

        return {
            "status": "healthy",
            "service": "stockx_selling",
            "api_connected": True,
            "listings_accessible": True,
            "timestamp": "2025-09-19T12:00:00Z"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Selling service unhealthy: {str(e)}"
        )


@router.get(
    "/listings/{listing_id}/details",
    response_model=ListingResponse,
    summary="Get detailed listing information",
    description="Get a specific listing with all related data using optimized eager loading"
)
async def get_listing_details(
    listing_id: Annotated[UUID, UUIDPath(description="Listing ID to retrieve")],
    selling_service: StockXSellingService = Depends(get_selling_service),
    user: User = Depends(require_authenticated_user)
):
    """Get detailed information for a specific listing"""
    try:
        listing = await selling_service.get_listing_with_full_details(listing_id)

        if not listing:
            raise ListingNotFoundError(str(listing_id))

        return ListingResponse(**listing.to_dict())

    except ListingNotFoundError:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error getting listing details",
            user_id=str(user.id),
            listing_id=str(listing_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve listing details"
        )