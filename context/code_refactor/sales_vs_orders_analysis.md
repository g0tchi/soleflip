# Sales vs Orders Domain Overlap - Analysis & Resolution

**Date**: 2025-11-05
**Priority**: 🔴 CRITICAL
**Status**: Analysis Complete → Implementation Ready

---

## Problem Statement

Two domains handle transaction/order logic with different database models, creating:
- **Code duplication** in import logic
- **Confusion** about which service to use
- **Data fragmentation** across two tables
- **Maintenance burden** with duplicate business logic

---

## Current State Analysis

### Domain 1: Sales Domain

**File**: `domains/sales/services/transaction_processor.py` (498 lines)

**Database Model**: `Transaction` (financial.transaction schema)
```python
class Transaction(Base, TimestampMixin):
    id = Column(UUID)
    inventory_id = Column(UUID, ForeignKey("inventory.stock.id"))
    platform_id = Column(UUID, ForeignKey("platform.marketplace.id"))
    transaction_date = Column(DateTime)
    sale_price = Column(Numeric(10, 2))
    platform_fee = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))
    net_profit = Column(Numeric(10, 2))
    status = Column(String(50))
    external_id = Column(String(100))
    buyer_destination_country = Column(String(100))
    buyer_destination_city = Column(String(100))
    notes = Column(Text)
```

**Purpose**:
- Generic financial transaction tracking
- Used for CSV/Excel/JSON imports
- Platform-agnostic design

**Used By**:
- `domains/integration/services/import_processor.py`
- `scripts/transactions/create_alias_transactions.py`
- Legacy import flows

---

### Domain 2: Orders Domain

**File**: `domains/orders/services/order_import_service.py` (400 lines)

**Database Model**: `Order` (sales.order schema)
```python
class Order(Base, TimestampMixin):
    id = Column(UUID)
    inventory_item_id = Column(UUID, ForeignKey("inventory.stock.id"))
    listing_id = Column(UUID, ForeignKey("sales.listing.id"))

    # StockX-specific (but platform-agnostic design)
    stockx_order_number = Column(String(100), unique=True, index=True)
    status = Column(String(50), index=True)
    amount = Column(Numeric(10, 2))
    currency_code = Column(String(10))
    inventory_type = Column(String(50))

    # Shipping
    shipping_label_url = Column(String(512))
    shipping_document_path = Column(String(512))

    # Timestamps
    stockx_created_at = Column(DateTime)
    last_stockx_updated_at = Column(DateTime)

    # Business Metrics (Notion Sync)
    sold_at = Column(DateTime, index=True)
    gross_sale = Column(Numeric(10, 2))
    net_proceeds = Column(Numeric(10, 2))
    gross_profit = Column(Numeric(10, 2))
    net_profit = Column(Numeric(10, 2))
    roi = Column(Numeric(5, 2))
    payout_received = Column(Boolean, index=True)
    payout_date = Column(DateTime)
    shelf_life_days = Column(Integer)

    # Multi-platform support (v2.3.3)
    platform_specific_data = Column(JSONB)  # For StockX, eBay, GOAT, Alias
    raw_data = Column(JSONB)
```

**Purpose**:
- Order lifecycle management
- Rich business metrics (ROI, profit, etc.)
- Multi-platform support (StockX, eBay, GOAT, Alias)
- Notion integration

**Used By**:
- `domains/integration/api/upload_router.py` (StockX order sync)
- `domains/integration/api/webhooks.py` (StockX webhooks)
- Modern API endpoints

---

## Key Differences

| Aspect | Transaction (Sales) | Order (Orders) |
|--------|---------------------|----------------|
| **Schema** | financial.transaction | sales.order |
| **Focus** | Generic financial tracking | Business operations & metrics |
| **Fields** | 11 core fields | 20+ fields including business metrics |
| **Platform Support** | Generic (via platform_id) | Explicit multi-platform (platform_specific_data) |
| **Business Metrics** | Basic (net_profit only) | Rich (ROI, gross/net profit, shelf life) |
| **Integrations** | CSV/Excel imports | StockX API, Webhooks, Notion |
| **Relationships** | InventoryItem, Platform | InventoryItem, Listing, Platform |
| **Usage** | Legacy imports | Modern API flows |

---

## Data Flow Analysis

