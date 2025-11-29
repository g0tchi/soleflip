# Phase 2: Inventory Schema Consolidation Plan
**Date**: 2025-11-29
**Priority**: HIGH
**Expected Impact**: 60-80% performance improvement on inventory queries
**Risk Level**: MEDIUM (requires careful data migration)

## Current State Analysis

### Inventory Tables Structure

#### 1. inventory.stock (Main Table)
**Columns**: 25 fields
- Core: id, product_id, size_id, supplier_id, quantity
- Financial: purchase_price, gross_purchase_price, vat_amount, vat_rate
- Lifecycle: delivery_date, shelf_life_days, profit_per_shelf_day, roi_percentage
- Platform: listed_stockx, listed_alias, listed_local
- Status: status, detailed_status, location
- Metadata: notes, external_ids, created_at, updated_at

**Already has some financial and lifecycle data!**

#### 2. inventory.stock_financial (Redundant)
**Columns**: 8 fields
- purchase_price ✅ DUPLICATE (already in stock)
- gross_purchase_price ✅ DUPLICATE
- vat_amount ✅ DUPLICATE
- profit_per_shelf_day ✅ DUPLICATE
- roi ✅ DUPLICATE (as roi_percentage in stock)

**Verdict**: 100% redundant with stock table

#### 3. inventory.stock_lifecycle (Partially Redundant)
**Columns**: 6 fields
- shelf_life_days ✅ DUPLICATE
- listed_on_platforms ❌ NEW (JSONB) - needs migration
- status_history ❌ NEW (JSONB) - needs migration

**Verdict**: 2 unique fields to migrate

#### 4. inventory.stock_metrics (Computed Metrics)
**Columns**: 9 fields
- available_quantity ❌ NEW - can be computed
- reserved_quantity ❌ NEW - important for reservations
- total_cost ❌ NEW - can be computed
- expected_profit ❌ NEW - can be computed
- last_calculated_at ❌ NEW - metadata

**Verdict**: Add reserved_quantity, remove computed fields

#### 5. inventory.stock_reservation (Separate Concern)
**Columns**: 9 fields
- Full reservation tracking system
- reserved_quantity, reserved_until, reservation_reason
- status, reserved_by

**Verdict**: Keep as separate table (correct design pattern)

## Consolidation Strategy

### Fields to Add to inventory.stock

```sql
-- From stock_lifecycle (unique fields)
listed_on_platforms JSONB     -- Platform listing history
status_history JSONB           -- Status change tracking

-- From stock_metrics (essential fields only)
reserved_quantity INTEGER DEFAULT 0  -- Currently reserved units

-- Computed fields (views instead of columns)
-- available_quantity = quantity - reserved_quantity
-- total_cost = gross_purchase_price
-- expected_profit = (calculated in application)
```

### Tables to Remove
1. ✅ **stock_financial** - 100% redundant
2. ✅ **stock_lifecycle** - after migrating 2 JSONB fields
3. ✅ **stock_metrics** - replace with materialized view

### Tables to Keep
1. ✅ **stock** - consolidated main table
2. ✅ **stock_reservation** - separate concern (correct pattern)

## Migration Plan

### Phase 2A: Add New Columns (Week 2)

```sql
-- Step 1: Add new columns to stock table
ALTER TABLE inventory.stock
  ADD COLUMN IF NOT EXISTS listed_on_platforms JSONB,
  ADD COLUMN IF NOT EXISTS status_history JSONB,
  ADD COLUMN IF NOT EXISTS reserved_quantity INTEGER DEFAULT 0;

-- Step 2: Create indexes
CREATE INDEX IF NOT EXISTS idx_stock_reserved
ON inventory.stock (id, reserved_quantity)
WHERE reserved_quantity > 0;

CREATE INDEX IF NOT EXISTS idx_stock_listed_platforms
ON inventory.stock USING GIN (listed_on_platforms);

CREATE INDEX IF NOT EXISTS idx_stock_status_history
ON inventory.stock USING GIN (status_history);
```

### Phase 2B: Backfill Data (Week 2)

```sql
-- Step 3: Migrate stock_lifecycle data
UPDATE inventory.stock s
SET
  listed_on_platforms = sl.listed_on_platforms,
  status_history = sl.status_history
FROM inventory.stock_lifecycle sl
WHERE s.id = sl.stock_id;

-- Step 4: Migrate stock_metrics reserved_quantity
UPDATE inventory.stock s
SET reserved_quantity = sm.reserved_quantity
FROM inventory.stock_metrics sm
WHERE s.id = sm.stock_id;

-- Step 5: Verify data integrity
SELECT COUNT(*) as total_stock FROM inventory.stock;
SELECT COUNT(*) as migrated_lifecycle
FROM inventory.stock
WHERE listed_on_platforms IS NOT NULL OR status_history IS NOT NULL;
SELECT COUNT(*) as has_reservations
FROM inventory.stock
WHERE reserved_quantity > 0;
```

