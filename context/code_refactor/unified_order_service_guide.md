# UnifiedOrderService - Quick Start Guide

**Status**: ✅ Ready to Use
**Created**: 2025-11-05
**Purpose**: Provide a single interface for order imports while we consolidate Sales & Orders domains

---

## Problem This Solves

Previously, developers had to decide between two services:
- `TransactionProcessor` (Sales domain) for CSV/Excel imports → Transaction table
- `OrderImportService` (Orders domain) for StockX API → Order table

This caused confusion, code duplication, and data fragmentation.

**Solution**: `UnifiedOrderService` provides a single interface that automatically routes to the correct service.

---

## Quick Start

### Basic Usage

```python
from domains.orders.services import UnifiedOrderService

async def import_my_orders(db_session, orders_data, platform):
    # Create service
    unified_service = UnifiedOrderService(db_session)

    # Import orders (automatically routes to correct service)
    result = await unified_service.import_orders(
        orders_data=orders_data,
        source=platform  # "stockx", "ebay", "csv", etc.
    )

    print(f"Created: {result['created']}, Updated: {result['updated']}")
```

### Even Simpler (Convenience Function)

```python
from domains.orders.services import import_orders

async def import_my_orders(db_session, orders_data):
    result = await import_orders(
        db_session,
        orders_data,
        source="stockx"
    )
```

---

## Supported Sources

### API-Based Sources (→ Order table)
- `"stockx"` - StockX orders
- `"ebay"` - eBay orders (planned)
- `"goat"` - GOAT orders (planned)
- `"alias"` - Alias orders (planned)

### File-Based Sources (→ Transaction table, legacy)
- `"csv"` - CSV imports
- `"excel"` - Excel imports
- `"notion"` - Notion exports

Use `OrderSource` constants for type safety:

```python
from domains.orders.services import OrderSource

await unified_service.import_orders(
    orders_data,
    source=OrderSource.STOCKX  # Type-safe!
)
```

---

## Migration Examples

### Before: Multiple Services

```python
# OLD CODE - Don't do this anymore!

from domains.sales.services.transaction_processor import TransactionProcessor
from domains.orders.services.order_import_service import OrderImportService

if source == "stockx":
    # Use OrderImportService
    order_service = OrderImportService(db_session)
    result = await order_service.import_stockx_orders(data)
elif source == "csv":
    # Use TransactionProcessor
    transaction_service = TransactionProcessor(db_session)
    result = await transaction_service.create_transactions_from_batch(batch_id)
```

### After: Single Service

```python
# NEW CODE - Do this instead!

from domains.orders.services import UnifiedOrderService

# Works for all sources
unified_service = UnifiedOrderService(db_session)
result = await unified_service.import_orders(data, source=source)
```

---

## Real-World Examples

### Example 1: Upload Router (StockX Orders)

**Before**:
```python
# domains/integration/api/upload_router.py

from domains.orders.services.order_import_service import OrderImportService

@router.post("/import/stockx-orders")
async def import_stockx_orders(db: AsyncSession = Depends(get_db_session)):
    order_import_service = OrderImportService(db)
    result = await order_import_service.import_stockx_orders(orders_data)
    return result
```

**After**:
```python
# domains/integration/api/upload_router.py

from domains.orders.services import UnifiedOrderService

@router.post("/import/stockx-orders")
async def import_stockx_orders(db: AsyncSession = Depends(get_db_session)):
    unified_service = UnifiedOrderService(db)
    result = await unified_service.import_orders(orders_data, source="stockx")
    return result
```

### Example 2: Import Processor (CSV Imports)

**Before**:
```python
# domains/integration/services/import_processor.py

from domains.sales.services.transaction_processor import TransactionProcessor

class ImportProcessor:
    def __init__(self, db_session):
        self.transaction_processor = TransactionProcessor(db_session)

    async def finalize_batch(self, batch_id):
        result = await self.transaction_processor.create_transactions_from_batch(batch_id)
        return result
```

**After**:
```python
# domains/integration/services/import_processor.py

from domains.orders.services import UnifiedOrderService

class ImportProcessor:
    def __init__(self, db_session):
        self.unified_order_service = UnifiedOrderService(db_session)

    async def finalize_batch(self, batch_id):
        result = await self.unified_order_service.import_orders(
            orders_data=[],  # Data comes from batch
            source="csv",
            batch_id=batch_id
        )
        return result
```

### Example 3: Webhook Handler

**Before**:
```python
# domains/integration/api/webhooks.py

from domains.orders.services.order_import_service import OrderImportService

@router.post("/webhooks/stockx/order-status")
async def handle_order_status(
    webhook_data: dict,
    db: AsyncSession = Depends(get_db_session)
):
    order_service = OrderImportService(db)
    # Process webhook...
    result = await order_service.import_stockx_orders([webhook_data["order"]])
    return {"status": "processed"}
```

**After**:
```python
# domains/integration/api/webhooks.py

from domains.orders.services import UnifiedOrderService

@router.post("/webhooks/stockx/order-status")
async def handle_order_status(
    webhook_data: dict,
    db: AsyncSession = Depends(get_db_session)
):
    unified_service = UnifiedOrderService(db)
    # Process webhook...
    result = await unified_service.import_orders(
        [webhook_data["order"]],
        source="stockx"
    )
    return {"status": "processed"}
```

---

## Advanced Usage

### Check Source Type

```python
unified_service = UnifiedOrderService(db_session)

if unified_service.is_api_source("stockx"):
    print("This will create Order records")

if unified_service.is_file_source("csv"):
    print("This will create Transaction records (legacy)")
```

### Standardize Platform Names

