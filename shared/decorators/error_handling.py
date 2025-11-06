"""
Enhanced error handling decorators with domain-specific exception mapping.
Replaces generic exception handling with meaningful, specific errors.
"""

import asyncio
import functools
from typing import Any, Callable, Dict, Optional, Type

import structlog
from sqlalchemy.exc import SQLAlchemyError

from shared.exceptions.domain_exceptions import (
    AuthenticationException,
    BatchProcessingException,
    DatabaseConnectionException,
    DatabaseOperationException,
    DomainException,
    ExternalApiException,
    ImportException,
    ParseException,
    ServiceIntegrationException,
    StockXApiException,
    ValidationException,
    create_specific_exception,
)

logger = structlog.get_logger(__name__)


def handle_domain_errors(
    context: str = "",
    reraise: bool = True,
    fallback_return: Any = None,
    specific_mappings: Optional[Dict[str, Type[DomainException]]] = None,
):
    """
    Enhanced decorator that maps generic exceptions to domain-specific ones.

    Args:
        context: Context description for error logging
        reraise: Whether to reraise the exception (True) or return fallback_return (False)
        fallback_return: Value to return if reraise=False
        specific_mappings: Custom exception mappings for this decorator instance
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except DomainException:
                # Already a domain exception, just re-raise
                raise
            except SQLAlchemyError as e:
                # Database specific errors
                error_msg = str(e)
                if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    domain_error = DatabaseConnectionException(
                        f"Database connection failed: {error_msg}",
                        details={"original_error": type(e).__name__, "context": context},
                    )
                else:
                    domain_error = DatabaseOperationException(
                        f"Database operation failed: {error_msg}",
                        details={"original_error": type(e).__name__, "context": context},
                    )

                logger.error(
                    f"Database error in {context or func.__name__}",
                    error=str(e),
                    error_type=type(e).__name__,
                    mapped_to=type(domain_error).__name__,
                )

                if reraise:
                    raise domain_error from e
                return fallback_return

            except Exception as e:
                # Generic exception mapping
                error_message = str(e).lower()

                # Check specific mappings first
                domain_error = None
                if specific_mappings:
                    for keyword, exception_class in specific_mappings.items():
                        if keyword.lower() in error_message:
                            domain_error = exception_class(
                                str(e),
                                details={"original_error": type(e).__name__, "context": context},
                            )
                            break

                # Fallback to automatic mapping
                if not domain_error:
                    domain_error = create_specific_exception(e, context or func.__name__)

                logger.error(
                    f"Error in {context or func.__name__}",
                    error=str(e),
                    error_type=type(e).__name__,
                    mapped_to=type(domain_error).__name__,
                    context=context,
                )

                if reraise:
                    raise domain_error from e
                return fallback_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DomainException:
                # Already a domain exception, just re-raise
                raise
            except SQLAlchemyError as e:
                # Database specific errors
                error_msg = str(e)
                if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    domain_error = DatabaseConnectionException(
                        f"Database connection failed: {error_msg}",
                        details={"original_error": type(e).__name__, "context": context},
                    )
                else:
                    domain_error = DatabaseOperationException(
                        f"Database operation failed: {error_msg}",
                        details={"original_error": type(e).__name__, "context": context},
                    )

                logger.error(
                    f"Database error in {context or func.__name__}",
                    error=str(e),
                    error_type=type(e).__name__,
                    mapped_to=type(domain_error).__name__,
                )

                if reraise:
                    raise domain_error from e
                return fallback_return

            except Exception as e:
                # Generic exception mapping
                domain_error = create_specific_exception(e, context or func.__name__)

                logger.error(
                    f"Error in {context or func.__name__}",
                    error=str(e),
                    error_type=type(e).__name__,
                    mapped_to=type(domain_error).__name__,
                    context=context,
                )

                if reraise:
                    raise domain_error from e
                return fallback_return

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def handle_api_errors(service_name: str = "external_api"):
    """
    Specialized decorator for external API operations.
    """
    specific_mappings = {
        "401": AuthenticationException,
        "403": AuthenticationException,
        "unauthorized": AuthenticationException,
        "forbidden": AuthenticationException,
        "429": ExternalApiException,  # Rate limiting
        "rate limit": ExternalApiException,
        "stockx": StockXApiException,
    }

    return handle_domain_errors(
        context=f"{service_name}_api_call", specific_mappings=specific_mappings
    )


def handle_import_errors(import_source: str = ""):
    """
    Specialized decorator for import operations.
    """
    specific_mappings = {
        "parse": ParseException,
        "format": ParseException,
        "validation": ValidationException,
        "batch": BatchProcessingException,
        "transform": ImportException,
    }

    return handle_domain_errors(
        context=f"import_{import_source}", specific_mappings=specific_mappings
    )


def handle_service_errors(service_name: str):
    """
    Specialized decorator for service layer operations.
    """
    specific_mappings = {
        "configuration": ServiceIntegrationException,
        "unavailable": ServiceIntegrationException,
        "integration": ServiceIntegrationException,
    }

    return handle_domain_errors(
        context=f"{service_name}_service", specific_mappings=specific_mappings
    )


# Convenience decorators for common use cases
stockx_api_errors = handle_api_errors("stockx")
database_errors = handle_domain_errors("database_operation")
validation_errors = handle_domain_errors("validation")
import_errors = handle_import_errors()


# Legacy compatibility - gradually replace these
def handle_database_errors(func):
    """Legacy compatibility decorator"""
    return handle_domain_errors("database_operation")(func)


def handle_validation_errors(func):
    """Legacy compatibility decorator"""
    return handle_domain_errors("validation")(func)
