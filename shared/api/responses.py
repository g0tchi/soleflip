"""
Standardized API Response Models
Consistent response structures for all API endpoints
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model with common fields"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class SuccessResponse(BaseResponse):
    """Standard success response"""

    success: bool = Field(default=True)
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseResponse):
    """Standard error response"""

    success: bool = Field(default=False)
    error: Dict[str, Any]


class PaginationInfo(BaseModel):
    """Pagination metadata"""

    skip: int = Field(ge=0)
    limit: int = Field(ge=1, le=1000)
    total: int = Field(ge=0)
    has_more: bool
    page: int = Field(ge=1)
    total_pages: int = Field(ge=1)

    @classmethod
    def create(cls, skip: int, limit: int, total: int) -> "PaginationInfo":
        """Create pagination info from skip/limit/total"""
        page = (skip // limit) + 1
        total_pages = max(1, (total + limit - 1) // limit)
        has_more = skip + limit < total

        return cls(
            skip=skip,
            limit=limit,
            total=total,
            has_more=has_more,
            page=page,
            total_pages=total_pages,
        )


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated list response"""

    items: List[T]
    pagination: PaginationInfo
    filters: Optional[Dict[str, Any]] = None


class InventoryItemResponse(BaseModel):
    """Inventory item response model"""

    id: UUID
    product_id: UUID
    product_name: str
    brand_name: Optional[str]
    category_name: str
    size: Optional[str]
    quantity: int
    purchase_price: Optional[float]
    purchase_date: Optional[datetime]
    supplier: Optional[str]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ProductResponse(BaseModel):
    """Product response model"""

    id: UUID
    sku: str
    name: str
    brand_name: Optional[str]
    category_name: str
    description: Optional[str]
    retail_price: Optional[float]
    avg_resale_price: Optional[float]
    release_date: Optional[datetime]
    inventory_count: int
    created_at: datetime
    updated_at: datetime


class BrandResponse(BaseModel):
    """Brand response model"""

    id: UUID
    name: str
    slug: str
    product_count: int
    created_at: datetime
    updated_at: datetime


class TransactionResponse(BaseModel):
    """Transaction response model"""

    id: UUID
    inventory_item_id: UUID
    product_name: str
    brand_name: Optional[str]
    size: str
    platform_name: str
    transaction_date: datetime
    sale_price: float
    platform_fee: float
    shipping_cost: float
    net_profit: float
    status: str
    buyer_destination_country: Optional[str]
    notes: Optional[str]


class ImportStatusResponse(BaseModel):
    """Import batch status response"""

    batch_id: UUID
    source_type: str
    source_file: Optional[str]
    total_records: int
    processed_records: int
    error_records: int
    status: str
    progress_percentage: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    errors: List[str]


class InventorySummaryResponse(BaseModel):
    """Inventory summary statistics"""

    total_items: int
    items_in_stock: int
    items_sold: int
    items_listed: int
    total_inventory_value: float
    average_purchase_price: float
    top_brands: List[Dict[str, Any]]
    status_breakdown: Dict[str, int]
    recent_activity: List[Dict[str, Any]]


class SystemHealthResponse(BaseModel):
    """System health check response"""

    status: str  # "healthy" | "degraded" | "unhealthy"
    timestamp: datetime
    version: str
    uptime_seconds: Optional[float]
    components: Dict[str, Any]


class ValidationErrorResponse(BaseResponse):
    """Validation error response"""

    success: bool = Field(default=False)
    error: Dict[str, Any]
    field_errors: Dict[str, List[str]]


class BulkOperationResponse(BaseResponse):
    """Response for bulk operations"""

    success: bool = Field(default=True)
    operation: str
    total_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]]
    processing_time_seconds: float


class SyncOperationResponse(BaseResponse):
    """Response for sync operations with external services"""

    success: bool = Field(default=True)
    operation: str
    service_name: str
    items_synced: int
    items_created: int
    items_updated: int
    items_skipped: int
    sync_duration_seconds: float
    last_sync_timestamp: datetime
    next_sync_timestamp: Optional[datetime]


