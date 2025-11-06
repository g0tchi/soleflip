"""
Centralized API Dependencies
Production-ready dependency injection system for consistent API patterns
"""

from typing import Annotated, Any, Dict, Optional
from uuid import UUID

import structlog
from fastapi import Depends, Header, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.stockx_service import StockXService
from domains.inventory.services.inventory_service import InventoryService
from domains.products.services.brand_service import BrandExtractorService
from shared.database.connection import get_db_session
from shared.database.session_manager import SessionManager

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
    """
    Pagination parameters for list endpoints.

    Provides consistent pagination across all API endpoints with validation
    and conversion utilities.

    Attributes:
        skip (int): Number of items to skip (offset). Default: 0, Min: 0
        limit (int): Number of items to return per page. Default: 100, Min: 1, Max: 1000

    Example:
        ```python
        from fastapi import Depends
        from shared.api.dependencies import PaginationParams

        @router.get("/products")
        async def list_products(pagination: PaginationParams = Depends()):
            products = await get_products(
                offset=pagination.skip,
                limit=pagination.limit
            )
            return products
        ```

    Query Parameters:
        - skip: Offset for pagination (e.g., skip=50 for page 2 with limit=50)
        - limit: Page size (number of items to return)

    Validation:
        - skip must be >= 0
        - limit must be between 1 and 1000 (prevents excessive data retrieval)

    Notes:
        - Use with ResponseFormatter.format_list_response() for consistent responses
        - Automatically validates and converts query parameters
    """

    def __init__(
        self,
        skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
        limit: Annotated[int, Query(ge=1, le=1000, description="Number of items to return")] = 100,
    ):
        self.skip = skip
        self.limit = limit

    def to_dict(self) -> Dict[str, int]:
        """
        Convert pagination parameters to dictionary.

        Returns:
            Dict with 'skip' and 'limit' keys

        Example:
            >>> pagination = PaginationParams(skip=10, limit=50)
            >>> pagination.to_dict()
            {'skip': 10, 'limit': 50}
        """
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
    """
    Multi-field search and filter parameters for list endpoints.

    Provides comprehensive filtering capabilities across product, inventory,
    and order endpoints with validation and utility methods.

    Attributes:
        query (Optional[str]): Free-text search query (searches name, SKU, description)
        brand (Optional[str]): Filter by brand name (case-insensitive)
        category (Optional[str]): Filter by category
        status (Optional[str]): Filter by status (e.g., "active", "sold", "pending")
        size (Optional[str]): Filter by size (e.g., "US 10", "M", "38 EU")
        min_price (Optional[float]): Minimum price filter (inclusive)
        max_price (Optional[float]): Maximum price filter (inclusive)

    Example:
        ```python
        from fastapi import Depends
        from shared.api.dependencies import SearchParams

        @router.get("/products")
        async def search_products(search: SearchParams = Depends()):
            filters = {}
            if search.brand:
                filters['brand'] = search.brand
            if search.min_price:
                filters['price__gte'] = search.min_price

            if search.has_filters():
                products = await filter_products(filters)
            else:
                products = await get_all_products()

            return products
        ```

    Query Parameters:
        - q: Search term (searches multiple fields)
        - brand: Brand name filter
        - category: Category filter
        - status: Status filter
        - size: Size filter
        - min_price: Minimum price (>=0)
        - max_price: Maximum price (>=0)

    Methods:
        has_filters(): Returns True if any filter is applied
        to_dict(): Returns all filters as dictionary

    Validation:
        - min_price and max_price must be >= 0 if provided
        - All parameters are optional (None by default)

    Notes:
        - Combine with PaginationParams for paginated filtered results
        - Use has_filters() to optimize queries (skip filtering if no filters applied)
    """

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
        """
        Convert search parameters to dictionary.

        Returns:
            Dict containing all search/filter parameters (including None values)

        Example:
            >>> search = SearchParams(brand="Nike", min_price=100.0)
            >>> search.to_dict()
            {
                'query': None,
                'brand': 'Nike',
                'category': None,
                'status': None,
                'size': None,
                'min_price': 100.0,
                'max_price': None
            }
        """
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
        """
        Check if any filters are applied.

        Returns:
            True if at least one filter parameter is not None

        Example:
            >>> search = SearchParams(brand="Nike")
            >>> search.has_filters()
            True

            >>> search = SearchParams()
            >>> search.has_filters()
            False

        Notes:
            Use this to optimize database queries - skip complex filtering
            logic if no filters are applied.
        """
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
    """
    HTTP request headers dependency for logging and monitoring.

    Captures common request headers for logging, tracing, and authentication
    purposes. Used for request correlation and debugging.

    Attributes:
        user_agent (Optional[str]): Client user agent string (e.g., browser, app version)
        request_id (Optional[str]): Request ID for tracing (X-Request-ID header)
        authorization (Optional[str]): Authorization header (JWT bearer token)

    Example:
        ```python
        from fastapi import Depends
        from shared.api.dependencies import RequestHeaders

        @router.get("/products")
        async def get_products(headers: RequestHeaders = Depends()):
            logger.info(
                "Request received",
                request_id=headers.request_id,
                user_agent=headers.user_agent
            )
            # ... endpoint logic
        ```

    Headers:
        - User-Agent: Identifies client application
        - X-Request-ID: Unique request identifier for tracing
        - Authorization: JWT token for authentication

    Notes:
        - Use with log_api_access() dependency for automatic logging
        - request_id useful for distributed tracing and debugging
        - authorization header parsed by auth middleware
    """

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
    """
    File upload and import configuration parameters.

    Controls behavior of CSV/data import operations including batch processing,
    validation-only mode, and overwrite settings.

    Attributes:
        batch_size (int): Number of rows to process per batch. Default: 1000, Min: 1, Max: 10000
        validate_only (bool): If True, only validate data without importing. Default: False
        overwrite_existing (bool): If True, overwrite existing records with same ID/SKU. Default: False

    Example:
        ```python
        from fastapi import Depends, UploadFile
        from shared.api.dependencies import UploadParams

        @router.post("/upload")
        async def upload_file(
            file: UploadFile,
            params: UploadParams = Depends()
        ):
            if params.validate_only:
                return await validate_csv(file, batch_size=params.batch_size)
            else:
                return await import_csv(
                    file,
                    batch_size=params.batch_size,
                    overwrite=params.overwrite_existing
                )
        ```

    Query Parameters:
        - batch_size: Rows per batch (affects memory usage and transaction size)
        - validate_only: Dry-run mode for validation
        - overwrite_existing: Update behavior for duplicate records

    Batch Size Guidelines:
        - Small files (<1000 rows): Use default (1000)
        - Medium files (1000-10000 rows): Use 2000-5000
        - Large files (>10000 rows): Use 500-1000 (memory optimization)

    Validation:
        - batch_size must be between 1 and 10000
        - All boolean flags default to False (safe defaults)

    Notes:
        - validate_only useful for testing imports before committing
        - overwrite_existing=False prevents accidental data loss
        - Larger batch_size = faster but more memory usage
    """

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
    """
    Error context helper for standardized error responses.

    Provides consistent error handling and logging across API endpoints
    with structured error messages and status codes.

    Attributes:
        operation (str): Operation being performed (e.g., "create", "update", "delete")
        resource_type (str): Type of resource (e.g., "product", "inventory", "order")

    Example:
        ```python
        from shared.api.dependencies import ErrorContext

        @router.post("/products")
        async def create_product(product_data: ProductCreate):
            error_context = ErrorContext("create", "product")
            try:
                product = await service.create_product(product_data)
                return product
            except ValueError as e:
                raise error_context.create_error_response(e, status_code=400)
            except Exception as e:
                raise error_context.create_error_response(e)
        ```

    Methods:
        create_error_response(error, status_code=500): Create HTTPException with logging

    Error Response Format:
        ```json
        {
            "detail": "Failed to create product"
        }
        ```

    Logging:
        Automatically logs errors with structured context:
        - operation: What was being attempted
        - resource_type: What resource was involved
        - error: Error message
        - error_type: Exception class name

    Status Codes:
        - 400: Bad Request (validation errors)
        - 404: Not Found (resource doesn't exist)
        - 409: Conflict (duplicate resources)
        - 500: Internal Server Error (unexpected errors)

    Notes:
        - Always log before creating HTTPException
        - Provides consistent error messages across endpoints
        - Useful for debugging with structured logs
    """

    def __init__(self, operation: str, resource_type: str):
        self.operation = operation
        self.resource_type = resource_type

    def create_error_response(self, error: Exception, status_code: int = 500) -> HTTPException:
        """
        Create standardized error response with logging.

        Args:
            error: The exception that occurred
            status_code: HTTP status code (default: 500)

        Returns:
            HTTPException with formatted error message

        Example:
            >>> context = ErrorContext("update", "inventory")
            >>> exc = ValueError("Invalid quantity")
            >>> http_exc = context.create_error_response(exc, status_code=400)
            >>> http_exc.status_code
            400
            >>> http_exc.detail
            'Failed to update inventory'

        Notes:
            - Logs error details before returning exception
            - Error message follows pattern: "Failed to {operation} {resource_type}"
            - Original error details logged but not exposed to client (security)
        """
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
    """
    Utility class for formatting standardized API responses.

    Provides consistent response formats across all API endpoints for lists,
    success messages, and paginated data.

    Methods:
        format_list_response(): Format paginated list responses
        format_success_response(): Format success operation responses

    Example:
        ```python
        from shared.api.dependencies import ResponseFormatter, PaginationParams

        @router.get("/products")
        async def list_products(
            pagination: PaginationParams = Depends(),
            search: SearchParams = Depends()
        ):
            products = await get_products(
                skip=pagination.skip,
                limit=pagination.limit,
                filters=search.to_dict()
            )
            total = await count_products(filters=search.to_dict())

            return ResponseFormatter.format_list_response(
                items=products,
                total=total,
                pagination=pagination,
                search=search
            )
        ```

    Response Format (list):
        ```json
        {
            "items": [...],
            "pagination": {
                "skip": 0,
                "limit": 50,
                "total": 1250,
                "has_more": true
            },
            "filters": {
                "brand": "Nike",
                "min_price": 100.0
            }
        }
        ```

    Response Format (success):
        ```json
        {
            "message": "Product created successfully",
            "data": {...},
            "operation": "create"
        }
        ```

    Notes:
        - All static methods (no instance needed)
        - Use for consistent response structure
        - Pagination metadata automatically calculated
    """

    @staticmethod
    def format_list_response(
        items: list, total: int, pagination: PaginationParams, search: SearchParams = None
    ) -> Dict[str, Any]:
        """
        Format standardized paginated list response.

        Args:
            items: List of items for current page
            total: Total count of items (all pages)
            pagination: Pagination parameters used
            search: Search/filter parameters used (optional)

        Returns:
            Dict with items, pagination metadata, and applied filters

        Example:
            >>> items = [{"id": 1, "name": "Product 1"}]
            >>> pagination = PaginationParams(skip=0, limit=50)
            >>> response = ResponseFormatter.format_list_response(
            ...     items=items,
            ...     total=1250,
            ...     pagination=pagination
            ... )
            >>> response['pagination']['has_more']
            True

        Response Fields:
            - items: List of data objects
            - pagination.skip: Current offset
            - pagination.limit: Page size
            - pagination.total: Total item count
            - pagination.has_more: True if more pages exist
            - filters: Applied search/filter parameters (null if none)
        """
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
        """
        Format standardized success response.

        Args:
            message: Success message to display
            data: Optional data payload
            operation: Optional operation name (e.g., "create", "update", "delete")

        Returns:
            Dict with message and optional data/operation

        Example:
            >>> response = ResponseFormatter.format_success_response(
            ...     message="Product updated successfully",
            ...     data={"id": "uuid", "name": "Nike Air Max"},
            ...     operation="update"
            ... )
            >>> response['message']
            'Product updated successfully'

        Response Fields:
            - message: Human-readable success message (always present)
            - data: Result data (only if provided)
            - operation: Operation type (only if provided)

        Use Cases:
            - Create: Return created resource data
            - Update: Return updated resource data
            - Delete: No data, just confirmation message
            - Batch operations: Return statistics in data
        """
        response = {"message": message}
        if data is not None:
            response["data"] = data
        if operation:
            response["operation"] = operation
        return response


