# Exception Handling Consolidation Plan
**Date:** 2025-11-05
**Priority:** 🟠 HIGH
**Estimated Effort:** 3-5 days

## Problem Statement

Two separate exception handling modules exist with overlapping functionality:

1. **`shared/error_handling/exceptions.py`** (380 lines) - Primary, used by main.py
2. **`shared/exceptions/domain_exceptions.py`** (206 lines) - Minimal usage (1 file)

This creates confusion about which exceptions to use and leads to inconsistent error handling.

---

## Current State Analysis

### Module 1: `shared/error_handling/exceptions.py`

**Size:** 380 lines
**Usage:** `main.py` (exception handlers)

**Structure:**
```python
# Error codes enum
class ErrorCode(Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    # ... 15+ error codes

# Base exception
class SoleFlipException(Exception):
    def __init__(self, message, error_code, status_code, details):
        # Structured exception with HTTP status codes

# Specific exceptions
class ValidationException(SoleFlipException)
class ResourceNotFoundException(SoleFlipException)
class DuplicateResourceException(SoleFlipException)
class ImportProcessingException(SoleFlipException)
class BusinessRuleException(SoleFlipException)
class DatabaseException(SoleFlipException)
class ExternalServiceException(SoleFlipException)

# Exception handlers for FastAPI
async def soleflip_exception_handler(request, exc)
async def http_exception_handler(request, exc)
async def generic_exception_handler(request, exc)
```

**Features:**
- ✅ HTTP status code mapping
- ✅ Structured error responses
- ✅ ErrorCode enum for consistency
- ✅ FastAPI exception handlers
- ✅ Logging integration
- ✅ User-friendly error messages

### Module 2: `shared/exceptions/domain_exceptions.py`

**Size:** 206 lines
**Usage:** `domains/integration/services/stockx_service.py` (1 file only)

**Structure:**
```python
# Base exception
class DomainException(Exception):
    def __init__(self, message, details=None):
        # Simple exception with optional details dict

# Database exceptions
class DatabaseOperationException(DomainException)
class RecordNotFoundException(DatabaseOperationException)
class DuplicateRecordException(DatabaseOperationException)
class DatabaseConnectionException(DatabaseOperationException)

# API exceptions
class ExternalApiException(DomainException):
    # Adds status_code attribute
class StockXApiException(ExternalApiException)
class AuthenticationException(ExternalApiException)
class RateLimitException(ExternalApiException)

# Data processing exceptions
class DataProcessingException(DomainException)
class ValidationException(DataProcessingException)
class TransformationException(DataProcessingException)
class ParseException(DataProcessingException)

# Business logic exceptions
class BusinessLogicException(DomainException)
class InsufficientInventoryException(BusinessLogicException)
class InvalidPriceException(BusinessLogicException)
class OrderProcessingException(BusinessLogicException)

# Import exceptions
class ImportException(DomainException)
class FileFormatException(ImportException)
class BatchProcessingException(ImportException)

# Integration exceptions
class ServiceIntegrationException(DomainException)
class ServiceUnavailableException(ServiceIntegrationException)
class ConfigurationException(ServiceIntegrationException)
```

**Features:**
- ✅ Domain-specific exception hierarchy
- ✅ Detailed exception types
- ❌ No HTTP status code mapping
- ❌ No FastAPI handlers
- ❌ No ErrorCode enum
- ❌ No logging integration

---

## Exception Mapping

### Overlapping Exceptions

| error_handling | domain_exceptions | Functionality |
|----------------|-------------------|---------------|
| ValidationException | ValidationException | Input validation errors |
| ResourceNotFoundException | RecordNotFoundException | Missing database records |
| DuplicateResourceException | DuplicateRecordException | Duplicate key violations |
| DatabaseException | DatabaseOperationException | Database errors |
| ExternalServiceException | ExternalApiException | External API failures |
| ImportProcessingException | ImportException | Import/batch processing |

### Unique to domain_exceptions (Need Migration)