### Transaction Creation Flow (Sales Domain)
```
CSV/Excel File
    ↓
ImportProcessor.process_batch()
    ↓
TransactionProcessor.create_transactions_from_batch()
    ↓
Creates Transaction in financial.transaction
```

### Order Creation Flow (Orders Domain)
```
StockX API / Webhook
    ↓
upload_router.import_stockx_orders() OR webhooks.handle_order_status()
    ↓
OrderImportService.import_stockx_orders()
    ↓
Creates Order in sales.order
```

---

## Problem Impact

### For Developers
- ❌ Confusion: Which service to use for new integrations?
- ❌ Duplication: Similar logic in both services
- ❌ Maintenance: Bug fixes must be applied twice
- ❌ Testing: Duplicate test coverage needed

### For Data Integrity
- ❌ Fragmentation: Sales data split across two tables
- ❌ Reporting: Complex queries joining both tables
- ❌ Analytics: Inconsistent metrics (some orders missing ROI, etc.)

### For Business Operations
- ❌ Incomplete view: Can't see all sales in one place
- ❌ Limited metrics: Transaction table lacks ROI, gross profit
- ❌ Platform limitations: Transaction model not designed for modern needs

---

## Solution Options

### ✅ Option 1: Consolidate to Orders Domain (RECOMMENDED)

**Strategy**: Make `Order` the single source of truth for all sales

