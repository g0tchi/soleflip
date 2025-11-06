# Sales vs Orders Domain Migration Plan
**Date:** 2025-11-05
**Priority:** 🔴 CRITICAL
**Estimated Effort:** 2-3 weeks

## Problem Statement

Two domains handling order/transaction logic with different database models:

- **Sales Domain** (Legacy): Uses `Transaction` model (financial.transaction table)
- **Orders Domain** (Current v2.3.1): Uses `Order` model (sales.order table)

This creates confusion, potential data duplication, and unclear domain boundaries.

---

## Current State Analysis

### Sales Domain (`domains/sales/`)

**Files:**
- `services/transaction_processor.py` (498 LOC)
- `__init__.py`
- `services/__init__.py`

**Database Model:**
```python
class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = {"schema": "financial"}

    id = UUID
    inventory_id = UUID (FK → stock.id)
    platform_id = UUID (FK → marketplace.id)
    transaction_date = DateTime
    sale_price = Numeric(10, 2)
    platform_fee = Numeric(10, 2)
    shipping_cost = Numeric(10, 2)
    net_profit = Numeric(10, 2)
    status = String
    external_id = String
    buyer_destination_country = String
    buyer_destination_city = String
    notes = Text
```

**Responsibilities:**
- Create transactions from validated import data
- Handle platform fee calculations
- Create/link inventory items
- Create/link products and sizes

**Used By:**
- `domains/integration/services/import_processor.py` (line 278)

### Orders Domain (`domains/orders/`)

**Files:**
- `services/order_import_service.py` (400 LOC)
- `api/router.py`
- `__init__.py`
- `services/__init__.py`

**Database Model:**
```python
class Order(Base):
    __tablename__ = "order"
    __table_args__ = {"schema": "sales"}

    id = UUID
    inventory_item_id = UUID (FK → stock.id)
    listing_id = UUID (FK → listing.id)
    stockx_order_number = String(100, unique=True)
    status = String(50)
    amount = Numeric(10, 2)
    currency_code = String(10)
    # ... additional StockX-specific fields
```

**Responsibilities:**
- Import orders from StockX API
- Handle multi-platform orders (StockX, eBay, GOAT)
- Brand and category extraction via Products domain
- Upsert logic for order updates

**Used By:**
- `domains/integration/api/upload_router.py` (line 183)
- `domains/integration/api/webhooks.py` (line 22)

---

## Migration Strategy: Option A (Recommended)

**Consolidate into Orders Domain**

### Rationale
1. Orders is the v2.3.1 unified multi-platform approach
2. Better naming (Orders > Transactions for e-commerce)
3. More complete feature set for marketplace integrations
4. API already exists in Orders domain
5. Aligns with modern architecture documentation

### Migration Steps

#### Phase 1: Data Model Unification (Week 1)

**Step 1.1: Extend Order Model**
Add missing Transaction fields to Order model:

```python
# shared/database/models.py - Order model additions
class Order(Base):
    # ... existing fields ...

    # Financial fields from Transaction
    sale_price = Column(Numeric(10, 2))
    platform_fee = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2), default=0)
    net_profit = Column(Numeric(10, 2))

    # Transaction metadata
    transaction_date = Column(DateTime(timezone=True))
    buyer_destination_country = Column(String(100))
    buyer_destination_city = Column(String(100))
    external_transaction_id = Column(String(200))  # Merge with external_id

    # Keep existing platform tracking
    platform_source = Column(String(50))  # 'stockx', 'ebay', 'goat', etc.
```

**Step 1.2: Create Migration**
```bash
alembic revision --autogenerate -m "Merge Transaction fields into Order model"
```

**Step 1.3: Data Migration Script**
Create migration to copy existing Transaction data to Order table:

```python
# migrations/versions/XXXX_merge_transactions_to_orders.py
def upgrade():
    # Copy financial.transaction → sales.order
    op.execute("""
        INSERT INTO sales.order (
            id, inventory_item_id, transaction_date,
            sale_price, platform_fee, shipping_cost, net_profit,
            status, external_transaction_id,
            buyer_destination_country, buyer_destination_city,
            platform_source, notes, created_at, updated_at
        )
        SELECT
            t.id, t.inventory_id, t.transaction_date,
            t.sale_price, t.platform_fee, t.shipping_cost, t.net_profit,
            t.status, t.external_id,
            t.buyer_destination_country, t.buyer_destination_city,
            p.slug AS platform_source, t.notes, t.created_at, t.updated_at
        FROM financial.transaction t
        JOIN marketplace.platform p ON t.platform_id = p.id
        WHERE NOT EXISTS (
            SELECT 1 FROM sales.order o
            WHERE o.external_transaction_id = t.external_id
        )
    """)
```