# Dependency factory for creating parameterized dependencies
class DependencyFactory:
    """
    Factory class for creating parameterized FastAPI dependencies.

    Provides utility methods to generate dependency functions dynamically
    for services, validators, and other reusable patterns.

    Methods:
        create_service_dependency(service_class): Generate service dependency
        create_validation_dependency(validator_func): Generate validation dependency

    Example:
        ```python
        from shared.api.dependencies import DependencyFactory
        from domains.products.services.product_service import ProductService

        # Create service dependency dynamically
        get_product_service = DependencyFactory.create_service_dependency(
            ProductService
        )

        @router.get("/products")
        async def list_products(
            service: ProductService = Depends(get_product_service)
        ):
            return await service.list_products()

        # Create validation dependency
        def validate_positive(value: int) -> bool:
            return value > 0

        validate_positive_int = DependencyFactory.create_validation_dependency(
            validate_positive
        )

        @router.get("/products/{quantity}")
        async def get_products(
            quantity: int = Depends(validate_positive_int)
        ):
            return await get_n_products(quantity)
        ```

    Use Cases:
        - Dynamically generate dependencies for multiple similar services
        - Create reusable validation dependencies
        - Reduce boilerplate code for common patterns

    Notes:
        - All static methods (no instance needed)
        - Generated dependencies are proper FastAPI Depends() functions
        - Useful for code generation and meta-programming
    """

    @staticmethod
    def create_service_dependency(service_class):
        """
        Create a FastAPI dependency for any service class.

        Args:
            service_class: Service class to instantiate (must accept AsyncSession)

        Returns:
            Async function suitable for use with Depends()

        Example:
            >>> from domains.pricing.services.pricing_engine import PricingEngine
            >>> get_pricing_service = DependencyFactory.create_service_dependency(
            ...     PricingEngine
            ... )
            >>> # Use in endpoint:
            >>> @router.post("/calculate-price")
            >>> async def calculate(
            ...     service: PricingEngine = Depends(get_pricing_service)
            ... ):
            ...     return await service.calculate_price(...)

        Requirements:
            - service_class must accept AsyncSession as first argument
            - service_class must be a class (not instance)

        Benefits:
            - Reduces repetitive dependency definitions
            - Ensures consistent service instantiation pattern
            - Automatic database session injection
        """

        async def get_service(db: AsyncSession = Depends(get_db_session)):
            return service_class(db)

        return get_service

    @staticmethod
    def create_validation_dependency(validator_func):
        """
        Create a FastAPI dependency from a validation function.

        Args:
            validator_func: Function that returns True if input is valid

        Returns:
            Async function suitable for use with Depends()

        Example:
            >>> def is_valid_sku(sku: str) -> bool:
            ...     return len(sku) >= 5 and sku.isalnum()
            >>>
            >>> validate_sku = DependencyFactory.create_validation_dependency(
            ...     is_valid_sku
            ... )
            >>>
            >>> @router.get("/products/{sku}")
            >>> async def get_product(sku: str = Depends(validate_sku)):
            ...     return await find_product_by_sku(sku)

        Validation Rules:
            - validator_func must return bool
            - True = validation passed
            - False = raises 400 Bad Request

        Error Response:
            ```json
            {
                "detail": "Validation failed"
            }
            ```

        Notes:
            - Use FastAPI's Query/Path validators for simple cases
            - This is for complex custom validation logic
            - Can be combined with other dependencies
        """

        async def validate_input(value: Any):
            if not validator_func(value):
                raise HTTPException(status_code=400, detail="Validation failed")
            return value

        return validate_input
