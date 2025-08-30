"""
Centralized API Dependencies
Production-ready dependency injection system for consistent API patterns
"""

from typing import Optional, Dict, Any, Annotated
from fastapi import Depends, HTTPException, Query, Path, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from shared.database.connection import get_db_session
from shared.database.session_manager import SessionManager
from domains.inventory.services.inventory_service import InventoryService
from domains.integration.services.stockx_service import StockXService
from domains.products.services.brand_service import BrandExtractorService

logger = structlog.get_logger(__name__)


# Database Dependencies
async def get_session_manager() -> SessionManager:
    """Get session manager instance"""
    from shared.database.connection import db_manager

    return SessionManager(db_manager.session_factory)


# Service Dependencies
async def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    """Get inventory service with database session"""
    return InventoryService(db)


async def get_stockx_service(db: AsyncSession = Depends(get_db_session)) -> StockXService:
    """Get StockX service with database session"""
    return StockXService(db)


async def get_brand_service(db: AsyncSession = Depends(get_db_session)) -> BrandExtractorService:
    """Get brand extractor service with database session"""
    return BrandExtractorService(db)


# Pagination Dependencies
class PaginationParams:
    def __init__(
        self,
        skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
        limit: Annotated[int, Query(ge=1, le=1000, description="Number of items to return")] = 100,
    ):
        self.skip = skip
        self.limit = limit

    def to_dict(self) -> Dict[str, int]:
        return {"skip": self.skip, "limit": self.limit}


# Validation Dependencies
async def validate_uuid(uuid_value: UUID) -> UUID:
    """Validate UUID parameter"""
    if not uuid_value:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    return uuid_value


async def validate_product_id(product_id: Annotated[UUID, Path(description="Product ID")]) -> UUID:
    """Validate product ID exists"""
    # Basic UUID validation
    return await validate_uuid(product_id)


async def validate_inventory_item_id(
    item_id: Annotated[UUID, Path(description="Inventory item ID")],
) -> UUID:
    """Validate inventory item ID"""
    return await validate_uuid(item_id)


# Search and Filter Dependencies
class SearchParams:
    def __init__(
        self,
        q: Annotated[Optional[str], Query(description="Search query")] = None,
        brand: Annotated[Optional[str], Query(description="Filter by brand name")] = None,
        category: Annotated[Optional[str], Query(description="Filter by category")] = None,
        status: Annotated[Optional[str], Query(description="Filter by status")] = None,
        size: Annotated[Optional[str], Query(description="Filter by size")] = None,
        min_price: Annotated[
            Optional[float], Query(ge=0, description="Minimum price filter")
        ] = None,
        max_price: Annotated[
            Optional[float], Query(ge=0, description="Maximum price filter")
        ] = None,
    ):
        self.query = q
        self.brand = brand
        self.category = category
        self.status = status
        self.size = size
        self.min_price = min_price
        self.max_price = max_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "brand": self.brand,
            "category": self.category,
            "status": self.status,
            "size": self.size,
            "min_price": self.min_price,
            "max_price": self.max_price,
        }

    def has_filters(self) -> bool:
        """Check if any filters are applied"""
        return any(
            [
                self.query,
                self.brand,
                self.category,
                self.status,
                self.size,
                self.min_price,
                self.max_price,
            ]
        )


# Request Headers Dependencies
class RequestHeaders:
    def __init__(
        self,
        user_agent: Annotated[Optional[str], Header()] = None,
        x_request_id: Annotated[Optional[str], Header(alias="X-Request-ID")] = None,
        authorization: Annotated[Optional[str], Header()] = None,
    ):
        self.user_agent = user_agent
        self.request_id = x_request_id
        self.authorization = authorization


# Authentication Dependencies (placeholder for future implementation)
async def get_current_user():
    """Get current authenticated user (placeholder)"""
    # TODO: Implement actual authentication
    return {"user_id": "system", "role": "admin"}


