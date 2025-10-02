# Analytics Views Migration Plan

**Status:** 📋 Planning Phase
**Target Completion:** 2025-10-15
**Priority:** High
**Blocked By:** None
**Blocks:** Legacy transactions table cleanup

## 📋 Overview

This document outlines the systematic migration of **18 analytics views** and **1 foreign key constraint** from the deprecated `transactions.transactions` table to the new unified `transactions.orders` table.

## 🎯 Objectives

1. Migrate all analytics views to use `transactions.orders`
2. Update foreign key in `finance.expenses` table
3. Verify data integrity and query performance
4. Enable cleanup of deprecated `transactions.transactions` table

## 📊 Dependencies Inventory

### Analytics Views (18 total)

| View Name | Schema | Complexity | Estimated Effort |
|-----------|--------|------------|------------------|
| `daily_revenue` | analytics | Low | 30 min |
| `monthly_revenue` | analytics | Low | 30 min |
| `top_products_revenue` | analytics | Medium | 1 hour |
| `platform_performance` | analytics | Medium | 1 hour |
| `sales_by_country` | analytics | Low | 30 min |
| `executive_dashboard` | analytics | High | 2 hours |
| `sales_by_weekday` | analytics | Low | 30 min |
| `recent_transactions` | analytics | Low | 20 min |
| `revenue_growth` | analytics | Medium | 1 hour |
| `brand_deep_dive_overview` | analytics | High | 2 hours |
| `nike_product_breakdown` | analytics | High | 2 hours |
| `brand_monthly_performance` | analytics | Medium | 1 hour |
| `daily_sales` | analytics | Low | 30 min |
| `top_products` | analytics | Medium | 1 hour |
| `data_quality_check` | analytics | Low | 30 min |
| `brand_collaboration_performance` | analytics | Medium | 1 hour |
| `brand_market_position` | analytics | High | 2 hours |

**Total Estimated Effort:** 17 hours

### Foreign Key Constraints (1 total)

| Constraint | Source Table | Target Table | Impact |
|------------|--------------|--------------|--------|
| `expenses_transaction_id_fkey` | `finance.expenses` | `transactions.transactions` | Medium |

## 🗺️ Field Mapping Reference

### Column Name Changes

| Old (`transactions`) | New (`orders`) | Notes |
|----------------------|----------------|-------|
| `transaction_date` | `sold_at` | Timestamp when order completed |
| `sale_price` | `gross_sale` | Sale price before fees |
| `net_profit` | `net_profit` | ✅ No change |
| `platform_fee` | `platform_fee` | ✅ No change |
| `shipping_cost` | `shipping_cost` | ✅ No change |
| `status` | `status` | ✅ No change |
| `external_id` | `external_id` | ✅ No change |
| `notes` | `notes` | ✅ No change |
| `inventory_id` | `inventory_item_id` | ⚠️ Field renamed |
| `buyer_destination_country` | `buyer_destination_country` | ✅ No change |
| `buyer_destination_city` | `buyer_destination_city` | ✅ No change |

### New Fields Available in `orders`

| Field | Type | Description | Use Case |
|-------|------|-------------|----------|
| `net_proceeds` | NUMERIC | Net after platform fees | More accurate profit calculation |
| `gross_profit` | NUMERIC | Sale - Purchase | Simplified profitability |
| `roi` | NUMERIC | Return on investment % | Performance metrics |
| `payout_received` | BOOLEAN | Payment confirmed | Cash flow tracking |
| `payout_date` | TIMESTAMP | When paid out | Cash flow timing |
| `shelf_life_days` | INTEGER | Days until sold | Inventory velocity |
| `stockx_order_number` | VARCHAR | StockX-specific ID | Platform-specific tracking |
| `raw_data` | JSONB | Full order payload | Detailed analysis |

## 🔄 Migration Strategy

### Phase 1: View Analysis (1 day)

**Goal:** Extract and document all current view definitions

```bash
# Export all view definitions
psql $DATABASE_URL -c "\d+ analytics.daily_revenue" > views_backup/daily_revenue.sql
psql $DATABASE_URL -c "\d+ analytics.monthly_revenue" > views_backup/monthly_revenue.sql
# ... repeat for all 18 views

# Create complete backup
pg_dump --schema=analytics --schema-only $DATABASE_URL > analytics_schema_backup.sql
```