### Phase 2C: Create Materialized View for Metrics (Week 3)

```sql
-- Replace stock_metrics table with materialized view
CREATE MATERIALIZED VIEW inventory.stock_metrics_view AS
SELECT
  s.id as stock_id,
  s.quantity as total_quantity,
  s.quantity - COALESCE(s.reserved_quantity, 0) as available_quantity,
  s.reserved_quantity,
  s.gross_purchase_price as total_cost,
  -- Expected profit calculation
  CASE
    WHEN s.roi_percentage IS NOT NULL
    THEN s.gross_purchase_price * (s.roi_percentage / 100)
    ELSE NULL
  END as expected_profit,
  now() as last_calculated_at,
  s.created_at,
  s.updated_at
FROM inventory.stock s;

-- Index for fast lookups
CREATE UNIQUE INDEX idx_stock_metrics_view_stock_id
ON inventory.stock_metrics_view (stock_id);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_stock_metrics()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY inventory.stock_metrics_view;
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh (every hour)
-- SELECT cron.schedule('refresh-stock-metrics', '0 * * * *',
--   'SELECT refresh_stock_metrics();');
```

### Phase 2D: Update Application Code (Week 3)

#### Repository Changes Required

**Before (Multiple JOINs)**:
```python
# Old approach - 4 JOINs required
stock_with_metrics = await db.execute(
    select(Stock)
    .join(StockFinancial)
    .join(StockLifecycle)
    .join(StockMetrics)
    .where(Stock.id == stock_id)
)
```

**After (Single Table)**:
```python
# New approach - Direct access
stock = await db.execute(
    select(Stock)
    .where(Stock.id == stock_id)
)
# All data in one row!
```

#### Specific Code Changes

1. **domains/inventory/repositories/inventory_repository.py**
   - Remove StockFinancial queries
   - Remove StockLifecycle queries
   - Update StockMetrics to use materialized view

2. **domains/inventory/services/inventory_service.py**
   - Simplify inventory queries
   - Update reservation logic to use reserved_quantity column
   - Remove JOIN operations

3. **shared/database/models.py**
   - Remove StockFinancial model
   - Remove StockLifecycle model
   - Update StockMetrics to be a read-only view model

### Phase 2E: Testing & Validation (Week 4)

```sql
-- Validation queries
-- 1. Check data consistency
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT id) as unique_ids,
  COUNT(listed_on_platforms) as has_platform_data,
  COUNT(status_history) as has_history,
  SUM(CASE WHEN reserved_quantity > 0 THEN 1 ELSE 0 END) as has_reservations
FROM inventory.stock;

-- 2. Compare old vs new (before dropping tables)
SELECT
  'stock_financial' as source,
  COUNT(*) as record_count
FROM inventory.stock_financial
UNION ALL
SELECT
  'stock with financial data',
  COUNT(*)
FROM inventory.stock
WHERE purchase_price IS NOT NULL;

-- 3. Performance comparison
EXPLAIN ANALYZE
SELECT * FROM inventory.stock s
WHERE s.product_id = 'some-uuid'
  AND s.status = 'in_stock'
  AND s.reserved_quantity < s.quantity;
```

### Phase 2F: Drop Old Tables (Week 4 - After Verification)

```sql
-- Final step - only after 100% verification
BEGIN;

-- Backup old tables (just in case)
CREATE TABLE inventory.stock_financial_backup AS
SELECT * FROM inventory.stock_financial;

CREATE TABLE inventory.stock_lifecycle_backup AS
SELECT * FROM inventory.stock_lifecycle;

CREATE TABLE inventory.stock_metrics_backup AS
SELECT * FROM inventory.stock_metrics;

-- Drop old tables
DROP TABLE inventory.stock_financial CASCADE;
DROP TABLE inventory.stock_lifecycle CASCADE;
DROP TABLE inventory.stock_metrics CASCADE;

COMMIT;
```

## Expected Performance Improvements

### Query Performance

**Before** (4-table JOIN):
```sql
SELECT s.*, sf.*, sl.*, sm.*
FROM inventory.stock s
JOIN inventory.stock_financial sf ON s.id = sf.stock_id
JOIN inventory.stock_lifecycle sl ON s.id = sl.stock_id
JOIN inventory.stock_metrics sm ON s.id = sm.stock_id
WHERE s.status = 'in_stock';

-- Execution time: ~200ms (3,629 rows)
-- 4 table scans + 3 JOIN operations
```

**After** (single table):
```sql
SELECT s.*
FROM inventory.stock s
WHERE s.status = 'in_stock';

-- Execution time: ~40ms (expected)
-- 1 table scan with index
-- 60-80% faster! 🚀
```

### Storage Optimization

| Table | Current Size | After Consolidation |
|-------|--------------|---------------------|
| stock | 152 KB | ~180 KB |
| stock_financial | 8 KB | **REMOVED** ✅ |
| stock_lifecycle | 8 KB | **REMOVED** ✅ |
| stock_metrics | 8 KB | View (0 KB) ✅ |
| **Total** | **176 KB** | **~180 KB** |