#### Phase 2: Service Consolidation (Week 2)

**Step 2.1: Merge TransactionProcessor into OrderImportService**

Move logic from `transaction_processor.py` into `order_import_service.py`:

```python
# domains/orders/services/order_import_service.py

class OrderImportService:
    """Unified service for importing orders from all platforms"""

    async def import_orders_from_batch(
        self,
        batch_id: str,
        source: str = "csv"
    ) -> Dict[str, Any]:
        """
        Create orders from an import batch (CSV, StockX API, etc.)
        Replaces TransactionProcessor.create_transactions_from_batch
        """
        # Merge logic from both services
        pass

    async def import_stockx_orders(
        self,
        orders_data: List[Dict[str, Any]],
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Existing StockX API import (keep as-is)"""
        pass

    async def _create_order_from_import_record(
        self,
        import_record: ImportRecord
    ) -> bool:
        """
        Merge logic from:
        - TransactionProcessor._create_transaction_from_record
        - OrderImportService._import_single_stockx_order
        """
        pass
```

**Step 2.2: Update Integration Domain**

Update `import_processor.py`:

```python
# domains/integration/services/import_processor.py

from domains.orders.services.order_import_service import OrderImportService

class ImportProcessor:
    def __init__(
        self,
        db_session: AsyncSession,
        product_processor: Optional[ProductProcessor] = None,
        order_service: Optional[OrderImportService] = None,  # Changed from transaction_processor
    ):
        self.db_session = db_session
        self.product_processor = product_processor or ProductProcessor(db_session)
        self.order_service = order_service or OrderImportService(db_session)  # Changed

    async def _create_transactions_from_batch(self, batch_id: UUID, processed_count: int):
        """Now delegates to OrderImportService"""
        if processed_count == 0:
            return
        try:
            await self.order_service.import_orders_from_batch(str(batch_id))  # Changed
        except Exception as e:
            logger.error("Order creation failed", batch_id=batch_id, error=str(e))
```

**Step 2.3: Create Order Repository**

Add repository pattern to Orders domain:

```python
# domains/orders/repositories/order_repository.py

from shared.repositories.base_repository import BaseRepository
from shared.database.models import Order

class OrderRepository(BaseRepository[Order]):
    """Repository for Order data access"""

    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def find_by_external_id(self, external_id: str) -> Optional[Order]:
        """Find order by external transaction ID"""
        stmt = select(Order).where(Order.external_transaction_id == external_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def find_by_platform_and_order_number(
        self,
        platform: str,
        order_number: str
    ) -> Optional[Order]:
        """Find order by platform and order number"""
        stmt = select(Order).where(
            Order.platform_source == platform,
            Order.stockx_order_number == order_number
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
```

#### Phase 3: Testing & Validation (Week 2-3)

**Step 3.1: Update Tests**

Migrate tests from sales domain to orders domain:

```bash
# Move test files
mv tests/unit/sales/ tests/unit/orders/
mv tests/integration/sales/ tests/integration/orders/

# Update imports in test files
# Change: from domains.sales.services.transaction_processor import TransactionProcessor
# To: from domains.orders.services.order_import_service import OrderImportService
```

**Step 3.2: Run Test Suite**

```bash
make test
```

**Step 3.3: Validate Data Migration**

```sql
-- Check record counts match
SELECT 'Transactions' AS source, COUNT(*) FROM financial.transaction
UNION ALL
SELECT 'Orders (migrated)' AS source, COUNT(*) FROM sales.order
WHERE platform_source IN ('stockx', 'ebay', 'goat', 'alias', 'manual');

-- Validate financial totals match
SELECT
    SUM(sale_price) AS total_sales,
    SUM(net_profit) AS total_profit
FROM financial.transaction
WHERE transaction_date >= '2024-01-01';

-- Should match:
SELECT
    SUM(sale_price) AS total_sales,
    SUM(net_profit) AS total_profit
FROM sales.order
WHERE transaction_date >= '2024-01-01';
```

