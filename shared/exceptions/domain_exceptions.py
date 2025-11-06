"""
Domain-specific exceptions for improved error handling and debugging.
These replace generic Exception handlers with specific, meaningful error types.
"""

from typing import Any, Dict, Optional


class DomainException(Exception):
    """Base exception for all domain-specific errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Database Operation Exceptions
class DatabaseOperationException(DomainException):
    """Raised when database operations fail"""

    pass


class RecordNotFoundException(DatabaseOperationException):
    """Raised when a required database record is not found"""

    pass


class DuplicateRecordException(DatabaseOperationException):
    """Raised when attempting to create duplicate records"""

    pass


class DatabaseConnectionException(DatabaseOperationException):
    """Raised when database connection fails"""

    pass


# External API Exceptions
class ExternalApiException(DomainException):
    """Base exception for external API errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.status_code = status_code


class StockXApiException(ExternalApiException):
    """Raised for StockX API specific errors"""

    pass


class AuthenticationException(ExternalApiException):
    """Raised when API authentication fails"""

    pass


class RateLimitException(ExternalApiException):
    """Raised when API rate limits are exceeded"""

    pass


# Data Processing Exceptions
class DataProcessingException(DomainException):
    """Base exception for data processing errors"""

    pass


class ValidationException(DataProcessingException):
    """Raised when data validation fails"""

    pass


class TransformationException(DataProcessingException):
    """Raised when data transformation fails"""

    pass


class ParseException(DataProcessingException):
    """Raised when data parsing fails"""

    pass


# Business Logic Exceptions
class BusinessLogicException(DomainException):
    """Base exception for business logic violations"""

    pass


class InsufficientInventoryException(BusinessLogicException):
    """Raised when inventory is insufficient for operation"""

    pass


class InvalidPriceException(BusinessLogicException):
    """Raised when price validation fails"""

    pass


class OrderProcessingException(BusinessLogicException):
    """Raised when order processing fails"""

    pass


# Import/Export Exceptions
class ImportException(DomainException):
    """Base exception for import operations"""

    pass


class FileFormatException(ImportException):
    """Raised when file format is invalid or unsupported"""

    pass


class BatchProcessingException(ImportException):
    """Raised when batch processing fails"""

    pass


# Service Integration Exceptions
class ServiceIntegrationException(DomainException):
    """Base exception for service integration errors"""

    pass


class ServiceUnavailableException(ServiceIntegrationException):
    """Raised when required service is unavailable"""

    pass


class ConfigurationException(ServiceIntegrationException):
    """Raised when service configuration is invalid"""

    pass


# Common exception mappings for quick migration
COMMON_EXCEPTION_MAPPINGS = {
    # Database related
    "connection": DatabaseConnectionException,
    "timeout": DatabaseConnectionException,
    "not found": RecordNotFoundException,
    "duplicate": DuplicateRecordException,
    # API related
    "401": AuthenticationException,
    "403": AuthenticationException,
    "429": RateLimitException,
    "rate limit": RateLimitException,
    "unauthorized": AuthenticationException,
    # Data processing
    "validation": ValidationException,
    "parse": ParseException,
    "transform": TransformationException,
    "format": FileFormatException,
    # Business logic
    "inventory": InsufficientInventoryException,
    "price": InvalidPriceException,
    "order": OrderProcessingException,
}


def map_exception_by_message(error_message: str) -> type:
    """
    Map generic exceptions to specific types based on error message content.

    Args:
        error_message: The error message to analyze

    Returns:
        Specific exception class or DomainException as fallback
    """
    error_lower = error_message.lower()

    for keyword, exception_class in COMMON_EXCEPTION_MAPPINGS.items():
        if keyword in error_lower:
            return exception_class

    return DomainException


def create_specific_exception(original_exception: Exception, context: str = "") -> DomainException:
    """
    Create a specific domain exception from a generic exception.

    Args:
        original_exception: The original exception
        context: Additional context about where the error occurred

    Returns:
        Domain-specific exception instance
    """
    error_message = str(original_exception)
    exception_class = map_exception_by_message(error_message)

    details = {
        "original_exception": type(original_exception).__name__,
        "original_message": error_message,
        "context": context,
    }

    return exception_class(
        message=f"{context}: {error_message}" if context else error_message, details=details
    )
