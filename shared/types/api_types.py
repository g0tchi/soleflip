"""
API-specific type definitions
"""

from typing import Dict, List, Optional, Union, Any, Generic, TypeVar
from typing_extensions import TypedDict, NotRequired
from datetime import datetime
from pydantic import BaseModel, Field
from .base_types import EntityId, HTTPStatus, JSONDict
from .domain_types import *

T = TypeVar("T")


# Request Types
class PaginationParams(BaseModel):
    """Pagination parameters"""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=50, ge=1, le=1000, description="Number of items to return")


class SearchParams(BaseModel):
    """Search parameters"""

    query: Optional[str] = Field(None, description="Search query")
    brand: Optional[str] = Field(None, description="Filter by brand")
    category: Optional[str] = Field(None, description="Filter by category")
    status: Optional[str] = Field(None, description="Filter by status")
    size: Optional[str] = Field(None, description="Filter by size")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    date_from: Optional[datetime] = Field(None, description="Date range start")
    date_to: Optional[datetime] = Field(None, description="Date range end")


class SortParams(BaseModel):
    """Sort parameters"""

    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_direction: Optional[str] = Field(
        "asc", pattern="^(asc|desc)$", description="Sort direction"
    )


class BulkOperationParams(BaseModel):
    """Bulk operation parameters"""

    batch_size: int = Field(default=1000, ge=1, le=10000, description="Batch size for processing")
    validate_only: bool = Field(default=False, description="Only validate, don't process")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing records")
    skip_errors: bool = Field(default=False, description="Continue processing on errors")


# Request Models
class ProductCreateRequest(BaseModel):
    """Product creation request"""

    sku: str = Field(..., min_length=3, max_length=100, description="Product SKU")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    brand_name: str = Field(..., min_length=1, max_length=100, description="Brand name")
    category_name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    retail_price: Optional[float] = Field(None, ge=0, description="Retail price")
    release_date: Optional[datetime] = Field(None, description="Release date")


class ProductUpdateRequest(BaseModel):
    """Product update request"""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    retail_price: Optional[float] = Field(None, ge=0, description="Retail price")
    status: Optional[ProductStatus] = Field(None, description="Product status")


class InventoryItemCreateRequest(BaseModel):
    """Inventory item creation request"""

    product_id: EntityId = Field(..., description="Product ID")
    size_value: str = Field(..., min_length=1, max_length=20, description="Size value")
    size_region: SizeRegion = Field(..., description="Size region")
    quantity: int = Field(..., ge=1, description="Quantity")
    purchase_price: Optional[float] = Field(None, ge=0, description="Purchase price")
    purchase_date: Optional[datetime] = Field(None, description="Purchase date")
    supplier: Optional[str] = Field(None, max_length=100, description="Supplier name")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes")


class InventoryItemUpdateRequest(BaseModel):
    """Inventory item update request"""

    quantity: Optional[int] = Field(None, ge=0, description="Quantity")
    purchase_price: Optional[float] = Field(None, ge=0, description="Purchase price")
    status: Optional[InventoryStatus] = Field(None, description="Status")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes")


class TransactionCreateRequest(BaseModel):
    """Transaction creation request"""

    inventory_id: EntityId = Field(..., description="Inventory item ID")
    platform_name: str = Field(..., min_length=1, max_length=100, description="Platform name")
    transaction_date: datetime = Field(..., description="Transaction date")
    sale_price: float = Field(..., ge=0, description="Sale price")
    platform_fee: float = Field(..., ge=0, description="Platform fee")
    shipping_cost: float = Field(default=0, ge=0, description="Shipping cost")
    buyer_destination_country: Optional[str] = Field(
        None, max_length=100, description="Buyer country"
    )
    buyer_destination_city: Optional[str] = Field(None, max_length=100, description="Buyer city")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes")


class SupplierCreateRequest(BaseModel):
    """Supplier creation request"""

    name: str = Field(..., min_length=1, max_length=100, description="Supplier name")
    supplier_type: SupplierType = Field(..., description="Supplier type")
    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    website: Optional[str] = Field(None, max_length=200, description="Website URL")
    contact_person: Optional[str] = Field(None, max_length=100, description="Contact person")

    # Address
    address_line1: Optional[str] = Field(None, max_length=200, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=200, description="Address line 2")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(None, max_length=100, description="State/Province")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: Optional[str] = Field(default="Germany", max_length=50, description="Country")

    # Business details
    business_size: Optional[BusinessSize] = Field(None, description="Business size")
    payment_terms: Optional[str] = Field(None, max_length=100, description="Payment terms")
    return_policy_days: Optional[int] = Field(None, ge=0, le=365, description="Return policy days")


class ImportBatchCreateRequest(BaseModel):
    """Import batch creation request"""

    source_type: ImportSourceType = Field(..., description="Import source type")
    source_file: Optional[str] = Field(None, description="Source file path")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Response Models