# Response builder utility class
class ResponseBuilder:
    """Utility class for building standardized responses"""

    @staticmethod
    def success(
        message: str, data: Any = None, request_id: Optional[str] = None
    ) -> SuccessResponse:
        """Build success response"""
        return SuccessResponse(message=message, data=data, request_id=request_id)

    @staticmethod
    def error(
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
        request_id: Optional[str] = None,
    ) -> ErrorResponse:
        """Build error response"""
        return ErrorResponse(
            error={
                "code": code,
                "message": message,
                "details": details or {},
                "status_code": status_code,
            },
            request_id=request_id,
        )

    @staticmethod
    def paginated(
        items: List[T],
        skip: int,
        limit: int,
        total: int,
        filters: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> PaginatedResponse[T]:
        """Build paginated response"""
        return PaginatedResponse(
            items=items,
            pagination=PaginationInfo.create(skip, limit, total),
            filters=filters,
            request_id=request_id,
        )

    @staticmethod
    def validation_error(
        message: str, field_errors: Dict[str, List[str]], request_id: Optional[str] = None
    ) -> ValidationErrorResponse:
        """Build validation error response"""
        return ValidationErrorResponse(
            error={"code": "VALIDATION_ERROR", "message": message},
            field_errors=field_errors,
            request_id=request_id,
        )

    @staticmethod
    def bulk_operation(
        operation: str,
        total_items: int,
        successful_items: int,
        failed_items: int,
        errors: List[Dict[str, Any]] = None,
        processing_time: float = 0.0,
        request_id: Optional[str] = None,
    ) -> BulkOperationResponse:
        """Build bulk operation response"""
        return BulkOperationResponse(
            operation=operation,
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors or [],
            processing_time_seconds=processing_time,
            request_id=request_id,
        )

    @staticmethod
    def sync_operation(
        operation: str,
        service_name: str,
        stats: Dict[str, int],
        sync_duration: float = 0.0,
        next_sync: Optional[datetime] = None,
        request_id: Optional[str] = None,
    ) -> SyncOperationResponse:
        """Build sync operation response"""
        return SyncOperationResponse(
            operation=operation,
            service_name=service_name,
            items_synced=stats.get("synced", 0),
            items_created=stats.get("created", 0),
            items_updated=stats.get("updated", 0),
            items_skipped=stats.get("skipped", 0),
            sync_duration_seconds=sync_duration,
            last_sync_timestamp=datetime.utcnow(),
            next_sync_timestamp=next_sync,
            request_id=request_id,
        )


# Common response examples for OpenAPI documentation
RESPONSE_EXAMPLES = {
    "success_example": {
        "success": True,
        "message": "Operation completed successfully",
        "data": {"id": "123e4567-e89b-12d3-a456-426614174000"},
        "timestamp": "2025-01-15T10:30:00Z",
        "request_id": "req-123456",
    },
    "error_example": {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "The provided data is invalid",
            "details": {"field": "value"},
            "status_code": 400,
        },
        "timestamp": "2025-01-15T10:30:00Z",
        "request_id": "req-123456",
    },
    "paginated_example": {
        "items": [
            {"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Product 1"},
            {"id": "456e7890-e89b-12d3-a456-426614174001", "name": "Product 2"},
        ],
        "pagination": {
            "skip": 0,
            "limit": 50,
            "total": 150,
            "has_more": True,
            "page": 1,
            "total_pages": 3,
        },
        "filters": {"brand": "Nike", "status": "in_stock"},
        "timestamp": "2025-01-15T10:30:00Z",
        "request_id": "req-123456",
    },
}


# Convenience functions for backward compatibility
def create_success_response(
    message: str, data: Any = None, request_id: Optional[str] = None
) -> SuccessResponse:
    """Create a success response"""
    return ResponseBuilder.success(message, data, request_id)


def create_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 500,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create an error response"""
    return ResponseBuilder.error(code, message, details, status_code, request_id)