**Deliverables:**
- [ ] Backup directory with all view definitions
- [ ] Dependency graph showing view relationships
- [ ] Complexity assessment for each view

### Phase 2: View Migration (Low Complexity) (2 days)

**Views:** `daily_revenue`, `monthly_revenue`, `sales_by_country`, `sales_by_weekday`, `recent_transactions`, `daily_sales`, `data_quality_check`

**Example Migration:**

```sql
-- Step 1: Backup current view
CREATE VIEW analytics.daily_revenue_backup AS
SELECT * FROM analytics.daily_revenue;

-- Step 2: Create new view
CREATE OR REPLACE VIEW analytics.daily_revenue AS
SELECT
    DATE(sold_at) as date,  -- Changed from transaction_date
    platform_id,
    SUM(gross_sale) as gross_revenue,  -- Changed from sale_price
    SUM(net_proceeds) as net_revenue,  -- NEW: More accurate
    SUM(platform_fee) as total_fees,
    SUM(net_profit) as profit,
    COUNT(*) as order_count
FROM transactions.orders  -- Changed from transactions.transactions
WHERE status = 'completed'
GROUP BY DATE(sold_at), platform_id
ORDER BY date DESC;

-- Step 3: Validate output
SELECT * FROM analytics.daily_revenue WHERE date = '2024-01-01'
EXCEPT
SELECT * FROM analytics.daily_revenue_backup WHERE date = '2024-01-01';
-- Should return 0 rows (identical data)

-- Step 4: Drop backup if validation passes
DROP VIEW analytics.daily_revenue_backup;
```

**Quality Checks:**
- [ ] Row counts match between old and new views
- [ ] Aggregated totals match (±0.01 for rounding)
- [ ] Date ranges preserved
- [ ] No NULL values introduced

### Phase 3: View Migration (Medium Complexity) (3 days)

**Views:** `top_products_revenue`, `platform_performance`, `revenue_growth`, `brand_monthly_performance`, `top_products`, `brand_collaboration_performance`

**Example Migration:**

```sql
-- More complex view with multiple joins
CREATE OR REPLACE VIEW analytics.platform_performance AS
SELECT
    p.name as platform_name,
    p.slug as platform_slug,
    DATE_TRUNC('month', o.sold_at) as month,  -- Changed field
    COUNT(*) as total_orders,
    SUM(o.gross_sale) as gross_revenue,
    SUM(o.platform_fee) as total_fees,
    SUM(o.net_proceeds) as net_revenue,
    SUM(o.net_profit) as total_profit,
    AVG(o.roi) as avg_roi,  -- NEW: ROI tracking
    AVG(o.shelf_life_days) as avg_shelf_life,  -- NEW: Velocity metric
    COUNT(CASE WHEN o.payout_received THEN 1 END) as paid_out_count,  -- NEW
    SUM(CASE WHEN o.payout_received THEN o.net_proceeds ELSE 0 END) as paid_out_amount  -- NEW
FROM transactions.orders o  -- Changed table
JOIN core.platforms p ON p.id = o.platform_id
WHERE o.status = 'completed'
GROUP BY p.name, p.slug, DATE_TRUNC('month', o.sold_at)
ORDER BY month DESC, gross_revenue DESC;
```

**Quality Checks:**
- [ ] JOIN performance maintained
- [ ] Aggregations correct
- [ ] New metrics add value

### Phase 4: View Migration (High Complexity) (4 days)

**Views:** `executive_dashboard`, `brand_deep_dive_overview`, `nike_product_breakdown`, `brand_market_position`

**Considerations:**
- Multiple nested subqueries
- Complex window functions
- Performance-critical dashboards
- May need materialized views for performance

**Example Strategy:**

