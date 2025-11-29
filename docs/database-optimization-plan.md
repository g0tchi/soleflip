# SoleFlipper Database Optimization Plan
**Generated**: 2025-11-29
**Source**: Gibson AI Analysis + Claude Code Review

## Executive Summary

Gibson AI has identified **8 critical optimization areas** with potential for:
- **60-80% query performance improvement** on inventory queries
- **10x faster JSONB queries** with proper GIN indexes
- **100x faster time-series queries** with partitioning
- **30-40% storage reduction** through consolidation

---

## 🚨 Critical Issues (Immediate Attention)

### 1. Schema Redundancy - Inventory Domain

**Problem**: 5 fragmented tables causing unnecessary JOIN overhead
- `inventory.stock` (main)
- `inventory.stock_financial`
- `inventory.stock_lifecycle`
- `inventory.stock_metrics`
- `inventory.stock_reservation`

**Solution**: Consolidate into single `inventory.stock` table

**Impact**: Eliminates 3-4 JOINs per query, **60-80% performance gain**

**Implementation** (`migrations/consolidate_inventory.sql`):
```sql
ALTER TABLE inventory.stock
  ADD COLUMN purchase_price NUMERIC(10,2),
  ADD COLUMN sale_price NUMERIC(10,2),
  ADD COLUMN fees JSONB,
  ADD COLUMN lifecycle_status VARCHAR(20),
  ADD COLUMN state_changed_at TIMESTAMP,
  ADD COLUMN reserved_qty INT DEFAULT 0,
  ADD COLUMN reserved_by UUID,
  ADD COLUMN reservation_expires TIMESTAMP;

-- Backfill from fragmented tables
UPDATE inventory.stock s
SET
  purchase_price = sf.purchase_price,
  sale_price = sf.sale_price,
  fees = sf.fees,
  lifecycle_status = sl.status,
  state_changed_at = sl.changed_at,
  reserved_qty = COALESCE(sr.reserved_qty, 0),
  reserved_by = sr.reserved_by,
  reservation_expires = sr.expires_at
FROM inventory.stock_financial sf
LEFT JOIN inventory.stock_lifecycle sl ON sl.stock_id = s.id
LEFT JOIN inventory.stock_reservation sr ON sr.stock_id = s.id
WHERE sf.stock_id = s.id;

-- After verification, drop old tables
-- DROP TABLE inventory.stock_financial;
-- DROP TABLE inventory.stock_lifecycle;
-- DROP TABLE inventory.stock_metrics;
-- DROP TABLE inventory.stock_reservation;
```

---

### 2. Dual Transaction Tables

**Problem**: `financial.transaction` and `sales.order` overlap, creating reconciliation complexity

**Solution**: Deprecate `financial.transaction`, migrate to unified `sales.order` system

**Migration Strategy**:
```sql
-- Verify all financial.transaction records are in sales.order
SELECT COUNT(*) FROM financial.transaction t
WHERE NOT EXISTS (
  SELECT 1 FROM sales.order o
  WHERE o.external_id = t.external_id
);

-- After zero-count verification, mark as deprecated
ALTER TABLE financial.transaction
  ADD COLUMN deprecated BOOLEAN DEFAULT TRUE,
  ADD COLUMN migrated_to_order_id UUID;

-- Update references
UPDATE financial.transaction ft
SET migrated_to_order_id = o.id
FROM sales.order o
WHERE o.external_id = ft.external_id;
```

---

## ⚡ Quick Wins (Week 1 Implementation)

### 3. Multi-Platform JSONB Optimization

**Hybrid Approach**: Extract hot fields, keep JSONB for flexibility

```sql
-- Add frequently queried fields as dedicated columns
ALTER TABLE sales.order
  ADD COLUMN platform_order_id VARCHAR(100),
  ADD COLUMN shipping_cost NUMERIC(10,2),
  ADD COLUMN total_fees NUMERIC(10,2);

-- Populate from JSONB
UPDATE sales.order
SET
  platform_order_id = platform_specific_data->>'orderId',
  shipping_cost = (platform_specific_data->>'shippingCost')::numeric,
  total_fees = (platform_specific_data->>'totalFees')::numeric;

-- Create index for remaining queries
CREATE INDEX idx_order_platform_data ON sales.order USING GIN (platform_specific_data);

-- Same for listings
ALTER TABLE sales.listing
  ADD COLUMN platform_listing_id VARCHAR(100);

UPDATE sales.listing
SET platform_listing_id = platform_specific_data->>'listingId';

CREATE INDEX idx_listing_platform_data ON sales.listing USING GIN (platform_specific_data);
```

---

### 4. Critical Indexing Strategy

**Priority Indexes** (Deploy immediately):