```python
# Handles various platform name formats
source = unified_service.get_recommended_source("StockX")  # → "stockx"
source = unified_service.get_recommended_source("Stock-X")  # → "stockx"
source = unified_service.get_recommended_source("CSV Import")  # → "csv"
source = unified_service.get_recommended_source("file.xlsx")  # → "excel"
```

### Get Order by External ID

```python
# Searches in the correct table based on source
order = await unified_service.get_order_by_external_id(
    external_id="STX-123456",
    source="stockx"
)

if order:
    print(f"Found order: {order.id}")
```

---

## How It Works (Under the Hood)

The `UnifiedOrderService` is a **Facade Pattern** that:

1. **Accepts** order data + source
2. **Determines** which service to use based on source:
   - API sources (stockx, ebay, etc.) → `OrderImportService` → `Order` table
   - File sources (csv, excel) → `TransactionProcessor` → `Transaction` table
3. **Routes** the request to the appropriate service
4. **Returns** standardized result

```
┌─────────────────────────────────────┐
│   UnifiedOrderService (Facade)     │
│                                     │
│  import_orders(data, source)       │
└──────────────┬──────────────────────┘
               │
               ├─ is API source?
               │  ↓ Yes
               │  ┌──────────────────────────┐
               │  │  OrderImportService      │
               │  │  (Creates Order records) │
               │  └──────────────────────────┘
               │
               └─ is file source?
                  ↓ Yes
                  ┌──────────────────────────────┐
                  │  TransactionProcessor        │
                  │  (Creates Transaction records)│
                  └──────────────────────────────┘
```

---

## Return Format

All methods return a standardized statistics dictionary:

```python
{
    "total_orders": 100,      # Total orders processed
    "created": 95,            # Successfully created
    "updated": 3,             # Updated existing orders
    "skipped": 2,             # Skipped (duplicates, invalid data)
    "errors": []              # List of error messages
}
```

---

## Error Handling

```python
from domains.orders.services import UnifiedOrderService

try:
    result = await unified_service.import_orders(orders_data, source="unknown")
except ValueError as e:
    # Raised if source is not recognized
    print(f"Invalid source: {e}")

# Check for import errors
if result["errors"]:
    for error in result["errors"]:
        logger.error(f"Import error: {error}")
```

---

## Testing

### Unit Test Example

```python
import pytest
from domains.orders.services import UnifiedOrderService, OrderSource

@pytest.mark.asyncio
async def test_import_stockx_orders(db_session):
    service = UnifiedOrderService(db_session)

    orders_data = [
        {
            "orderNumber": "STX-123",
            "status": "completed",
            "amount": 150.00,
        }
    ]

    result = await service.import_orders(orders_data, source=OrderSource.STOCKX)

    assert result["created"] == 1
    assert result["errors"] == []
```

### Integration Test Example

```python
from fastapi.testclient import TestClient

def test_import_orders_endpoint(client: TestClient):
    response = client.post(
        "/import/orders",
        json={
            "orders": [...],
            "source": "stockx"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["created"] > 0
```

---

## Important Notes

### This is a Transitional Solution

`UnifiedOrderService` is a **temporary** facade to provide immediate value while we work on full consolidation.

**Long-term plan** (see `sales_vs_orders_analysis.md`):
- Migrate all Transaction data to Order table
- Deprecate TransactionProcessor
- All sources use OrderImportService directly
- UnifiedOrderService becomes unnecessary (or a thin wrapper)

### Which Table is Used?

- **API sources** (stockx, ebay, goat, alias) → `sales.order` table
- **File sources** (csv, excel, notion) → `financial.transaction` table *(legacy)*

You can check programmatically:

```python
if service.is_api_source(source):
    print("Uses Order table")
elif service.is_file_source(source):
    print("Uses Transaction table (legacy)")
```

### Backward Compatibility

Existing code using `OrderImportService` or `TransactionProcessor` directly will continue to work. This service is **additive**, not breaking.

---

## When to Use What

| Scenario | Recommendation |
|----------|---------------|
| **New code** | Use `UnifiedOrderService` |
| **API integrations** | Use `UnifiedOrderService` with API source |
| **CSV/Excel imports** | Use `UnifiedOrderService` with file source |
| **Existing code** | Gradually migrate to `UnifiedOrderService` |
| **Platform-specific logic** | Can still use `OrderImportService` directly |
| **Legacy scripts** | Continue using existing services (for now) |

---

## FAQ

### Q: Should I use this for all new code?
**A**: Yes! Use `UnifiedOrderService` for all new order import code.

### Q: Do I need to update existing code immediately?
**A**: No, but it's recommended to migrate gradually during maintenance.

### Q: What happens to TransactionProcessor?
**A**: It remains for backward compatibility but will be deprecated in the future.

### Q: Can I add new platforms?
**A**: Yes! Add to `OrderSource` constants and the service will handle routing.

### Q: What about eBay/GOAT support?
**A**: The service is ready for these platforms. Implement platform-specific logic in `OrderImportService` or use the generic import.

### Q: How do I report issues?
**A**: Create a GitHub issue with "UnifiedOrderService" in the title.

---

## Next Steps

1. **Try it out** in a new feature or endpoint
2. **Migrate existing code** gradually (low-priority maintenance task)
3. **Provide feedback** on the interface and routing logic
4. **Help plan** the full consolidation (see `sales_vs_orders_analysis.md`)

---

## Related Documentation

- **Full Analysis**: `context/code_refactor/sales_vs_orders_analysis.md`
- **Refactoring Roadmap**: `REFACTORING_ROADMAP.md`
- **API Documentation**: http://localhost:8000/docs (when running)

---

**Questions?** Review `sales_vs_orders_analysis.md` or create a GitHub issue.

**Status**: ✅ Production Ready | 🚀 Ready to Deploy
