"""
Selling Domain Exception Handling
Specialized exceptions for selling operations with security-aware error responses
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standardized error response model"""
    error: str
    message: str
    field: Optional[str] = None
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SellingBaseException(HTTPException):
    """Base exception for selling domain with security-aware responses"""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        field: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        # Sanitize error details for security
        sanitized_detail = self._sanitize_error_detail(detail)

        error_response = {
            "error": self.__class__.__name__,
            "message": sanitized_detail,
            "error_code": error_code,
            "field": field
        }

        super().__init__(status_code=status_code, detail=error_response, headers=headers)

    def _sanitize_error_detail(self, detail: str) -> str:
        """Remove sensitive information from error messages"""
        # Remove potential API keys, tokens, or sensitive data patterns
        sensitive_patterns = [
            r'api[_-]?key[_-]?[\w\d]+',
            r'token[_-]?[\w\d]+',
            r'secret[_-]?[\w\d]+',
            r'password[_-]?[\w\d]+',
            r'Bearer\s+[\w\d\-_\.]+',
            r'Basic\s+[\w\d\+/=]+',
        ]

        sanitized = detail
        for pattern in sensitive_patterns:
            import re
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)

        return sanitized


class ListingCreationError(SellingBaseException):
    """Error creating StockX listing"""

    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="LISTING_CREATION_FAILED",
            field=field
        )


class PriceUpdateError(SellingBaseException):
    """Error updating listing price"""

    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="PRICE_UPDATE_FAILED",
            field=field
        )


class ListingNotFoundError(SellingBaseException):
    """Listing not found in database"""

    def __init__(self, listing_id: str):
        super().__init__(
            detail=f"Listing not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="LISTING_NOT_FOUND",
            field="listing_id"
        )


class OpportunityNotFoundError(SellingBaseException):
    """QuickFlip opportunity not found"""

    def __init__(self, opportunity_id: str):
        super().__init__(
            detail=f"QuickFlip opportunity not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="OPPORTUNITY_NOT_FOUND",
            field="opportunity_id"
        )


class StockXAPIError(SellingBaseException):
    """StockX API communication error"""

    def __init__(self, detail: str, api_status: Optional[int] = None):
        # Don't expose internal API details in production
        public_detail = "External service temporarily unavailable"

        super().__init__(
            detail=public_detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_API_ERROR"
        )


class BulkOperationError(SellingBaseException):
    """Error in bulk listing operations"""

    def __init__(self, detail: str, failed_count: int = 0, total_count: int = 0):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_207_MULTI_STATUS,
            error_code="BULK_OPERATION_PARTIAL_FAILURE"
        )


class InsufficientPermissionsError(SellingBaseException):
    """User lacks required permissions"""

    def __init__(self, action: str):
        super().__init__(
            detail=f"Insufficient permissions for action: {action}",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="INSUFFICIENT_PERMISSIONS"
        )


class RateLimitExceededError(SellingBaseException):
    """Rate limit exceeded for API calls"""

    def __init__(self, retry_after: Optional[int] = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            detail="Rate limit exceeded. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            headers=headers
        )


class ValidationError(SellingBaseException):
    """Enhanced validation error with field-specific details"""

    def __init__(self, detail: str, field: Optional[str] = None, validation_errors: Optional[Dict] = None):
        error_detail = detail
        if validation_errors:
            # Sanitize validation error details
            sanitized_errors = {
                k: v for k, v in validation_errors.items()
                if not any(sensitive in k.lower() for sensitive in ['password', 'token', 'key', 'secret'])
            }
            if sanitized_errors:
                error_detail += f". Validation details: {sanitized_errors}"

        super().__init__(
            detail=error_detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            field=field
        )


class DatabaseError(SellingBaseException):
    """Database operation error"""

    def __init__(self, operation: str):
        super().__init__(
            detail=f"Database operation failed: {operation}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR"
        )


class ConfigurationError(SellingBaseException):
    """Service configuration error"""

    def __init__(self, component: str):
        super().__init__(
            detail=f"Service configuration error: {component}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONFIGURATION_ERROR"
        )


# Exception Handler Utilities
def handle_database_error(operation: str, original_error: Exception) -> DatabaseError:
    """Convert database exceptions to standardized format"""
    import structlog
    logger = structlog.get_logger(__name__)

    # Log the actual error for debugging (server-side only)
    logger.error(
        "Database operation failed",
        operation=operation,
        error_type=type(original_error).__name__,
        error_message=str(original_error)
    )

    return DatabaseError(operation)


def handle_api_error(service: str, original_error: Exception) -> StockXAPIError:
    """Convert external API errors to standardized format"""
    import structlog
    logger = structlog.get_logger(__name__)

    # Log detailed error for debugging
    logger.error(
        "External API error",
        service=service,
        error_type=type(original_error).__name__,
        error_message=str(original_error)
    )

    return StockXAPIError(f"{service} API error")


def create_field_validation_error(field: str, value: Any, constraint: str) -> ValidationError:
    """Create validation error for specific field constraints"""
    return ValidationError(
        detail=f"Invalid value for {field}: {constraint}",
        field=field
    )