```sql
-- JSONB Performance (10x improvement)
CREATE INDEX idx_order_platform_json ON sales.order USING GIN (platform_specific_data);
CREATE INDEX idx_listing_platform_json ON sales.listing USING GIN (platform_specific_data);
CREATE INDEX idx_product_enrichment ON catalog.product USING GIN (enrichment_data);

-- Composite Indexes for Frequent Joins
CREATE INDEX idx_stock_product_supplier ON inventory.stock (product_id, supplier_id);
CREATE INDEX idx_order_stock_platform ON sales.order (inventory_item_id, platform_id);
CREATE INDEX idx_price_history_product_date ON pricing.price_history (product_id, created_at DESC);

-- Partial Indexes (Hot Queries)
CREATE INDEX idx_active_stock ON inventory.stock (id, status) WHERE status = 'in_stock';
CREATE INDEX idx_pending_orders ON sales.order (id, status) WHERE status IN ('pending', 'processing');
CREATE INDEX idx_unenriched_products ON catalog.product (id) WHERE enrichment_data IS NULL;

-- Foreign Key Indexes (Missing!)
CREATE INDEX idx_stock_size_id ON inventory.stock (size_id);
CREATE INDEX idx_brand_patterns_brand ON catalog.brand_patterns (brand_id);
CREATE INDEX idx_marketplace_data_platform ON analytics.marketplace_data (platform_id);
```

**Expected Impact**: 50-70% query time reduction on JOIN-heavy queries

---

## 📊 Long-Term Architecture (Months 2-3)

### 5. Table Partitioning for Time-Series Data

**Target Tables**:
- `pricing.price_history` (high-volume updates)
- `analytics.sales_forecasts`
- `logging.event_store`
- `sales.pricing_history`

**Implementation**:

```sql
-- Convert price_history to partitioned table
CREATE TABLE pricing.price_history_new (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL,
  inventory_item_id UUID,
  platform_id UUID NOT NULL,
  price NUMERIC(10,2) NOT NULL,
  price_type VARCHAR(50),
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create initial partitions (last 6 months + next 3 months)
CREATE TABLE pricing.price_history_2024_11
  PARTITION OF pricing.price_history_new
  FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');

CREATE TABLE pricing.price_history_2024_12
  PARTITION OF pricing.price_history_new
  FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- Auto-partition function
CREATE OR REPLACE FUNCTION create_monthly_partition(
  schema_name TEXT,
  table_name TEXT,
  start_date DATE
) RETURNS void AS $$
DECLARE
  partition_name TEXT;
  end_date DATE;
BEGIN
  partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
  end_date := start_date + INTERVAL '1 month';

  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %I.%I PARTITION OF %I.%I FOR VALUES FROM (%L) TO (%L)',
    schema_name, partition_name, schema_name, table_name, start_date, end_date
  );

  RAISE NOTICE 'Created partition: %.%', schema_name, partition_name;
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly partition creation (via cron or pg_cron)
SELECT cron.schedule('create-next-month-partitions', '0 0 1 * *', $$
  SELECT create_monthly_partition('pricing', 'price_history_new', date_trunc('month', now() + interval '2 months')::date);
$$);
```

**Performance Impact**: 100x faster queries on historical data

---

### 6. Normalization Optimization - Size Tables

**Current Problem**: 4 separate size tables causing confusion
- `catalog.sizes`
- `catalog.size_master`
- `catalog.size_conversion`
- `catalog.product_variant` (includes size info)

**Recommended Structure**:

```sql
-- Unified size system
CREATE TABLE catalog.size_unified (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID REFERENCES catalog.category(id),
  display_value VARCHAR(20) NOT NULL,
  standardized_value NUMERIC(4,1),
  region VARCHAR(10) NOT NULL,
  us_equivalent NUMERIC(4,1),
  eu_equivalent NUMERIC(4,1),
  uk_equivalent NUMERIC(4,1),
  created_at TIMESTAMP DEFAULT now()
);

-- Conversion view for backward compatibility
CREATE VIEW catalog.sizes AS
SELECT id, category_id, display_value as value, standardized_value, region
FROM catalog.size_unified;
```

---

### 7. Supplier Security Enhancement

**Current**: PCI-compliant but could be more secure

**Recommendation**: Implement token vault with audit trail

```sql
-- Enhanced token vault
CREATE TABLE supplier.payment_vault (
  id BIGSERIAL PRIMARY KEY,
  account_id UUID NOT NULL REFERENCES supplier.account(id) ON DELETE CASCADE,
  provider VARCHAR(50) NOT NULL,
  token_ref VARCHAR(255) NOT NULL UNIQUE,
  last4 VARCHAR(4),
  brand VARCHAR(20),
  expires_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  last_verified TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

-- Audit trail
CREATE TABLE supplier.token_audit (
  id BIGSERIAL PRIMARY KEY,
  token_id BIGINT REFERENCES supplier.payment_vault(id),
  action VARCHAR(50) NOT NULL,
  accessed_by VARCHAR(100) NOT NULL,
  ip_address INET,
  accessed_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Audit trigger
CREATE OR REPLACE FUNCTION audit_payment_access()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO supplier.token_audit (token_id, action, accessed_by, accessed_at)
  VALUES (NEW.id, TG_OP, current_user, now());
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payment_access
AFTER INSERT OR UPDATE ON supplier.payment_vault
FOR EACH ROW EXECUTE FUNCTION audit_payment_access();
```

---

### 8. Analytics Data Warehouse

**Problem**: Analytics queries hitting OLTP database