**Implementation**:
1. **Migrate existing Transaction data** to Order table
2. **Deprecate TransactionProcessor** - redirect to OrderImportService
3. **Extend OrderImportService** for all platforms (CSV, Excel, eBay, GOAT, Alias)
4. **Update ImportProcessor** to use OrderImportService
5. **Keep Transaction table** for legacy/read-only (don't delete data)

**Pros**:
- ✅ Richer data model (ROI, gross/net profit, shelf life)
- ✅ Already multi-platform ready (platform_specific_data JSONB)
- ✅ Better aligned with business needs
- ✅ Modern architecture (v2.3.3 design)
- ✅ Easier to add new platforms

**Cons**:
- ⚠️ Migration required for existing Transaction data
- ⚠️ Schema change (financial → sales)
- ⚠️ Need to update all Transaction references

**Effort**: 5-6 days
**Risk**: Medium (requires careful migration)

---

### Option 2: Consolidate to Sales Domain

**Strategy**: Extend `Transaction` model, deprecate `Order`

**Implementation**:
1. Add all Order fields to Transaction model
2. Migrate Order data to Transaction
3. Update OrderImportService to use Transaction
4. Rename Transaction → Order (or keep both names)

**Pros**:
- ✅ Financial schema might be more appropriate
- ✅ Transaction is more generic term

**Cons**:
- ❌ Transaction model is simpler - needs major extension
- ❌ Losing v2.3.3 multi-platform design
- ❌ Name "Transaction" less clear than "Order"
- ❌ More work to extend Transaction model

**Effort**: 6-7 days
**Risk**: Medium-High

**Verdict**: ❌ Not recommended - Order model is more feature-complete

---

### Option 3: Keep Both, Add Clear Separation

**Strategy**: Document when to use each, add mapping layer

**Implementation**:
1. Document Transaction = legacy CSV imports
2. Document Order = modern API integrations
3. Add mapping service to sync data between tables
4. Update documentation

**Pros**:
- ✅ No migration needed
- ✅ Low risk
- ✅ Fast implementation

**Cons**:
- ❌ Doesn't solve the core problem
- ❌ Continues data fragmentation
- ❌ Still confusing for developers
- ❌ Ongoing maintenance burden

**Effort**: 1-2 days
**Risk**: Low

**Verdict**: ❌ Band-aid solution - doesn't address root cause

---

## Recommended Solution: Option 1

**Consolidate to Orders Domain with gradual migration**

---

## Implementation Plan

### Phase 1: Preparation (Day 1)
1. **Audit existing data**
   - Count records in Transaction table
   - Identify fields that don't map to Order
   - Check for data quality issues

2. **Create migration script**
   - Map Transaction fields → Order fields
   - Handle edge cases
   - Test on staging data

3. **Update Order model** (if needed)
   - Add any missing fields from Transaction
   - Ensure platform_specific_data can hold all platforms

### Phase 2: Service Consolidation (Days 2-3)

1. **Extend OrderImportService**
   ```python
   class OrderImportService:
       """Unified order import for all platforms"""

       async def import_stockx_orders(...) -> Dict[str, Any]:
           # Existing StockX logic

       async def import_ebay_orders(...) -> Dict[str, Any]:
           # New eBay logic

       async def import_goat_orders(...) -> Dict[str, Any]:
           # New GOAT logic

       async def import_generic_orders(
           self,
           orders_data: List[Dict],
           platform_name: str
       ) -> Dict[str, Any]:
           """Import orders from CSV/Excel/generic sources"""
           # Replaces TransactionProcessor logic
   ```

2. **Create adapter layer**
   ```python
   class TransactionToOrderAdapter:
       """Converts legacy Transaction logic to Order format"""

       def convert_transaction_data(
           self,
           transaction_data: Dict
       ) -> Dict:
           """Map transaction fields to order fields"""
           return {
               "inventory_item_id": transaction_data["inventory_id"],
               "amount": transaction_data["sale_price"],
               "sold_at": transaction_data["transaction_date"],
               "net_profit": transaction_data["net_profit"],
               "platform_specific_data": {
                   "platform_fee": transaction_data["platform_fee"],
                   "shipping_cost": transaction_data["shipping_cost"],
                   "external_id": transaction_data["external_id"],
                   "buyer_country": transaction_data.get("buyer_destination_country"),
                   "buyer_city": transaction_data.get("buyer_destination_city"),
               },
               "status": transaction_data["status"],
               # ...
           }
   ```

### Phase 3: Update ImportProcessor (Day 3-4)

```python
# Before:
from domains.sales.services.transaction_processor import TransactionProcessor

class ImportProcessor:
    def __init__(self, db_session):
        self.transaction_processor = TransactionProcessor(db_session)

    async def finalize_batch(self, batch_id):
        # Create transactions
        await self.transaction_processor.create_transactions_from_batch(batch_id)

# After:
from domains.orders.services.order_import_service import OrderImportService
from domains.orders.adapters.transaction_adapter import TransactionToOrderAdapter

class ImportProcessor:
    def __init__(self, db_session):
        self.order_import_service = OrderImportService(db_session)
        self.adapter = TransactionToOrderAdapter()

    async def finalize_batch(self, batch_id):
        # Convert batch data to order format
        orders_data = await self.adapter.convert_batch_to_orders(batch_id)
        # Create orders
        await self.order_import_service.import_generic_orders(
            orders_data,
            platform_name="csv_import"  # or detect from batch
        )
```

### Phase 4: Data Migration (Day 4-5)

```python
# Migration script: scripts/migrations/migrate_transactions_to_orders.py

async def migrate_transactions_to_orders():
    """
    Migrate existing Transaction records to Order table
    """
    async with db_manager.get_session() as session:
        # Get all transactions
        transactions = await session.execute(
            select(Transaction).where(Transaction.migrated_to_order.is_(False))
        )

        adapter = TransactionToOrderAdapter()

        for transaction in transactions.scalars():
            try:
                # Convert to order format
                order_data = adapter.convert_transaction_to_order(transaction)

                # Create order
                order = Order(**order_data)
                session.add(order)

                # Mark transaction as migrated (add this field)
                transaction.migrated_to_order = True
                transaction.migrated_order_id = order.id

            except Exception as e:
                logger.error(
                    "Failed to migrate transaction",
                    transaction_id=transaction.id,
                    error=str(e)
                )

        await session.commit()
```

### Phase 5: Deprecation & Cleanup (Day 5-6)

1. **Mark TransactionProcessor as deprecated**
   ```python
   import warnings

   class TransactionProcessor:
       """
       DEPRECATED: Use OrderImportService instead

       This service is maintained for backward compatibility only.
       All new code should use domains.orders.services.OrderImportService
       """

       def __init__(self, db_session):
           warnings.warn(
               "TransactionProcessor is deprecated. Use OrderImportService.",
               DeprecationWarning,
               stacklevel=2
           )
           # Keep implementation for legacy support
   ```

2. **Update documentation**
   - Add deprecation notice to CLAUDE.md
   - Update API documentation
   - Create migration guide

3. **Update tests**
   - Keep Transaction tests for backward compatibility
   - Add Order tests for new functionality
   - Add migration tests

---

## Migration Safety Measures

### Data Validation
```python
async def validate_migration():
    """Ensure data integrity after migration"""
    async with db_manager.get_session() as session:
        # Count records
        transaction_count = await session.scalar(select(func.count(Transaction.id)))
        order_count = await session.scalar(
            select(func.count(Order.id)).where(
                Order.platform_specific_data.contains({"migrated_from": "transaction"})
            )
        )

        # Verify totals match
        assert transaction_count == order_count, "Record count mismatch!"

        # Sample validation
        transactions = await session.execute(
            select(Transaction).limit(100)
        )

        for transaction in transactions.scalars():
            order = await session.scalar(
                select(Order).where(Order.id == transaction.migrated_order_id)
            )

            assert order is not None, f"Missing order for transaction {transaction.id}"
            assert order.amount == transaction.sale_price
            assert order.net_profit == transaction.net_profit
            # ... more assertions
```

### Rollback Plan
1. Keep Transaction table intact (don't delete)
2. Add `migrated_to_order` flag to track migration status
3. Create reverse migration script (Order → Transaction)
4. Database backup before migration
5. Run migration in staging first

### Monitoring
- Log all migration operations
- Track migration progress
- Alert on validation failures
- Monitor performance impact

---

## Testing Strategy

### Unit Tests
```python
class TestOrderImportService:
    async def test_import_generic_orders_from_csv():
        """Test importing orders from CSV (replaces TransactionProcessor)"""

    async def test_import_stockx_orders():
        """Test existing StockX import"""

    async def test_platform_specific_data_storage():
        """Test JSONB storage for different platforms"""
```

### Integration Tests
```python
async def test_full_import_pipeline():
    """Test end-to-end: CSV → Order creation"""

async def test_transaction_to_order_adapter():
    """Test adapter converts Transaction data correctly"""

async def test_backward_compatibility():
    """Ensure legacy Transaction queries still work"""
```

### Migration Tests
```python
async def test_migrate_transactions_to_orders():
    """Test migration script"""

async def test_data_integrity_after_migration():
    """Validate no data loss"""
```

---

## Success Criteria

- [ ] All Transaction data migrated to Order table
- [ ] OrderImportService supports all platforms (CSV, StockX, eBay, GOAT, Alias)
- [ ] ImportProcessor uses OrderImportService
- [ ] TransactionProcessor marked deprecated
- [ ] Zero data loss verified
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team trained on new flow

---

## Rollout Strategy

### Week 1: Implementation
- Days 1-3: Build OrderImportService extensions
- Days 4-5: Create migration script
- Day 6: Testing in staging

### Week 2: Deployment
- Day 1: Run migration in production (off-hours)
- Day 2: Monitor for issues
- Days 3-5: Update dependent services gradually
- Day 6-7: Complete documentation

### Post-Deployment (Week 3+)
- Monitor error rates
- Gather developer feedback
- Gradual deprecation of TransactionProcessor
- After 3 months: Consider removing TransactionProcessor entirely

---

## Alternative: Quick Win (If time-constrained)

If full consolidation is too ambitious right now, do a **minimal viable refactoring**:

1. **Create OrderService facade**
   ```python
   class UnifiedOrderService:
       """Facade that routes to appropriate service"""

       def __init__(self, db_session):
           self.order_import = OrderImportService(db_session)
           self.transaction_processor = TransactionProcessor(db_session)

       async def import_orders(
           self,
           data: List[Dict],
           source: str
       ) -> Dict[str, Any]:
           """Route to appropriate service based on source"""
           if source in ["stockx", "ebay", "goat"]:
               return await self.order_import.import_stockx_orders(data)
           else:
               # Legacy CSV imports
               return await self.transaction_processor.create_transactions(data)
   ```

2. **Document the separation**
   - Transaction = legacy CSV imports only
   - Order = all API-based imports
   - Add this to CLAUDE.md

3. **Plan full consolidation for Q2**

**Effort**: 1 day
**Risk**: Low
**Benefit**: Immediate clarity, buys time for full solution

---

## Recommendation

**Primary**: Implement **Option 1 (Full Consolidation)** over 2 weeks
**Fallback**: Implement **Quick Win** now, full consolidation in Q2

The Orders Domain with the `Order` model is clearly the more mature, feature-rich solution aligned with business needs. The investment in consolidation will pay off in:
- Reduced maintenance burden
- Better data integrity
- Clearer architecture
- Easier onboarding for new developers

---

**Status**: 📋 Ready for Implementation
**Next Action**: Review with team & get approval for migration plan