```sql
-- Convert to materialized view if needed
CREATE MATERIALIZED VIEW analytics.executive_dashboard AS
WITH monthly_metrics AS (
    SELECT
        DATE_TRUNC('month', sold_at) as month,
        COUNT(*) as orders,
        SUM(gross_sale) as revenue,
        SUM(net_profit) as profit,
        AVG(roi) as avg_roi
    FROM transactions.orders
    WHERE status = 'completed'
    GROUP BY DATE_TRUNC('month', sold_at)
),
growth_metrics AS (
    SELECT
        month,
        orders,
        revenue,
        profit,
        LAG(revenue) OVER (ORDER BY month) as prev_month_revenue,
        (revenue - LAG(revenue) OVER (ORDER BY month)) /
            NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100 as revenue_growth_pct
    FROM monthly_metrics
)
SELECT * FROM growth_metrics
ORDER BY month DESC;

-- Create refresh schedule
CREATE INDEX ON analytics.executive_dashboard (month);

-- Auto-refresh strategy
CREATE OR REPLACE FUNCTION refresh_executive_dashboard()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.executive_dashboard;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

**Quality Checks:**
- [ ] Dashboard loads in <2 seconds
- [ ] Historical data matches exactly
- [ ] Refresh strategy tested
- [ ] Materialized view indexes optimized

### Phase 5: Foreign Key Migration (1 day)

**Constraint:** `finance.expenses.transaction_id` → `transactions.orders.id`

```sql
-- Step 1: Check current usage
SELECT COUNT(*) FROM finance.expenses;
SELECT COUNT(*) FROM finance.expenses e
JOIN transactions.transactions t ON e.transaction_id = t.id;

-- Step 2: Analyze data integrity
SELECT e.id, e.transaction_id
FROM finance.expenses e
LEFT JOIN transactions.orders o ON e.transaction_id = o.id
WHERE o.id IS NULL;
-- Should return 0 rows (all expenses have matching orders)

-- Step 3: Drop old constraint
ALTER TABLE finance.expenses
DROP CONSTRAINT expenses_transaction_id_fkey;

-- Step 4: Rename column if needed (optional)
ALTER TABLE finance.expenses
RENAME COLUMN transaction_id TO order_id;

-- Step 5: Add new constraint
ALTER TABLE finance.expenses
ADD CONSTRAINT expenses_order_id_fkey
FOREIGN KEY (order_id)
REFERENCES transactions.orders(id)
ON DELETE RESTRICT;

-- Step 6: Validate
SELECT COUNT(*) FROM finance.expenses e
JOIN transactions.orders o ON e.order_id = o.id;
```

### Phase 6: Testing & Validation (2 days)

**Test Plan:**

1. **Data Integrity Tests**
```sql
-- Compare totals across all views
SELECT
    'old' as source,
    COUNT(*) as total_records,
    SUM(sale_price) as total_revenue
FROM transactions.transactions
UNION ALL
SELECT
    'new' as source,
    COUNT(*) as total_records,
    SUM(gross_sale) as total_revenue
FROM transactions.orders;
-- Totals should match
```

2. **Performance Tests**
```sql
-- Benchmark view queries
EXPLAIN ANALYZE SELECT * FROM analytics.executive_dashboard;
-- Compare with old view performance
```

3. **Dashboard Tests**
- [ ] Load all dashboards in Metabase
- [ ] Verify chart data matches historical
- [ ] Check for broken queries
- [ ] Test date range filters

4. **API Tests**
- [ ] Run analytics API test suite
- [ ] Verify JSON response formats
- [ ] Check pagination still works
- [ ] Test error handling

### Phase 7: Legacy Table Cleanup (1 day)

**Prerequisites:**
- ✅ All 18 views migrated and validated
- ✅ Foreign key constraint updated
- ✅ 7 days of production monitoring (no errors)
- ✅ Stakeholder approval

**Cleanup Steps:**

```sql
-- Step 1: Final verification
SELECT
    schemaname,
    viewname,
    definition
FROM pg_views
WHERE definition LIKE '%transactions.transactions%'
  AND schemaname NOT IN ('pg_catalog', 'information_schema');
-- Should return 0 rows

-- Step 2: Check for any remaining foreign keys
SELECT
    tc.constraint_name,
    tc.table_schema,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE ccu.table_name = 'transactions'
  AND ccu.table_schema = 'transactions';
-- Should return 0 rows

-- Step 3: Create final backup
CREATE TABLE transactions.transactions_archive AS
SELECT * FROM transactions.transactions;

-- Step 4: Drop the legacy table
DROP TABLE transactions.transactions CASCADE;