**Solution**: Dedicated analytics schema with materialized views

```sql
-- Create analytics warehouse
CREATE SCHEMA analytics_dw;

-- Fact table: Daily sales summary
CREATE MATERIALIZED VIEW analytics_dw.fact_daily_sales AS
SELECT
  DATE(o.sold_at) as sale_date,
  p.brand_id,
  p.category_id,
  pl.id as platform_id,
  COUNT(DISTINCT o.id) as total_orders,
  SUM(o.gross_sale) as gross_revenue,
  SUM(o.platform_fee + o.shipping_cost) as total_costs,
  SUM(o.net_profit) as net_profit,
  AVG(o.roi) as avg_roi
FROM sales.order o
JOIN inventory.stock s ON o.inventory_item_id = s.id
JOIN catalog.product p ON s.product_id = p.id
JOIN platform.marketplace pl ON o.platform_id = pl.id
WHERE o.status = 'completed'
GROUP BY 1, 2, 3, 4;

-- Index for fast aggregation queries
CREATE INDEX idx_daily_sales_date ON analytics_dw.fact_daily_sales (sale_date DESC);
CREATE INDEX idx_daily_sales_brand ON analytics_dw.fact_daily_sales (brand_id, sale_date);

-- Refresh schedule (daily at 2 AM)
SELECT cron.schedule('refresh-daily-sales', '0 2 * * *', $$
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_dw.fact_daily_sales;
$$);

-- Inventory health snapshot
CREATE MATERIALIZED VIEW analytics_dw.inventory_health AS
SELECT
  p.brand_id,
  p.category_id,
  COUNT(s.id) as total_units,
  SUM(CASE WHEN s.status = 'in_stock' THEN 1 ELSE 0 END) as available_units,
  SUM(CASE WHEN s.listed_stockx THEN 1 ELSE 0 END) as listed_stockx_count,
  AVG(EXTRACT(days FROM now() - s.purchase_date)) as avg_shelf_days,
  SUM(s.purchase_price) as total_inventory_value
FROM inventory.stock s
JOIN catalog.product p ON s.product_id = p.id
WHERE s.status != 'sold'
GROUP BY 1, 2;
```

---

## 🔄 Implementation Timeline

### Phase 1: Quick Wins (Week 1)
**Priority**: High | **Risk**: Low

- [ ] Deploy all critical indexes (JSONB, composite, partial)
- [ ] Add structured columns to JSONB tables
- [ ] Test performance improvements
- [ ] Document index maintenance procedures

**Expected Outcome**: 50-70% query performance improvement

---

### Phase 2: Consolidation (Weeks 2-4)
**Priority**: High | **Risk**: Medium

- [ ] Consolidate inventory tables
  - [ ] Add new columns to `inventory.stock`
  - [ ] Backfill data from fragmented tables
  - [ ] Update application code
  - [ ] Verify data integrity
  - [ ] Drop old tables

- [ ] Deprecate `financial.transaction`
  - [ ] Verify all data migrated to `sales.order`
  - [ ] Update reporting queries
  - [ ] Mark table as deprecated

**Expected Outcome**: Simplified schema, easier maintenance

---

### Phase 3: Advanced Optimizations (Months 2-3)
**Priority**: Medium | **Risk**: Medium-High

- [ ] Implement table partitioning
  - [ ] `pricing.price_history`
  - [ ] `logging.event_store`
  - [ ] `analytics.sales_forecasts`

- [ ] Build analytics data warehouse
  - [ ] Create materialized views
  - [ ] Set up refresh schedules
  - [ ] Migrate reporting queries

- [ ] Optimize normalization
  - [ ] Consolidate size tables
  - [ ] Update brand structure

**Expected Outcome**: 100x faster time-series queries, real-time analytics

---

## 📈 Success Metrics

### Performance KPIs
- **Query Response Time**: Target <100ms for 95th percentile
- **JSONB Query Speed**: 10x improvement (baseline vs indexed)
- **Time-Series Queries**: 100x improvement with partitioning
- **Storage Usage**: 30-40% reduction

### Monitoring Queries

```sql
-- Query performance monitoring
SELECT
  query,
  calls,
  total_exec_time / calls as avg_time_ms,
  stddev_exec_time
FROM pg_stat_statements
WHERE query LIKE '%inventory.stock%'
ORDER BY total_exec_time DESC
LIMIT 20;

-- Index usage stats
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname IN ('inventory', 'sales', 'pricing')
ORDER BY idx_scan DESC;

-- Table bloat check
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🚀 Next Steps

1. **Review this plan** with development team
2. **Set up monitoring** (pg_stat_statements, query logging)
3. **Create test environment** for migration testing
4. **Start Phase 1** (indexes) this week
5. **Schedule Phase 2** for weeks 2-4
6. **Plan Phase 3** for Q1 2025

---

## 📚 References

- Gibson AI Analysis: 2025-11-29
- PostgreSQL Partitioning Docs: https://www.postgresql.org/docs/current/ddl-partitioning.html
- JSONB Indexing Best Practices: https://www.postgresql.org/docs/current/datatype-json.html
- Database Consolidation Pattern: DDD Aggregate Design
