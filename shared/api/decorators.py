"""
API Route Decorators
Reusable decorators to reduce boilerplate code in API routes
"""

import functools
import time
from typing import Any, Callable, Optional
from uuid import UUID

import structlog
from fastapi import HTTPException

from shared.api.dependencies import ErrorContext

logger = structlog.get_logger(__name__)


def with_error_handling(
    operation: str,
    resource: str,
    include_not_found: bool = False
):
    """
    Decorator that adds standardized error handling to route handlers

    Args:
        operation: The operation being performed (e.g., "fetch", "create", "update")
        resource: The resource being operated on (e.g., "inventory item", "product")
        include_not_found: Whether to handle HTTPException(404) specially

    Example:
        @router.get("/items/{item_id}")
        @with_error_handling("fetch", "inventory item", include_not_found=True)
        async def get_item(item_id: UUID, service: Service = Depends()):
            return await service.get_item(item_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions as-is (validation errors, 404s, etc.)
                if include_not_found:
                    raise
                raise
            except Exception as e:
                error_context = ErrorContext(operation, resource)
                raise error_context.create_error_response(e)
        return wrapper
    return decorator


def with_logging(
    message: str,
    include_params: bool = True,
    log_level: str = "info"
):
    """
    Decorator that adds automatic logging to route handlers

    Args:
        message: The log message to emit
        include_params: Whether to include function parameters in log
        log_level: Log level to use ("info", "debug", "warning")

    Example:
        @router.get("/items")
        @with_logging("Fetching inventory items")
        async def get_items(skip: int = 0, limit: int = 50):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            log_fn = getattr(logger, log_level, logger.info)

            if include_params:
                # Filter out dependency-injected services from logging
                params_to_log = {
                    k: str(v) if isinstance(v, UUID) else v
                    for k, v in kwargs.items()
                    if not k.endswith('_service') and not k.endswith('_session')
                }
                log_fn(message, **params_to_log)
            else:
                log_fn(message)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def with_timing(metric_name: Optional[str] = None):
    """
    Decorator that logs execution time of route handlers

    Args:
        metric_name: Optional custom metric name (defaults to function name)

    Example:
        @router.post("/import")
        @with_timing("csv_import_duration")
        async def import_csv(file: UploadFile):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            name = metric_name or func.__name__
            logger.info(
                f"Route execution completed",
                route=name,
                duration_seconds=round(duration, 3),
                duration_ms=round(duration * 1000, 1)
            )

            return result
        return wrapper
    return decorator


def validate_uuid(param_name: str = "id"):
    """
    Decorator that validates UUID parameters

    Args:
        param_name: Name of the UUID parameter to validate

    Example:
        @router.get("/items/{item_id}")
        @validate_uuid("item_id")
        async def get_item(item_id: str):
            # item_id is guaranteed to be a valid UUID string
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if param_name in kwargs:
                value = kwargs[param_name]
                if isinstance(value, str):
                    try:
                        # Validate it's a proper UUID
                        UUID(value)
                    except (ValueError, AttributeError):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid UUID format for parameter '{param_name}': {value}"
                        )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_resource_exists(
    service_param: str,
    resource_id_param: str,
    getter_method: str = "get_by_id",
    resource_name: str = "resource"
):
    """
    Decorator that ensures a resource exists before executing route handler

    Args:
        service_param: Name of the service dependency parameter
        resource_id_param: Name of the resource ID parameter
        getter_method: Method name to call on service to fetch resource
        resource_name: Human-readable resource name for error messages

    Example:
        @router.put("/items/{item_id}")
        @require_resource_exists("inventory_service", "item_id", "get_item_detailed", "inventory item")
        async def update_item(item_id: UUID, data: dict, inventory_service: Service = Depends()):
            # item is guaranteed to exist at this point
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            service = kwargs.get(service_param)
            resource_id = kwargs.get(resource_id_param)

            if service and resource_id:
                getter = getattr(service, getter_method, None)
                if getter:
                    resource = await getter(resource_id)
                    if not resource:
                        raise HTTPException(
                            status_code=404,
                            detail=f"{resource_name.title()} with ID {resource_id} not found"
                        )
                    # Store the fetched resource in kwargs for use in handler
                    kwargs[f"_fetched_{resource_name.replace(' ', '_')}"] = resource

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience decorator combos for common patterns

def standard_get_route(resource: str):
    """
    Standard decorator stack for GET routes that fetch a single resource

    Example:
        @router.get("/items/{item_id}")
        @standard_get_route("inventory item")
        async def get_item(item_id: UUID, service: Service = Depends()):
            return await service.get_item(item_id)
    """
    def decorator(func: Callable) -> Callable:
        @with_error_handling("fetch", resource, include_not_found=True)
        @with_logging(f"Fetching {resource}")
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def standard_list_route(resource: str):
    """
    Standard decorator stack for GET routes that list resources

    Example:
        @router.get("/items")
        @standard_list_route("inventory items")
        async def list_items(skip: int = 0, limit: int = 50, service: Service = Depends()):
            return await service.list_items(skip, limit)
    """
    def decorator(func: Callable) -> Callable:
        @with_error_handling("list", resource)
        @with_logging(f"Listing {resource}")
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def standard_create_route(resource: str):
    """
    Standard decorator stack for POST routes that create resources

    Example:
        @router.post("/items")
        @standard_create_route("inventory item")
        async def create_item(data: CreateRequest, service: Service = Depends()):
            return await service.create_item(data)
    """
    def decorator(func: Callable) -> Callable:
        @with_error_handling("create", resource)
        @with_logging(f"Creating {resource}")
        @with_timing()
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def standard_update_route(resource: str):
    """
    Standard decorator stack for PUT/PATCH routes that update resources

    Example:
        @router.put("/items/{item_id}")
        @standard_update_route("inventory item")
        async def update_item(item_id: UUID, data: UpdateRequest, service: Service = Depends()):
            return await service.update_item(item_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @with_error_handling("update", resource, include_not_found=True)
        @with_logging(f"Updating {resource}")
        @with_timing()
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def standard_delete_route(resource: str):
    """
    Standard decorator stack for DELETE routes

    Example:
        @router.delete("/items/{item_id}")
        @standard_delete_route("inventory item")
        async def delete_item(item_id: UUID, service: Service = Depends()):
            return await service.delete_item(item_id)
    """
    def decorator(func: Callable) -> Callable:
        @with_error_handling("delete", resource, include_not_found=True)
        @with_logging(f"Deleting {resource}")
        @with_timing()
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