| Exception | Category | Migration Target |
|-----------|----------|------------------|
| StockXApiException | API | Add to error_handling as specific ExternalServiceException |
| AuthenticationException | API | Add to error_handling with 401 status code |
| RateLimitException | API | Add to error_handling with 429 status code |
| TransformationException | Data | Add to error_handling as ValidationException subtype |
| ParseException | Data | Add to error_handling as ValidationException subtype |
| InsufficientInventoryException | Business | Add to error_handling as BusinessRuleException subtype |
| InvalidPriceException | Business | Add to error_handling as BusinessRuleException subtype |
| OrderProcessingException | Business | Add to error_handling as BusinessRuleException subtype |
| FileFormatException | Import | Add to error_handling as ImportProcessingException subtype |
| BatchProcessingException | Import | Add to error_handling as ImportProcessingException subtype |
| ServiceUnavailableException | Integration | Add to error_handling as ExternalServiceException subtype |
| ConfigurationException | Config | Add to error_handling with 500 status code |
| DatabaseConnectionException | Database | Add to error_handling as DatabaseException subtype |

---

## Consolidation Strategy

### Phase 1: Extend error_handling Module (Day 1-2)

**Step 1.1: Add Missing ErrorCode Values**

```python
# shared/error_handling/exceptions.py

class ErrorCode(Enum):
    # ... existing codes ...

    # API-specific errors
    STOCKX_API_ERROR = "STOCKX_API_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"  # Already exists

    # Data processing errors
    TRANSFORMATION_ERROR = "TRANSFORMATION_ERROR"
    PARSE_ERROR = "PARSE_ERROR"

    # Business logic errors
    INSUFFICIENT_INVENTORY = "INSUFFICIENT_INVENTORY"
    INVALID_PRICE = "INVALID_PRICE"
    ORDER_PROCESSING_ERROR = "ORDER_PROCESSING_ERROR"

    # Import errors
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"  # Already exists
    BATCH_PROCESSING_ERROR = "BATCH_PROCESSING_ERROR"

    # Integration errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
```

**Step 1.2: Add Domain-Specific Exceptions**

```python
# shared/error_handling/exceptions.py

# ============================================================================
# API & Integration Exceptions
# ============================================================================

class StockXApiException(ExternalServiceException):
    """StockX API specific errors"""

    def __init__(
        self,
        message: str = "StockX API error occurred",
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.STOCKX_API_ERROR,
            status_code=502,  # Bad Gateway
            details=details or {}
        )
        if status_code:
            self.details["api_status_code"] = status_code


class AuthenticationException(ExternalServiceException):
    """Authentication/authorization failures"""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            status_code=401,
            details=details or {}
        )


class RateLimitException(ExternalServiceException):
    """Rate limit exceeded errors"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=details
        )


class ServiceUnavailableException(ExternalServiceException):
    """External service unavailable errors"""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["service_name"] = service_name

        super().__init__(
            message=message or f"Service {service_name} is unavailable",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details=details
        )


# ============================================================================
# Data Processing Exceptions
# ============================================================================

class TransformationException(ValidationException):
    """Data transformation errors"""

    def __init__(
        self,
        message: str = "Data transformation failed",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            field_errors=[],
            details=details
        )
        self.error_code = ErrorCode.TRANSFORMATION_ERROR


class ParseException(ValidationException):
    """Data parsing errors"""

    def __init__(
        self,
        message: str = "Failed to parse data",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            field_errors=[],
            details=details or {}
        )
        self.error_code = ErrorCode.PARSE_ERROR


# ============================================================================
# Business Logic Exceptions
# ============================================================================

class InsufficientInventoryException(BusinessRuleException):
    """Not enough inventory available"""

    def __init__(
        self,
        product_id: Optional[UUID] = None,
        requested: Optional[int] = None,
        available: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if product_id:
            details["product_id"] = str(product_id)
        if requested is not None:
            details["requested_quantity"] = requested
        if available is not None:
            details["available_quantity"] = available

        super().__init__(
            message="Insufficient inventory available",
            rule="inventory_check",
            details=details
        )
        self.error_code = ErrorCode.INSUFFICIENT_INVENTORY


class InvalidPriceException(BusinessRuleException):
    """Invalid price value"""

    def __init__(
        self,
        price: Optional[Decimal] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if price is not None:
            details["price"] = str(price)
        if reason:
            details["reason"] = reason

        super().__init__(
            message=f"Invalid price: {reason}" if reason else "Invalid price",
            rule="price_validation",
            details=details
        )
        self.error_code = ErrorCode.INVALID_PRICE


class OrderProcessingException(BusinessRuleException):
    """Order processing errors"""

    def __init__(
        self,
        order_id: Optional[UUID] = None,
        message: str = "Order processing failed",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if order_id:
            details["order_id"] = str(order_id)

        super().__init__(
            message=message,
            rule="order_processing",
            details=details
        )
        self.error_code = ErrorCode.ORDER_PROCESSING_ERROR


# ============================================================================
# Import Exceptions
# ============================================================================

class FileFormatException(ImportProcessingException):
    """File format errors"""

    def __init__(
        self,
        filename: Optional[str] = None,
        expected_format: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if filename:
            details["filename"] = filename
        if expected_format:
            details["expected_format"] = expected_format

        super().__init__(
            message=f"Invalid file format: {filename}" if filename else "Invalid file format",
            batch_id=None,
            details=details
        )
        self.error_code = ErrorCode.FILE_FORMAT_ERROR


class BatchProcessingException(ImportProcessingException):
    """Batch processing errors"""

    def __init__(
        self,
        batch_id: Optional[str] = None,
        records_processed: Optional[int] = None,
        records_failed: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if records_processed is not None:
            details["records_processed"] = records_processed
        if records_failed is not None:
            details["records_failed"] = records_failed

        super().__init__(
            message="Batch processing failed",
            batch_id=batch_id,
            details=details
        )
        self.error_code = ErrorCode.BATCH_PROCESSING_ERROR


# ============================================================================
# Database Exceptions
# ============================================================================

class DatabaseConnectionException(DatabaseException):
    """Database connection errors"""

    def __init__(
        self,
        message: str = "Database connection failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            query=None,
            details=details or {}
        )
        self.error_code = ErrorCode.DATABASE_CONNECTION_ERROR


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationException(SoleFlipException):
    """Configuration errors"""

    def __init__(
        self,
        config_key: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if config_key:
            details["config_key"] = config_key

        super().__init__(
            message=message or f"Configuration error: {config_key}",
            error_code=ErrorCode.CONFIGURATION_ERROR,
            status_code=500,
            details=details
        )
```

