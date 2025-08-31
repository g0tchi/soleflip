"""
Custom Exception Classes and Global Error Handling
Production-ready error handling with proper logging and user feedback
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class ErrorCode(Enum):
    """Standardized error codes"""

    # Validation errors (400x)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # Authentication/Authorization errors (401x/403x)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"

    # Resource errors (404x)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"

    # Business logic errors (409x)
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"

    # Import/Processing errors (422x)
    IMPORT_VALIDATION_FAILED = "IMPORT_VALIDATION_FAILED"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"

    # Rate limiting (429x)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (500x)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class SoleFlipException(Exception):
    """Base exception for all SoleFlipper errors"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
        super().__init__(self.message)


class ValidationException(SoleFlipException):
    """Exception for validation errors"""

    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"field_errors": field_errors or {}, **(details or {})},
            user_message="The provided data is invalid. Please check your input and try again.",
        )
        self.field_errors = field_errors or {}


class ResourceNotFoundException(SoleFlipException):
    """Exception for resource not found errors"""

    def __init__(
        self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id, **(details or {})},
            user_message=f"The requested {resource_type.lower()} could not be found.",
        )


class DuplicateResourceException(SoleFlipException):
    """Exception for duplicate resource errors"""

    def __init__(
        self,
        resource_type: str,
        conflicting_field: str,
        conflicting_value: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"{resource_type} with {conflicting_field} '{conflicting_value}' already exists",
            error_code=ErrorCode.DUPLICATE_RESOURCE,
            status_code=409,
            details={
                "resource_type": resource_type,
                "conflicting_field": conflicting_field,
                "conflicting_value": conflicting_value,
                **(details or {}),
            },
            user_message=f"A {resource_type.lower()} with this {conflicting_field} already exists.",
        )


class ImportProcessingException(SoleFlipException):
    """Exception for import/processing errors"""

    def __init__(
        self,
        message: str,
        batch_id: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.IMPORT_VALIDATION_FAILED,
            status_code=422,
            details={
                "batch_id": batch_id,
                "validation_errors": validation_errors or [],
                **(details or {}),
            },
            user_message="There was an error processing your import. Please check the file format and try again.",
        )
        self.batch_id = batch_id
        self.validation_errors = validation_errors or []


class BusinessRuleException(SoleFlipException):
    """Exception for business rule violations"""

    def __init__(self, message: str, rule: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            status_code=409,
            details={"violated_rule": rule, **(details or {})},
            user_message="This operation violates a business rule. Please check your data and try again.",
        )


class DatabaseException(SoleFlipException):
    """Exception for database-related errors"""

    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details={"operation": operation, **(details or {})},
            user_message="A database error occurred. Please try again later.",
        )


class ExternalServiceException(SoleFlipException):
    """Exception for external service errors"""

    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=502,
            details={
                "service_name": service_name,
                "service_status_code": status_code,
                **(details or {}),
            },
            user_message=f"An error occurred while communicating with {service_name}. Please try again later.",
        )


# Global Exception Handlers
async def soleflip_exception_handler(request: Request, exc: SoleFlipException) -> JSONResponse:
    """Handle SoleFlipper custom exceptions"""

    # Log the error with full context
    logger.error(
        "SoleFlipper exception occurred",
        error_code=exc.error_code.value,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
        method=request.method,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )

    # Return structured error response
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code.value,
                "message": exc.user_message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """Handle validation exceptions with field-level errors"""

    logger.warning(
        "Validation error occurred",
        message=exc.message,
        field_errors=exc.field_errors,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "field_errors": exc.field_errors,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""

    # Log the full exception with traceback
    logger.error(
        "Unexpected exception occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    # Don't expose internal error details to users
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""

    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


# Error handling decorators
def handle_database_errors(func):
    """Decorator to handle database errors"""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Check if it's a database-related error
            error_message = str(e).lower()
            if any(
                db_error in error_message
                for db_error in ["connection", "database", "relation", "column", "constraint"]
            ):
                raise DatabaseException(
                    message=f"Database error in {func.__name__}: {str(e)}",
                    operation=func.__name__,
                    details={"original_error": str(e)},
                )
            else:
                # Re-raise as-is if not a database error
                raise

    return wrapper


def handle_validation_errors(func):
    """Decorator to handle validation errors"""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            raise ValidationException(message=str(e), details={"function": func.__name__})
        except TypeError as e:
            raise ValidationException(
                message=f"Type error: {str(e)}", details={"function": func.__name__}
            )

    return wrapper


# Utility functions
def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": {
            "code": error_code.value,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }


def log_and_raise(exception_class: type, message: str, **kwargs):
    """Log an error and raise exception"""
    logger.error(message, **kwargs)
    raise exception_class(message, **kwargs)