#### Phase 4: Deprecation & Cleanup (Week 3)

**Step 4.1: Mark Sales Domain as Deprecated**

```python
# domains/sales/__init__.py
"""
DEPRECATED: This domain has been merged into domains/orders/
All functionality now available in OrderImportService.

Migration completed: 2025-11-05
Scheduled for removal: 2025-12-01
"""
import warnings

warnings.warn(
    "Sales domain is deprecated. Use domains.orders instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**Step 4.2: Add Legacy Support (Optional)**

If immediate removal is risky, create compatibility layer:

```python
# domains/sales/services/transaction_processor.py
"""DEPRECATED - Use domains.orders.services.order_import_service instead"""

from domains.orders.services.order_import_service import OrderImportService

class TransactionProcessor:
    """
    DEPRECATED: Legacy wrapper for backward compatibility
    Redirects to OrderImportService
    """

    def __init__(self, db_session):
        warnings.warn(
            "TransactionProcessor is deprecated. Use OrderImportService instead.",
            DeprecationWarning
        )
        self._service = OrderImportService(db_session)

    async def create_transactions_from_batch(self, batch_id: str):
        """Delegate to OrderImportService"""
        return await self._service.import_orders_from_batch(batch_id)
```

**Step 4.3: Final Removal (After 4 weeks)**

```bash
# Remove sales domain
rm -rf domains/sales/

# Drop transaction table (after backup!)
alembic revision -m "Drop deprecated financial.transaction table"
# In migration: op.drop_table('transaction', schema='financial')
```

---

## Alternative: Option B (Not Recommended)

**Keep Both with Clear Separation**

If stakeholders require keeping both:

### Separation Strategy

**Sales Domain → Financial Transactions**
- Rename to `domains/financial/`
- Focus: Revenue tracking, accounting, P&L
- Model: Keep Transaction table
- Responsibilities:
  - Calculate net profit
  - Track platform fees
  - Generate financial reports
  - Tax calculations

**Orders Domain → Order Fulfillment**
- Keep as `domains/orders/`
- Focus: Order lifecycle, logistics
- Model: Keep Order table
- Responsibilities:
  - Order status tracking
  - Shipping coordination
  - Customer communication
  - Platform synchronization

**Integration:**
- Orders publishes `OrderCompleted` event
- Financial subscribes and creates Transaction record
- Clear one-way dependency: Orders → Financial

**Cons:**
- Duplicate data storage
- More complex synchronization
- Higher maintenance burden
- Potential inconsistencies

---

## Rollback Plan

If migration encounters critical issues:

### Phase 1 Rollback (Data Model)
```bash
alembic downgrade -1
```

### Phase 2 Rollback (Service Code)
```bash
git revert <commit-hash>
```

### Phase 3 Rollback (Data)
```sql
-- Re-sync Transaction table from Order table
TRUNCATE financial.transaction;
INSERT INTO financial.transaction (...)
SELECT ... FROM sales.order WHERE ...;
```

---

## Success Metrics

- ✅ All Transaction records migrated to Order table
- ✅ Financial totals match pre-migration
- ✅ All tests pass (unit, integration, API)
- ✅ No duplicate orders created
- ✅ Import workflows function correctly
- ✅ Sales domain removed from codebase
- ✅ Zero production incidents during migration

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss during migration | Low | Critical | Full database backup before migration |
| Test coverage gaps | Medium | High | Add integration tests for import workflows |
| Production errors | Medium | High | Feature flag for gradual rollout |
| Financial data mismatch | Low | Critical | Automated validation queries |
| Breaking API changes | Low | Medium | Keep legacy endpoints with deprecation warnings |

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | Data Model | Extended Order model, migration script, data copied |
| 2 | Service Layer | Merged services, updated imports, repository added |
| 2-3 | Testing | All tests passing, validation complete |
| 3 | Deprecation | Sales domain marked deprecated, docs updated |
| 7+ | Cleanup | Sales domain removed (after 4-week grace period) |

---

## Next Steps

1. ✅ Review this plan with team
2. 🔲 Get stakeholder approval
3. 🔲 Create feature branch: `feat/merge-sales-orders-domain`
4. 🔲 Execute Phase 1 (Data Model)
5. 🔲 Execute Phase 2 (Service Layer)
6. 🔲 Execute Phase 3 (Testing)
7. 🔲 Execute Phase 4 (Deprecation)