-- Step 5: Document in migrations
-- Create Alembic migration: drop_legacy_transactions_table
```

## 📋 Validation Checklist

### Pre-Migration

- [ ] All view definitions backed up to `views_backup/`
- [ ] Full database backup created
- [ ] Stakeholders notified of migration schedule
- [ ] Rollback plan documented

### Per-View Migration

- [ ] View definition updated
- [ ] Row count matches old view
- [ ] Sample queries return identical results
- [ ] Performance benchmarked (no degradation)
- [ ] Dependent dashboards tested
- [ ] Changes committed to git

### Post-Migration

- [ ] All 18 views using `transactions.orders`
- [ ] Foreign key updated
- [ ] 7 days production monitoring completed
- [ ] No errors in logs related to views
- [ ] Dashboard performance acceptable
- [ ] Analytics reports match historical data
- [ ] Legacy table dropped
- [ ] Documentation updated

## 🚨 Rollback Plan

### If View Migration Fails

```sql
-- Restore from backup
CREATE OR REPLACE VIEW analytics.{view_name} AS
SELECT * FROM {backup_view_name};

-- Or restore from file
psql $DATABASE_URL < views_backup/{view_name}.sql
```

### If Performance Degrades

```sql
-- Revert to old table
CREATE OR REPLACE VIEW analytics.{view_name} AS
-- [original definition using transactions.transactions]

-- Add indexes to new table
CREATE INDEX idx_orders_sold_at ON transactions.orders(sold_at);
CREATE INDEX idx_orders_platform_status ON transactions.orders(platform_id, status);
```

### If Data Mismatch Found

```sql
-- Keep both views for comparison
CREATE VIEW analytics.{view_name}_new AS
SELECT * FROM transactions.orders ...;

CREATE VIEW analytics.{view_name}_old AS
SELECT * FROM transactions.transactions ...;

-- Investigate differences
SELECT * FROM analytics.{view_name}_new
EXCEPT
SELECT * FROM analytics.{view_name}_old;
```

## 📊 Success Metrics

### Migration Success Criteria

- ✅ All 18 views migrated within 2 weeks
- ✅ Zero data loss or corruption
- ✅ No performance degradation (max +10% query time)
- ✅ Zero production incidents related to migration
- ✅ All stakeholder dashboards functional
- ✅ Foreign key successfully updated
- ✅ Legacy table successfully dropped

### Post-Migration Metrics

- **Query Performance**: <2s for complex dashboards
- **Data Freshness**: Real-time (no materialization delay)
- **Dashboard Uptime**: 99.9%
- **Error Rate**: 0% related to views

## 📅 Timeline

| Phase | Duration | Start Date | End Date | Owner |
|-------|----------|------------|----------|-------|
| Phase 1: Analysis | 1 day | 2025-10-02 | 2025-10-02 | TBD |
| Phase 2: Low Complexity | 2 days | 2025-10-03 | 2025-10-04 | TBD |
| Phase 3: Medium Complexity | 3 days | 2025-10-05 | 2025-10-09 | TBD |
| Phase 4: High Complexity | 4 days | 2025-10-10 | 2025-10-13 | TBD |
| Phase 5: Foreign Key | 1 day | 2025-10-14 | 2025-10-14 | TBD |
| Phase 6: Testing | 2 days | 2025-10-15 | 2025-10-16 | TBD |
| Phase 7: Cleanup | 1 day | 2025-10-23 | 2025-10-23 | TBD |

**Total Duration:** 14 working days (3 weeks with buffer)

## 🔗 Related Documentation

- `context/orders-multi-platform-migration.md` - Main migration overview
- `migrations/versions/2025_10_01_0730_84bc4d8b03ef_*.py` - Schema migration
- `shared/database/models.py:436` - Order model definition
- `domains/analytics/` - Analytics domain implementation

## 📝 Notes

### Performance Considerations

- Consider materialized views for complex dashboards
- Add appropriate indexes on `sold_at`, `platform_id`, `status`
- Monitor query performance during migration
- Use `EXPLAIN ANALYZE` for optimization

### Data Integrity

- The new `orders` table has MORE data than legacy
- New fields (`roi`, `shelf_life_days`) enhance analytics
- All historical data preserved (2020-2025)
- No changes to underlying transaction data

### Team Communication

- Daily standup updates during migration
- Slack notifications for each phase completion
- Stakeholder demo after Phase 6
- Post-mortem after cleanup

---

**Document Version:** 1.0
**Last Updated:** 2025-10-01
**Status:** 📋 Planning Phase
**Next Review:** 2025-10-02
