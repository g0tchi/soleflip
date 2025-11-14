"""
Unit tests for API types
Testing Pydantic models and utility methods for 100% coverage
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from shared.api.responses import (
    BulkOperationResponse,
    SyncOperationResponse,
)
from shared.types.api_types import (
    BaseResponse,
    ErrorResponse,
    HealthCheckResponse,
    PaginatedResponse,
    PaginationInfo,
    SuccessResponse,
    ValidationErrorResponse,
)


class TestPaginationInfo:
    """Test PaginationInfo model and create method edge cases"""

    def test_pagination_info_direct_creation(self):
        """Test direct PaginationInfo creation with validation"""
        pagination = PaginationInfo(
            skip=10, limit=20, total=100, has_more=True, page=1, total_pages=5
        )

        assert pagination.skip == 10
        assert pagination.limit == 20
        assert pagination.total == 100
        assert pagination.has_more is True
        assert pagination.page == 1
        assert pagination.total_pages == 5

    def test_pagination_create_zero_skip_zero_limit_edge_case(self):
        """Test edge case: zero skip, minimum limit"""
        pagination = PaginationInfo.create(skip=0, limit=1, total=10)

        assert pagination.page == 1  # (0 // 1) + 1 = 1
        assert pagination.total_pages == 10  # max(1, (10 + 1 - 1) // 1) = 10
        assert pagination.has_more is True  # 0 + 1 < 10

    def test_pagination_create_large_skip_calculations(self):
        """Test edge case: large skip values for page calculation"""
        pagination = PaginationInfo.create(skip=99, limit=10, total=100)

        assert pagination.page == 10  # (99 // 10) + 1 = 10
        assert pagination.total_pages == 10  # max(1, (100 + 10 - 1) // 10) = 10
        assert pagination.has_more is False  # 99 + 10 >= 100

    def test_pagination_create_total_pages_edge_cases(self):
        """Test total pages calculation edge cases"""
        # Case 1: total=0 should give total_pages=1
        pagination = PaginationInfo.create(skip=0, limit=10, total=0)
        assert pagination.total_pages == 1  # max(1, (0 + 10 - 1) // 10) = max(1, 0) = 1

        # Case 2: total=1, limit=1 should give total_pages=1
        pagination = PaginationInfo.create(skip=0, limit=1, total=1)
        assert pagination.total_pages == 1  # max(1, (1 + 1 - 1) // 1) = 1

        # Case 3: total slightly over limit boundary
        pagination = PaginationInfo.create(skip=0, limit=10, total=11)
        assert pagination.total_pages == 2  # max(1, (11 + 10 - 1) // 10) = 2

    def test_pagination_create_has_more_boundary_conditions(self):
        """Test has_more calculation boundary conditions"""
        # Case 1: exactly at boundary (skip + limit == total)
        pagination = PaginationInfo.create(skip=90, limit=10, total=100)
        assert pagination.has_more is False  # 90 + 10 == 100, so not < 100

        # Case 2: one less than boundary
        pagination = PaginationInfo.create(skip=89, limit=10, total=100)
        assert pagination.has_more is True  # 89 + 10 < 100

        # Case 3: one more than boundary
        pagination = PaginationInfo.create(skip=91, limit=10, total=100)
        assert pagination.has_more is False  # 91 + 10 > 100

    def test_pagination_info_field_validation(self):
        """Test PaginationInfo field validation"""
        # Test negative skip
        with pytest.raises(ValidationError):
            PaginationInfo(skip=-1, limit=10, total=100, has_more=True, page=1, total_pages=10)

        # Test zero limit
        with pytest.raises(ValidationError):
            PaginationInfo(skip=0, limit=0, total=100, has_more=True, page=1, total_pages=10)

        # Test negative total
        with pytest.raises(ValidationError):
            PaginationInfo(skip=0, limit=10, total=-1, has_more=True, page=1, total_pages=10)

        # Test zero page
        with pytest.raises(ValidationError):
            PaginationInfo(skip=0, limit=10, total=100, has_more=True, page=0, total_pages=10)

        # Test zero total_pages
        with pytest.raises(ValidationError):
            PaginationInfo(skip=0, limit=10, total=100, has_more=True, page=1, total_pages=0)


class TestPaginatedResponse:
    """Test PaginatedResponse model"""

    def test_paginated_response_basic(self):
        """Test basic paginated response"""
        pagination = PaginationInfo.create(skip=0, limit=10, total=25)
        items = [{"id": 1}, {"id": 2}]

        response = PaginatedResponse[dict](items=items, pagination=pagination)

        assert response.items == items
        assert response.pagination == pagination
        assert response.request_id is None

    def test_paginated_response_with_optional_fields(self):
        """Test paginated response with optional fields"""
        pagination = PaginationInfo.create(skip=10, limit=5, total=50)
        items = ["item1", "item2"]

        response = PaginatedResponse[str](
            items=items,
            pagination=pagination,
            request_id="req-123",
        )

        assert response.items == items
        assert response.request_id == "req-123"


class TestBaseResponse:
    """Test BaseResponse model"""

    def test_base_response_basic(self):
        """Test basic base response"""
        response = BaseResponse()

        assert response.request_id is None
        assert response.timestamp is not None

    def test_base_response_with_request_id(self):
        """Test base response with request ID"""
        response = BaseResponse(request_id="req-123")

        assert response.request_id == "req-123"
        assert response.timestamp is not None


class TestSuccessResponse:
    """Test SuccessResponse model"""

    def test_success_response_basic(self):
        """Test basic success response"""
        response = SuccessResponse(success=True, message="Operation completed", data={"id": 123})

        assert response.success is True
        assert response.message == "Operation completed"
        assert response.data == {"id": 123}

    def test_success_response_without_data(self):
        """Test success response without data"""
        response = SuccessResponse(success=True, message="Delete completed")

        assert response.success is True
        assert response.data is None


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_error_response_basic(self):
        """Test basic error response"""
        response = ErrorResponse(
            success=False, error={"message": "Something went wrong", "code": "ERR_001"}
        )

        assert response.success is False
        assert response.error["message"] == "Something went wrong"
        assert response.error["code"] == "ERR_001"

    def test_error_response_with_details(self):
        """Test error response with details"""
        response = ErrorResponse(
            success=False,
            error={
                "message": "Validation error",
                "code": "VALIDATION_FAILED",
                "details": {"field": "email", "value": "invalid"},
            },
        )

        assert response.error["message"] == "Validation error"
        assert response.error["code"] == "VALIDATION_FAILED"
        assert response.error["details"]["field"] == "email"


class TestValidationErrorResponse:
    """Test ValidationErrorResponse model"""

    def test_validation_error_response(self):
        """Test validation error response"""
        response = ValidationErrorResponse(
            success=False,
            error={"message": "Validation failed", "code": "VALIDATION_ERROR"},
            field_errors={"name": ["Required field"], "email": ["Invalid format"]},
        )

        assert response.success is False
        assert response.error["message"] == "Validation failed"
        assert len(response.field_errors) == 2
        assert "name" in response.field_errors
        assert "email" in response.field_errors
        assert response.field_errors["name"][0] == "Required field"
        assert response.field_errors["email"][0] == "Invalid format"


class TestBulkOperationResponse:
    """Test BulkOperationResponse model"""

    def test_bulk_operation_response_basic(self):
        """Test basic bulk operation response"""
        response = BulkOperationResponse(
            success=True,
            operation="import_products",
            total_items=100,
            successful_items=95,
            failed_items=5,
            errors=[],
            processing_time_seconds=0.0,
        )

        assert response.success is True
        assert response.operation == "import_products"
        assert response.total_items == 100
        assert response.successful_items == 95
        assert response.failed_items == 5
        assert response.errors == []
        assert response.processing_time_seconds == 0.0

    def test_bulk_operation_response_with_errors(self):
        """Test bulk operation response with errors"""
        errors = [{"row": 5, "error": "Invalid data"}]

        response = BulkOperationResponse(
            success=False,
            operation="import_orders",
            total_items=50,
            successful_items=40,
            failed_items=10,
            errors=errors,
            processing_time_seconds=25.5,
            request_id="bulk-123",
        )

        assert response.success is False
        assert response.errors == errors
        assert response.processing_time_seconds == 25.5
        assert response.request_id == "bulk-123"


class TestSyncOperationResponse:
    """Test SyncOperationResponse model"""

    def test_sync_operation_response(self):
        """Test sync operation response"""
        last_sync = datetime.now(timezone.utc)
        next_sync = datetime.now(timezone.utc)

        response = SyncOperationResponse(
            success=True,
            operation="stockx_sync",
            service_name="StockX API",
            items_synced=100,
            items_created=20,
            items_updated=80,
            items_skipped=0,
            sync_duration_seconds=5.5,
            last_sync_timestamp=last_sync,
            next_sync_timestamp=next_sync,
        )

        assert response.success is True
        assert response.operation == "stockx_sync"
        assert response.service_name == "StockX API"
        assert response.items_synced == 100
        assert response.items_created == 20
        assert response.items_updated == 80
        assert response.items_skipped == 0
        assert response.sync_duration_seconds == 5.5
        assert response.last_sync_timestamp == last_sync
        assert response.next_sync_timestamp == next_sync


class TestHealthCheckResponse:
    """Test HealthCheckResponse model"""

    def test_health_check_response(self):
        """Test health check response"""
        components = {
            "database": {"status": "healthy", "latency_ms": 5},
            "redis": {"status": "healthy", "latency_ms": 2},
        }
        timestamp = datetime.now(timezone.utc)

        response = HealthCheckResponse(
            status="healthy",
            timestamp=timestamp,
            version="0.9.0",
            environment="production",
            components=components,
        )

        assert response.status == "healthy"
        assert response.components == components
        assert response.version == "0.9.0"
        assert response.environment == "production"
        assert response.timestamp == timestamp