### Phase 2: Update StockX Service (Day 2)

**Step 2.1: Update Import Statement**

```python
# domains/integration/services/stockx_service.py

# OLD:
from shared.exceptions.domain_exceptions import (
    StockXApiException,
    AuthenticationException,
    RateLimitException,
)

# NEW:
from shared.error_handling.exceptions import (
    StockXApiException,
    AuthenticationException,
    RateLimitException,
)
```

**Step 2.2: Verify StockX Service Still Works**

```bash
pytest tests/integration/test_stockx_service.py -v
```

### Phase 3: Add Deprecation Warnings (Day 3)

**Step 3.1: Mark domain_exceptions as Deprecated**

```python
# shared/exceptions/domain_exceptions.py

"""
DEPRECATED: This module has been consolidated into shared.error_handling.exceptions

All exceptions have been migrated to the primary error handling module with:
- HTTP status code mapping
- ErrorCode enum integration
- FastAPI exception handler support
- Structured logging

Migration completed: 2025-11-05
Scheduled for removal: 2025-12-01

Please update imports:
  OLD: from shared.exceptions.domain_exceptions import StockXApiException
  NEW: from shared.error_handling.exceptions import StockXApiException
"""

import warnings
from shared.error_handling.exceptions import *  # noqa: F401, F403

warnings.warn(
    "shared.exceptions.domain_exceptions is deprecated. "
    "Use shared.error_handling.exceptions instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### Phase 4: Testing & Validation (Day 3-4)

**Step 4.1: Update Tests**

```bash
# Find all test files importing domain_exceptions
grep -r "from shared.exceptions.domain_exceptions import" tests/

# Update imports to use error_handling instead
# (Should be minimal since only 1 production file uses it)
```

**Step 4.2: Run Full Test Suite**

```bash
make test
```

**Step 4.3: Check for Deprecation Warnings**

```bash
pytest -W error::DeprecationWarning
```

### Phase 5: Documentation Update (Day 4)

**Step 5.1: Update CLAUDE.md**

```markdown
## Error Handling

