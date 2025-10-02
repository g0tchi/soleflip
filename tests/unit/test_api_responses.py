"""
Unit tests for API response models and utilities
Testing response builders and models for 100% coverage
"""

from datetime import datetime, timezone

from shared.api.responses import (
    BaseResponse,
    SuccessResponse,
    ErrorResponse,
    PaginationInfo,
    PaginatedResponse,
    ResponseBuilder,
    ValidationErrorResponse,
    BulkOperationResponse,
    SyncOperationResponse,
    create_success_response,
    create_error_response,
    RESPONSE_EXAMPLES
)


class TestBaseResponse:
    """Test BaseResponse model"""

    def test_base_response_default_timestamp(self):
        """Test that BaseResponse creates default timestamp"""
        response = BaseResponse()

        assert isinstance(response.timestamp, datetime)
        assert response.request_id is None

    def test_base_response_with_request_id(self):
        """Test BaseResponse with request_id"""
        request_id = "test-req-123"
        response = BaseResponse(request_id=request_id)

        assert response.request_id == request_id


class TestPaginationInfo:
    """Test PaginationInfo model and factory method"""

    def test_pagination_create_basic(self):
        """Test basic pagination creation"""
        pagination = PaginationInfo.create(skip=0, limit=10, total=25)

        assert pagination.skip == 0
        assert pagination.limit == 10
        assert pagination.total == 25
        assert pagination.page == 1
        assert pagination.total_pages == 3
        assert pagination.has_more is True

    def test_pagination_create_last_page(self):
        """Test pagination on last page"""
        pagination = PaginationInfo.create(skip=20, limit=10, total=25)

        assert pagination.skip == 20
        assert pagination.limit == 10
        assert pagination.total == 25
        assert pagination.page == 3
        assert pagination.total_pages == 3
        assert pagination.has_more is False

    def test_pagination_create_exact_pages(self):
        """Test pagination with exact page divisions"""
        pagination = PaginationInfo.create(skip=0, limit=10, total=30)

        assert pagination.total_pages == 3
        assert pagination.has_more is True

    def test_pagination_create_single_page(self):
        """Test pagination with single page"""
        pagination = PaginationInfo.create(skip=0, limit=10, total=5)

        assert pagination.page == 1
        assert pagination.total_pages == 1
        assert pagination.has_more is False

    def test_pagination_create_zero_total(self):
        """Test pagination with zero total items"""
        pagination = PaginationInfo.create(skip=0, limit=10, total=0)

        assert pagination.page == 1
        assert pagination.total_pages == 1
        assert pagination.has_more is False