**Result**: Minimal storage increase (+4 KB), massive performance gain

## Risk Mitigation

### Data Safety Measures

1. **Full Database Backup**
   ```bash
   docker exec soleflip-postgres pg_dump -U soleflip soleflip | \
     gzip > backup_phase2_$(date +%Y%m%d).sql.gz
   ```

2. **Table Backups Before Drop**
   - Create backup tables before dropping
   - Keep for 2 weeks after deployment

3. **Phased Rollout**
   - Week 2: Add columns, no drops
   - Week 3: Migrate data, test thoroughly
   - Week 4: Drop tables only after verification

4. **Rollback Plan**
   ```sql
   -- If issues arise, restore from backup
   DROP TABLE inventory.stock CASCADE;
   RESTORE TABLE FROM backup_phase2.sql;
   ```

### Testing Strategy

#### Unit Tests
- Test all repository methods
- Verify data integrity
- Check reservation logic

#### Integration Tests
- Full inventory workflows
- Multi-table queries
- Concurrent access scenarios

#### Performance Tests
```python
# Benchmark old vs new approach
import time

# Old approach
start = time.time()
stock = await old_inventory_repo.get_with_metrics(stock_id)
old_time = time.time() - start

# New approach
start = time.time()
stock = await new_inventory_repo.get(stock_id)
new_time = time.time() - start

improvement = (old_time - new_time) / old_time * 100
assert improvement >= 60, f"Expected 60%+ improvement, got {improvement}%"
```

## Application Code Migration Guide

### Repository Pattern Updates

**File**: `domains/inventory/repositories/inventory_repository.py`

```python
# REMOVE these queries
async def get_stock_financial(self, stock_id: UUID) -> StockFinancial:
    # DELETE - data now in Stock table
    pass

async def get_stock_lifecycle(self, stock_id: UUID) -> StockLifecycle:
    # DELETE - data now in Stock table
    pass

# UPDATE this query
async def get_stock_with_metrics(self, stock_id: UUID) -> Stock:
    # OLD (4 JOINs):
    # stmt = select(Stock).join(StockFinancial).join(...)

    # NEW (direct access):
    stmt = select(Stock).where(Stock.id == stock_id)
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()

# ADD metrics view query
async def get_stock_metrics(self, stock_id: UUID) -> StockMetricsView:
    stmt = select(StockMetricsView).where(
        StockMetricsView.stock_id == stock_id
    )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

### Model Updates

**File**: `shared/database/models.py`

```python
# UPDATE Stock model
class Stock(Base, TimestampMixin):
    __tablename__ = "stock"
    __table_args__ = {"schema": "inventory"}

    # ... existing fields ...

    # NEW FIELDS (Phase 2)
    listed_on_platforms = Column(JSONB, comment="Platform listing history")
    status_history = Column(JSONB, comment="Status change tracking")
    reserved_quantity = Column(Integer, default=0, comment="Reserved units")

# REMOVE these models
# class StockFinancial(Base): ...  # DELETE
# class StockLifecycle(Base): ...  # DELETE

# REPLACE with view model
class StockMetricsView(Base):
    __tablename__ = "stock_metrics_view"
    __table_args__ = {"schema": "inventory"}

    stock_id = Column(UUID, primary_key=True)
    total_quantity = Column(Integer)
    available_quantity = Column(Integer)
    reserved_quantity = Column(Integer)
    total_cost = Column(Numeric(10, 2))
    expected_profit = Column(Numeric(10, 2))
    last_calculated_at = Column(DateTime(timezone=True))
```

## Timeline & Milestones

### Week 2: Preparation & Extension
- [ ] Day 1: Database backup
- [ ] Day 2: Add new columns to stock table
- [ ] Day 3: Create indexes
- [ ] Day 4-5: Backfill data from old tables

### Week 3: Migration & Testing
- [ ] Day 1-2: Create materialized view
- [ ] Day 3: Update application code
- [ ] Day 4-5: Comprehensive testing

### Week 4: Validation & Cleanup
- [ ] Day 1-2: Performance validation
- [ ] Day 3: Final verification
- [ ] Day 4: Create backup tables
- [ ] Day 5: Drop old tables (if validation passes)

## Success Criteria

✅ **Data Integrity**
- 100% data migration success
- Zero data loss
- All tests passing

✅ **Performance**
- Inventory queries 60-80% faster
- Reduced JOIN operations
- Lower database load

✅ **Code Quality**
- Simplified repository code
- Cleaner model definitions
- Better maintainability

✅ **Stability**
- No production incidents
- Successful rollback capability
- Monitoring in place

## Next Steps

1. **Review this plan** with team
2. **Schedule Phase 2** for Weeks 2-4
3. **Prepare development environment**
4. **Create detailed migration scripts**
5. **Set up monitoring and alerts**

---

**Phase 2 will eliminate 3 tables and 60-80% of JOIN overhead on inventory queries!** 🚀