class BaseResponse(BaseModel):
    """Base response model"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class SuccessResponse(BaseResponse):
    """Success response model"""

    success: bool = Field(default=True)
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseResponse):
    """Error response model"""

    success: bool = Field(default=False)
    error: Dict[str, Any]


class ValidationErrorResponse(BaseResponse):
    """Validation error response model"""

    success: bool = Field(default=False)
    error: Dict[str, Any]
    field_errors: Dict[str, List[str]]


class PaginationInfo(BaseModel):
    """Pagination information model"""

    skip: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    has_more: bool
    page: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=1)

    @classmethod
    def create(cls, skip: int, limit: int, total: int) -> "PaginationInfo":
        """Create pagination info from parameters"""
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
    """Paginated response model"""

    items: List[T]
    pagination: PaginationInfo
    filters: Optional[Dict[str, Any]] = None


class ProductResponse(BaseModel):
    """Product response model"""

    id: EntityId
    sku: str
    name: str
    brand_id: Optional[EntityId] = None
    brand_name: Optional[str] = None
    category_id: EntityId
    category_name: str
    description: Optional[str] = None
    retail_price: Optional[float] = None
    avg_resale_price: Optional[float] = None
    release_date: Optional[datetime] = None
    status: ProductStatus
    inventory_count: int = 0
    created_at: datetime
    updated_at: datetime


class InventoryItemResponse(BaseModel):
    """Inventory item response model"""

    id: EntityId
    product_id: EntityId
    product_name: str
    product_sku: str
    brand_name: Optional[str] = None
    category_name: str
    size: str
    size_region: SizeRegion
    quantity: int
    purchase_price: Optional[float] = None
    purchase_date: Optional[datetime] = None
    supplier: Optional[str] = None
    status: InventoryStatus
    notes: Optional[str] = None
    external_ids: Optional[JSONDict] = None
    created_at: datetime
    updated_at: datetime


class TransactionResponse(BaseModel):
    """Transaction response model"""

    id: EntityId
    inventory_item_id: EntityId
    product_name: str
    product_sku: str
    brand_name: Optional[str] = None
    size: str
    platform_name: str
    transaction_date: datetime
    sale_price: float
    platform_fee: float
    shipping_cost: float
    net_profit: float
    status: TransactionStatus
    external_id: Optional[str] = None
    buyer_destination_country: Optional[str] = None
    buyer_destination_city: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SupplierResponse(BaseModel):
    """Supplier response model"""

    id: EntityId
    name: str
    slug: str
    supplier_type: SupplierType
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    contact_person: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    rating: Optional[float] = None
    status: SupplierStatus
    total_orders_count: int = 0
    total_order_value: Optional[float] = None
    last_order_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BrandResponse(BaseModel):
    """Brand response model"""

    id: EntityId
    name: str
    slug: str
    product_count: int = 0
    created_at: datetime
    updated_at: datetime


class CategoryResponse(BaseModel):
    """Category response model"""

    id: EntityId
    name: str
    slug: str
    parent_id: Optional[EntityId] = None
    path: Optional[str] = None
    product_count: int = 0
    created_at: datetime
    updated_at: datetime


class ImportBatchResponse(BaseModel):
    """Import batch response model"""

    id: EntityId
    source_type: ImportSourceType
    source_file: Optional[str] = None
    total_records: int
    processed_records: int
    error_records: int
    status: ImportStatus
    progress_percentage: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    errors: List[str] = []
    created_at: datetime
    updated_at: datetime


class BulkOperationResponse(BaseResponse):
    """Bulk operation response model"""

    operation: str
    total_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]] = []
    processing_time_seconds: float


class SyncOperationResponse(BaseResponse):
    """Sync operation response model"""

    operation: str
    service_name: str
    items_synced: int
    items_created: int
    items_updated: int
    items_skipped: int
    sync_duration_seconds: float
    last_sync_timestamp: datetime
    next_sync_timestamp: Optional[datetime] = None


class HealthCheckResponse(BaseModel):
    """Health check response model"""

    status: str  # "healthy" | "degraded" | "unhealthy"
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: Optional[float] = None
    components: Dict[str, Any]


class InventorySummaryResponse(BaseModel):
    """Inventory summary response model"""

    total_items: int
    items_in_stock: int
    items_sold: int
    items_listed: int
    total_inventory_value: float
    average_purchase_price: float
    top_brands: List[Dict[str, Any]]
    status_breakdown: Dict[str, int]
    recent_activity: List[Dict[str, Any]]


# Webhook Types
class WebhookRequest(BaseModel):
    """Webhook request model"""

    event: WebhookEvent
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    version: str = "1.0"
    signature: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response model"""

    received: bool = True
    processed: bool
    message: Optional[str] = None
    errors: List[str] = []


# File Upload Types
class FileUploadResponse(BaseModel):
    """File upload response model"""

    filename: str
    size: int
    content_type: str
    upload_id: str
    url: Optional[str] = None


class BatchUploadRequest(BaseModel):
    """Batch upload request model"""

    file_type: str = Field(..., pattern="^(csv|json|xlsx)$")
    delimiter: Optional[str] = Field(",", max_length=1, description="CSV delimiter")
    has_header: bool = Field(True, description="File has header row")
    encoding: str = Field("utf-8", description="File encoding")
    column_mappings: Optional[Dict[str, str]] = Field(None, description="Column name mappings")


# API Metadata Types
class APIMetadata(TypedDict):
    """API metadata structure"""

    title: str
    version: str
    description: str
    contact: NotRequired[Dict[str, str]]
    license: NotRequired[Dict[str, str]]
    servers: NotRequired[List[Dict[str, str]]]


class OpenAPIConfig(TypedDict):
    """OpenAPI configuration structure"""

    openapi_url: str
    docs_url: Optional[str]
    redoc_url: Optional[str]
    swagger_ui_parameters: NotRequired[Dict[str, Any]]


# Rate Limiting Types
class RateLimitInfo(BaseModel):
    """Rate limit information model"""

    limit: int
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response model"""

    error: str = "Rate limit exceeded"
    rate_limit: RateLimitInfo
    message: str = "Too many requests. Please try again later."


# Cache Types
class CacheInfo(BaseModel):
    """Cache information model"""

    key: str
    hit: bool
    ttl: Optional[int] = None
    size: Optional[int] = None


class CacheStats(BaseModel):
    """Cache statistics model"""

    hits: int
    misses: int
    hit_rate: float
    size: int
    max_size: int