class TestResponseBuilder:
    """Test ResponseBuilder utility methods"""

    def test_success_response_basic(self):
        """Test basic success response"""
        response = ResponseBuilder.success("Operation completed", {"id": 123})

        assert isinstance(response, SuccessResponse)
        assert response.success is True
        assert response.message == "Operation completed"
        assert response.data == {"id": 123}

    def test_success_response_with_request_id(self):
        """Test success response with request_id"""
        request_id = "req-456"
        response = ResponseBuilder.success("Done", request_id=request_id)

        assert response.request_id == request_id

    def test_error_response_basic(self):
        """Test basic error response"""
        response = ResponseBuilder.error("VALIDATION_ERROR", "Invalid input")

        assert isinstance(response, ErrorResponse)
        assert response.success is False
        assert response.error["code"] == "VALIDATION_ERROR"
        assert response.error["message"] == "Invalid input"
        assert response.error["status_code"] == 500
        assert response.error["details"] == {}

    def test_error_response_with_details(self):
        """Test error response with details and status code"""
        details = {"field": "email", "value": "invalid"}
        response = ResponseBuilder.error(
            "FIELD_ERROR",
            "Field validation failed",
            details=details,
            status_code=400,
            request_id="req-789"
        )

        assert response.error["details"] == details
        assert response.error["status_code"] == 400
        assert response.request_id == "req-789"

    def test_paginated_response(self):
        """Test paginated response builder"""
        items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        filters = {"status": "active"}

        response = ResponseBuilder.paginated(
            items=items,
            skip=10,
            limit=5,
            total=50,
            filters=filters,
            request_id="req-page"
        )

        assert isinstance(response, PaginatedResponse)
        assert response.items == items
        assert response.filters == filters
        assert response.request_id == "req-page"
        assert response.pagination.skip == 10
        assert response.pagination.limit == 5
        assert response.pagination.total == 50

    def test_validation_error_response(self):
        """Test validation error response builder"""
        field_errors = {
            "email": ["Invalid email format"],
            "age": ["Must be positive", "Required field"]
        }

        response = ResponseBuilder.validation_error(
            "Validation failed",
            field_errors,
            request_id="req-validation"
        )

        assert isinstance(response, ValidationErrorResponse)
        assert response.success is False
        assert response.error["code"] == "VALIDATION_ERROR"
        assert response.field_errors == field_errors
        assert response.request_id == "req-validation"

    def test_bulk_operation_response(self):
        """Test bulk operation response builder"""
        errors = [{"row": 5, "error": "Invalid data"}]

        response = ResponseBuilder.bulk_operation(
            operation="import_products",
            total_items=100,
            successful_items=95,
            failed_items=5,
            errors=errors,
            processing_time=12.5,
            request_id="req-bulk"
        )

        assert isinstance(response, BulkOperationResponse)
        assert response.success is True
        assert response.operation == "import_products"
        assert response.total_items == 100
        assert response.successful_items == 95
        assert response.failed_items == 5
        assert response.errors == errors
        assert response.processing_time_seconds == 12.5
        assert response.request_id == "req-bulk"

    def test_bulk_operation_response_defaults(self):
        """Test bulk operation response with default values"""
        response = ResponseBuilder.bulk_operation(
            operation="test_op",
            total_items=10,
            successful_items=10,
            failed_items=0
        )

        assert response.errors == []
        assert response.processing_time_seconds == 0.0
        assert response.request_id is None

    def test_sync_operation_response(self):
        """Test sync operation response builder"""
        stats = {
            "synced": 100,
            "created": 20,
            "updated": 75,
            "skipped": 5
        }
        next_sync = datetime.now(timezone.utc)

        response = ResponseBuilder.sync_operation(
            operation="stockx_sync",
            service_name="StockX API",
            stats=stats,
            sync_duration=45.2,
            next_sync=next_sync,
            request_id="req-sync"
        )

        assert isinstance(response, SyncOperationResponse)
        assert response.success is True
        assert response.operation == "stockx_sync"
        assert response.service_name == "StockX API"
        assert response.items_synced == 100
        assert response.items_created == 20
        assert response.items_updated == 75
        assert response.items_skipped == 5
        assert response.sync_duration_seconds == 45.2
        assert response.next_sync_timestamp == next_sync
        assert response.request_id == "req-sync"
        assert isinstance(response.last_sync_timestamp, datetime)

    def test_sync_operation_response_missing_stats(self):
        """Test sync operation response with missing stats"""
        stats = {"created": 10}  # Missing other keys

        response = ResponseBuilder.sync_operation(
            operation="partial_sync",
            service_name="Test Service",
            stats=stats
        )

        assert response.items_synced == 0
        assert response.items_created == 10
        assert response.items_updated == 0
        assert response.items_skipped == 0
        assert response.sync_duration_seconds == 0.0
        assert response.next_sync_timestamp is None


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility"""

    def test_create_success_response(self):
        """Test create_success_response function"""
        response = create_success_response("Success", {"result": "ok"}, "req-123")

        assert isinstance(response, SuccessResponse)
        assert response.message == "Success"
        assert response.data == {"result": "ok"}
        assert response.request_id == "req-123"

    def test_create_error_response(self):
        """Test create_error_response function"""
        details = {"trace": "stack_trace"}
        response = create_error_response(
            "SERVER_ERROR",
            "Internal error",
            details=details,
            status_code=500,
            request_id="req-error"
        )

        assert isinstance(response, ErrorResponse)
        assert response.error["code"] == "SERVER_ERROR"
        assert response.error["message"] == "Internal error"
        assert response.error["details"] == details
        assert response.error["status_code"] == 500
        assert response.request_id == "req-error"


class TestResponseExamples:
    """Test that response examples are valid"""

    def test_response_examples_exist(self):
        """Test that response examples are defined"""
        assert "success_example" in RESPONSE_EXAMPLES
        assert "error_example" in RESPONSE_EXAMPLES
        assert "paginated_example" in RESPONSE_EXAMPLES

    def test_success_example_structure(self):
        """Test success example has correct structure"""
        example = RESPONSE_EXAMPLES["success_example"]

        assert example["success"] is True
        assert "message" in example
        assert "data" in example
        assert "timestamp" in example
        assert "request_id" in example

    def test_error_example_structure(self):
        """Test error example has correct structure"""
        example = RESPONSE_EXAMPLES["error_example"]

        assert example["success"] is False
        assert "error" in example
        assert "code" in example["error"]
        assert "message" in example["error"]
        assert "details" in example["error"]
        assert "status_code" in example["error"]

    def test_paginated_example_structure(self):
        """Test paginated example has correct structure"""
        example = RESPONSE_EXAMPLES["paginated_example"]

        assert "items" in example
        assert "pagination" in example
        assert "filters" in example
        assert isinstance(example["items"], list)
        assert len(example["items"]) == 2

        pagination = example["pagination"]
        assert all(key in pagination for key in [
            "skip", "limit", "total", "has_more", "page", "total_pages"
        ])