### Exception Classes

All custom exceptions are defined in `shared/error_handling/exceptions.py`:

- **SoleFlipException**: Base exception with HTTP status codes and error codes
- **ValidationException**: Input validation errors (400)
- **ResourceNotFoundException**: Missing resources (404)
- **BusinessRuleException**: Business logic violations (409)
- **DatabaseException**: Database operation errors (500)
- **ExternalServiceException**: External API failures (502/503)
- **ImportProcessingException**: Import/batch processing errors (422)

Domain-specific exceptions extend these base classes:
- StockXApiException, AuthenticationException, RateLimitException
- InsufficientInventoryException, InvalidPriceException
- FileFormatException, BatchProcessingException

### Usage Example

```python
from shared.error_handling.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    ErrorCode
)

# Raise with structured error info
raise ResourceNotFoundException(
    resource_type="Product",
    resource_id=product_id,
    details={"sku": sku}
)

# Exception handlers automatically convert to JSON response:
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Product not found",
    "details": {
      "resource_type": "Product",
      "resource_id": "123e4567-e89b-12d3-a456-426614174000",
      "sku": "ABC123"
    }
  }
}
```

### Deprecated Modules

❌ **`shared/exceptions/domain_exceptions.py`** - Deprecated as of 2025-11-05
   - Use `shared/error_handling/exceptions.py` instead
   - All exceptions migrated with enhanced features
```

### Phase 6: Cleanup (Day 5 + 4 weeks grace period)

**Step 6.1: Monitor for Usage**

```bash
# After 4 weeks, verify no imports remain
grep -r "shared.exceptions.domain_exceptions" . --include="*.py"
```

**Step 6.2: Final Removal**

```bash
# Remove deprecated module
rm -rf shared/exceptions/

# Update imports if any stragglers found
# (Should be caught by deprecation warnings)
```

---

## Benefits

### Before Consolidation
- ❌ Two separate exception modules
- ❌ Confusion about which to use
- ❌ Inconsistent error responses
- ❌ No HTTP status code mapping in domain_exceptions
- ❌ No FastAPI integration in domain_exceptions

### After Consolidation
- ✅ Single source of truth for exceptions
- ✅ Consistent error handling across all domains
- ✅ HTTP status codes for all exceptions
- ✅ FastAPI exception handlers integrated
- ✅ Structured error responses
- ✅ ErrorCode enum for consistency
- ✅ Better logging and monitoring

---

## Testing Checklist

- [ ] All existing tests pass
- [ ] StockX service tests pass with new imports
- [ ] Exception handlers return correct HTTP status codes
- [ ] Error responses include ErrorCode values
- [ ] Deprecation warnings appear when using old module
- [ ] No new exceptions raised during import
- [ ] API returns structured error responses
- [ ] Logging includes exception details

---

## Rollback Plan

If issues arise:

### Immediate Rollback (Before removal)
```bash
# Revert import changes in stockx_service.py
git checkout HEAD~1 -- domains/integration/services/stockx_service.py
```

### Full Rollback
```bash
# Restore domain_exceptions module
git revert <consolidation-commit>
```

---

## Timeline

| Day | Phase | Deliverables |
|-----|-------|--------------|
| 1-2 | Extend Module | All domain exceptions added to error_handling |
| 2 | Update StockX | StockX service using new imports, tests passing |
| 3 | Deprecation | domain_exceptions marked deprecated with warnings |
| 3-4 | Testing | Full test suite passing, no regressions |
| 4 | Documentation | CLAUDE.md updated, migration guide written |
| 35+ | Cleanup | domain_exceptions removed (after grace period) |

---

## Next Steps

1. ✅ Review this plan with team
2. 🔲 Get approval to proceed
3. 🔲 Create feature branch: `feat/consolidate-exception-handling`
4. 🔲 Execute Phase 1 (Extend error_handling)
5. 🔲 Execute Phase 2 (Update StockX service)
6. 🔲 Execute Phase 3 (Add deprecation)
7. 🔲 Execute Phase 4 (Testing)
8. 🔲 Execute Phase 5 (Documentation)
9. 🔲 Wait 4 weeks (monitor for stragglers)
10. 🔲 Execute Phase 6 (Final removal)