async def require_admin_role(current_user=Depends(get_current_user)):
    """Require admin role for endpoint access"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# Business Logic Dependencies
async def validate_inventory_operation(
    item_id: UUID = Depends(validate_inventory_item_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
) -> Dict[str, Any]:
    """Validate that inventory item exists and return its details"""
    try:
        item = await inventory_service.get_product_details(item_id)
        if not item:
            raise HTTPException(
                status_code=404, detail=f"Inventory item with ID {item_id} not found"
            )
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to validate inventory item", item_id=str(item_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to validate inventory item")


# File Upload Dependencies
class UploadParams:
    def __init__(
        self,
        batch_size: Annotated[
            int, Query(ge=1, le=10000, description="Batch processing size")
        ] = 1000,
        validate_only: Annotated[bool, Query(description="Only validate, don't import")] = False,
        overwrite_existing: Annotated[
            bool, Query(description="Overwrite existing records")
        ] = False,
    ):
        self.batch_size = batch_size
        self.validate_only = validate_only
        self.overwrite_existing = overwrite_existing


# Monitoring Dependencies
async def log_api_access(
    headers: RequestHeaders = Depends(),
    pagination: PaginationParams = Depends(),
):
    """Log API access for monitoring"""
    logger.info(
        "API endpoint accessed",
        user_agent=headers.user_agent,
        request_id=headers.request_id,
        pagination=pagination.to_dict(),
    )


# Error Handling Dependencies
class ErrorContext:
    def __init__(self, operation: str, resource_type: str):
        self.operation = operation
        self.resource_type = resource_type

    def create_error_response(self, error: Exception, status_code: int = 500) -> HTTPException:
        """Create standardized error response"""
        logger.error(
            f"Error in {self.operation}",
            operation=self.operation,
            resource_type=self.resource_type,
            error=str(error),
            error_type=type(error).__name__,
        )

        return HTTPException(
            status_code=status_code, detail=f"Failed to {self.operation} {self.resource_type}"
        )


# Common dependency combinations
def get_inventory_context():
    """Get common inventory operation dependencies"""
    return {
        "service": Depends(get_inventory_service),
        "pagination": Depends(PaginationParams),
        "search": Depends(SearchParams),
        "headers": Depends(RequestHeaders),
    }


def get_product_context():
    """Get common product operation dependencies"""
    return {
        "inventory_service": Depends(get_inventory_service),
        "brand_service": Depends(get_brand_service),
        "pagination": Depends(PaginationParams),
        "search": Depends(SearchParams),
    }


# Response Formatting Dependencies
class ResponseFormatter:
    @staticmethod
    def format_list_response(
        items: list, total: int, pagination: PaginationParams, search: SearchParams = None
    ) -> Dict[str, Any]:
        """Format standardized list response"""
        return {
            "items": items,
            "pagination": {
                "skip": pagination.skip,
                "limit": pagination.limit,
                "total": total,
                "has_more": pagination.skip + pagination.limit < total,
            },
            "filters": search.to_dict() if search and search.has_filters() else None,
        }

    @staticmethod
    def format_success_response(
        message: str, data: Any = None, operation: str = None
    ) -> Dict[str, Any]:
        """Format standardized success response"""
        response = {"message": message}
        if data is not None:
            response["data"] = data
        if operation:
            response["operation"] = operation
        return response


# Dependency factory for creating parameterized dependencies
class DependencyFactory:
    @staticmethod
    def create_service_dependency(service_class):
        """Create a service dependency for any service class"""

        async def get_service(db: AsyncSession = Depends(get_db_session)):
            return service_class(db)

        return get_service

    @staticmethod
    def create_validation_dependency(validator_func):
        """Create a validation dependency from a validator function"""

        async def validate_input(value: Any):
            if not validator_func(value):
                raise HTTPException(status_code=400, detail="Validation failed")
            return value

        return validate_input
