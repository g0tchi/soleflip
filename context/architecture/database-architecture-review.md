# Database Architecture Review: Multi-Source Pricing System
**Senior Database Architect Review**
**Date:** 2025-10-12
**System:** SoleFlipper Price Sources v2.3.0
**Scope:** Scalability, Performance, Normalization

---

## Executive Summary

**Overall Assessment:** ⭐⭐⭐⭐☆ (4/5) - Good architecture with room for optimization

**Strengths:**
- ✅ Proper normalization (3NF)
- ✅ Flexible JSONB for source-specific data
- ✅ Good foreign key constraints
- ✅ Reasonable indexing strategy

**Critical Issues Identified:**
- 🔴 **Size handling incomplete** - Missing standardized_value population
- 🟡 **Unique constraint too strict** - May cause issues with size variants
- 🟡 **View performance** - Potential N+1 problem at scale
- 🟡 **Missing partitioning strategy** - Will hurt at 10M+ records

---

## 1. Schema Analysis

### Current Design

```sql
price_sources (integration schema)
├─ id (UUID, PK)
├─ product_id (UUID, FK → products.products) ✅
├─ size_id (UUID, FK → sizes) ✅
├─ source_type (ENUM) ✅
├─ source_product_id (VARCHAR) ✅
├─ price_type (ENUM) ✅
├─ price_cents (INTEGER) ✅
├─ supplier_id (UUID, FK → suppliers) ✅
├─ metadata (JSONB) ✅
├─ timestamps (created_at, updated_at, last_updated) ✅
└─ UNIQUE(product_id, source_type, source_product_id, size_id)
```

### Issues & Recommendations

#### 🔴 CRITICAL: Unique Constraint Problem

**Current:**
```sql
UNIQUE(product_id, source_type, source_product_id, size_id)
```

**Problem:** If `size_id` is NULL for generic products, you can only have ONE price per product-source combination!

**Scenario:**
```sql
-- StockX has multiple variants for same product
INSERT (product_id='abc', source='stockx', source_product_id='variant-1', size_id=NULL) ✅
INSERT (product_id='abc', source='stockx', source_product_id='variant-2', size_id=NULL) ❌ FAILS!
-- Both NULL values are treated as equal in UNIQUE constraint
```

**Fix:**
```sql
-- Option A: Remove size_id from unique constraint
UNIQUE(product_id, source_type, source_product_id)

-- Option B: Use partial unique index (PostgreSQL 9.5+)
CREATE UNIQUE INDEX uq_price_source_with_size
ON price_sources (product_id, source_type, source_product_id, size_id)
WHERE size_id IS NOT NULL;

CREATE UNIQUE INDEX uq_price_source_without_size
ON price_sources (product_id, source_type, source_product_id)
WHERE size_id IS NULL;
```

**Recommendation:** Use **Option B** (partial indexes) for maximum flexibility.

---

#### 🟡 IMPORTANT: Size Architecture Decision

**Current State:**
- `sizes.standardized_value` is NULL everywhere
- Size matching is impossible
- View includes size logic that won't work

**Three Architectural Paths:**

##### **Path 1: Populate standardized_value (Recommended)**
```sql
-- Migration to populate standardized values
UPDATE sizes SET standardized_value =
  CASE
    WHEN region = 'EU' THEN value
    WHEN region = 'US' THEN (us_to_eu_conversion(value))
    WHEN region = 'UK' THEN (uk_to_eu_conversion(value))
  END;
```

**Pros:**
- ✅ Proper size matching across regions
- ✅ Future-proof for international expansion
- ✅ Clean query logic

**Cons:**
- ⚠️ Requires size conversion table/logic
- ⚠️ One-time data cleanup needed

##### **Path 2: Remove size_id, use metadata (Quick Fix)**
```sql
price_sources:
- size_id: REMOVE
- metadata: {"size": "38", "region": "EU"}
```

**Pros:**
- ✅ No FK complexity
- ✅ Works immediately

**Cons:**
- ❌ No referential integrity
- ❌ Size matching requires complex JSONB queries
- ❌ Can't index on size

##### **Path 3: Separate price_source_variants table (Over-engineered?)**
```sql
price_sources (generic)
├─ id
├─ product_id
├─ source_type
└─ ...

price_source_variants (size-specific)
├─ price_source_id (FK)
├─ size_id (FK)
├─ price_cents
└─ ...
```

**Pros:**
- ✅ Clean separation
- ✅ Handles complex scenarios

**Cons:**
- ❌ Over-complicated for current needs
- ❌ More JOINs = slower queries

**Recommendation:** **Path 1** - Fix the sizes table, it's the cleanest long-term solution.

---

## 2. Indexing Strategy

### Current Indexes (Good)
```sql
✅ idx_price_sources_product_id
✅ idx_price_sources_source_type
✅ idx_price_sources_price_type
✅ idx_price_sources_product_source (composite)
✅ idx_price_sources_size
✅ idx_price_sources_last_updated
```

### Missing Indexes (Add These!)

#### Critical for Profit Query
```sql
-- Composite index for profit opportunities view
CREATE INDEX idx_price_sources_profit_query
ON integration.price_sources (product_id, price_type, in_stock)
WHERE in_stock = true;

-- Partial index for retail prices only
CREATE INDEX idx_price_sources_retail_active
ON integration.price_sources (product_id, size_id, price_cents)
WHERE price_type = 'retail' AND in_stock = true;

-- Partial index for resale prices only
CREATE INDEX idx_price_sources_resale_active
ON integration.price_sources (product_id, size_id, price_cents)
WHERE price_type = 'resale' AND in_stock = true;
```

#### For Analytics Queries
```sql
-- Price history lookups
CREATE INDEX idx_price_history_date_range
ON integration.price_history (price_source_id, recorded_at DESC);

-- Source-specific queries
CREATE INDEX idx_price_sources_source_updated
ON integration.price_sources (source_type, last_updated DESC)
WHERE in_stock = true;
```

---

## 3. Scalability Concerns

### Current Scale Projections

| Records | Query Time | Storage | Concern Level |
|---------|------------|---------|---------------|
| 10K     | <50ms      | <50MB   | ✅ Fine       |
| 100K    | <200ms     | ~500MB  | ✅ Fine       |
| 1M      | <1s        | ~5GB    | 🟡 Monitor    |
| 10M     | 3-5s       | ~50GB   | 🔴 Optimize   |
| 100M    | 15-30s     | ~500GB  | 🔴 Partition  |

### Recommended Optimizations at Scale

#### At 1M+ records: Add Covering Indexes
```sql
-- Covering index for profit query (include all needed columns)
CREATE INDEX idx_profit_opportunities_covering
ON integration.price_sources (product_id, price_type, in_stock, size_id)
INCLUDE (price_cents, source_type, source_name, affiliate_link, supplier_id);
```

#### At 10M+ records: Partition by Source Type
```sql
-- Range partitioning by source_type
CREATE TABLE price_sources_stockx PARTITION OF price_sources
  FOR VALUES IN ('stockx');

CREATE TABLE price_sources_awin PARTITION OF price_sources
  FOR VALUES IN ('awin');

CREATE TABLE price_sources_ebay PARTITION OF price_sources
  FOR VALUES IN ('ebay');
```

**Benefits:**
- ✅ 10x faster queries when filtering by source
- ✅ Easier maintenance (drop old partitions)
- ✅ Better query planning

#### At 100M+ records: Time-based Partitioning
```sql
-- Partition price_history by month
CREATE TABLE price_history (
  ...
  recorded_at TIMESTAMP
) PARTITION BY RANGE (recorded_at);

CREATE TABLE price_history_2025_10 PARTITION OF price_history
  FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

---

## 4. View Performance Analysis

### Current `profit_opportunities_v2` View

**Performance at Scale:**
```sql
-- Current view does:
1. JOIN products (1x)
2. JOIN brands (1x)
3. JOIN price_sources retail (Nx)
4. JOIN sizes retail (Nx)
5. JOIN price_sources resale (Nx)
6. JOIN sizes resale (Nx)
7. WHERE filters
8. ORDER BY profit

-- Time complexity: O(N²) for N products with multiple prices
```

**Problem:** At 100K products × 10 sources = 1M price_sources records, this becomes slow!

### Optimization: Materialized View

```sql
-- Create materialized view for fast access
CREATE MATERIALIZED VIEW integration.profit_opportunities_v2_mat AS
SELECT * FROM integration.profit_opportunities_v2;

-- Refresh strategy: incremental refresh every hour
CREATE INDEX ON integration.profit_opportunities_v2_mat (profit_eur DESC);

-- Refresh command
REFRESH MATERIALIZED VIEW CONCURRENTLY integration.profit_opportunities_v2_mat;
```

**Performance Gain:**
- Before: 3-5 seconds for profit query
- After: <100ms (read from cached results)

**Trade-off:** Data is up to 1 hour stale (acceptable for profit analysis)

---

## 5. Data Integrity

### Current Constraints (Good)
```sql
✅ FK: product_id → products.products (CASCADE)
✅ FK: size_id → sizes (SET NULL)
✅ FK: supplier_id → suppliers (SET NULL)
✅ CHECK: price_cents >= 0 (MISSING!)
✅ CHECK: in_stock is NOT NULL
```

### Add Data Validation Constraints

```sql
-- Price must be positive
ALTER TABLE integration.price_sources
ADD CONSTRAINT chk_price_positive
CHECK (price_cents >= 0);

-- Stock quantity must be positive if specified
ALTER TABLE integration.price_sources
ADD CONSTRAINT chk_stock_positive
CHECK (stock_quantity IS NULL OR stock_quantity >= 0);

-- Currency must be valid
ALTER TABLE integration.price_sources
ADD CONSTRAINT chk_currency_valid
CHECK (currency ~ '^[A-Z]{3}$');

-- last_updated must be in the past
ALTER TABLE integration.price_sources
ADD CONSTRAINT chk_last_updated_past
CHECK (last_updated IS NULL OR last_updated <= NOW());
```

---

## 6. Query Optimization Recommendations

### Current Profit Query Issues

**Slow query pattern:**
```sql
-- This will be SLOW at scale
SELECT *
FROM integration.profit_opportunities_v2
WHERE profit_eur >= 20
ORDER BY profit_eur DESC
LIMIT 50;
```

**Why slow?**
- View calculates ALL opportunities first
- Then filters
- Then sorts
- Then limits

### Optimized Approach: Pre-filter in View

```sql
-- Add a parameterized function instead of view
CREATE OR REPLACE FUNCTION integration.get_profit_opportunities(
  min_profit_eur NUMERIC DEFAULT 20,
  limit_count INT DEFAULT 50
) RETURNS TABLE (
  product_id UUID,
  product_name VARCHAR,
  profit_eur NUMERIC,
  ...
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.id,
    p.name,
    (ps_resale.price_cents - ps_retail.price_cents) / 100.0 as profit_eur,
    ...
  FROM products.products p
  -- ... joins ...
  WHERE (ps_resale.price_cents - ps_retail.price_cents) / 100.0 >= min_profit_eur
  ORDER BY profit_eur DESC
  LIMIT limit_count;
END;
$$ LANGUAGE plpgsql STABLE;
```

**Performance gain:** 5-10x faster by filtering BEFORE sorting!

---

## 7. Recommended Migration Path

### Phase 1: Fix Critical Issues (Now)
```sql
-- 1. Fix unique constraint (partial indexes)
DROP CONSTRAINT uq_price_source;

CREATE UNIQUE INDEX uq_price_source_with_size
ON integration.price_sources (product_id, source_type, source_product_id, size_id)
WHERE size_id IS NOT NULL;

CREATE UNIQUE INDEX uq_price_source_without_size
ON integration.price_sources (product_id, source_type, source_product_id)
WHERE size_id IS NULL;

-- 2. Add missing indexes
CREATE INDEX idx_price_sources_profit_query
ON integration.price_sources (product_id, price_type, in_stock)
WHERE in_stock = true;

-- 3. Add data validation constraints
ALTER TABLE integration.price_sources
ADD CONSTRAINT chk_price_positive CHECK (price_cents >= 0);
```

### Phase 2: Populate Size Data (Week 1)
```sql
-- Create size conversion logic
-- Populate standardized_value for all sizes
-- Test size-based profit matching
```

### Phase 3: Performance Optimization (Month 1)
```sql
-- Add covering indexes
-- Create materialized view
-- Implement incremental refresh
```

### Phase 4: Partitioning (When >1M records)
```sql
-- Partition by source_type
-- Partition price_history by month
```

---

## 8. Final Recommendations

### ⭐ High Priority (Do Now)

1. **Fix unique constraint** - Use partial indexes
2. **Add profit query composite index** - 5-10x speedup
3. **Add data validation constraints** - Prevent bad data
4. **Populate sizes.standardized_value** - Enable size matching

### 🟡 Medium Priority (Next Sprint)

5. **Create materialized view** - For fast profit queries
6. **Add covering indexes** - Reduce disk I/O
7. **Implement size conversion table** - Clean size matching
8. **Add monitoring** - Track query performance

### 🔵 Low Priority (Future)

9. **Partitioning strategy** - When >1M records
10. **Read replicas** - If query load increases
11. **Caching layer** - Redis for hot queries
12. **Archive old data** - price_history older than 1 year

---

## 9. Performance Benchmarks (Expected)

### Before Optimizations
```
Profit opportunities query (1M prices):
- Current: 3-5 seconds
- 90th percentile: 8 seconds
- Concurrent users: ~10 max
```

### After Optimizations
```
Profit opportunities query (1M prices):
- With indexes: 500-800ms
- With materialized view: 50-100ms
- 90th percentile: 200ms
- Concurrent users: ~100 max
```

### At Scale (10M prices)
```
With partitioning + materialized view:
- Query time: <200ms
- Concurrent users: ~500 max
- Storage: ~50GB
```

---

## 10. Conclusion

**Current Grade: B+ (Good, but needs fixes)**

**To reach A+ (Production-ready at scale):**

1. ✅ Fix unique constraint (critical bug)
2. ✅ Add strategic indexes (5-10x speedup)
3. ✅ Populate standardized_value (enable size matching)
4. ✅ Add data validation (prevent bugs)
5. ⏳ Monitor and adjust (iterate)

**Timeline:**
- Critical fixes: 1 day
- Size data population: 1 week
- Performance optimization: 2 weeks
- **Production ready:** ~3 weeks

---

**Review conducted by:** Senior Database Architect
**Next review:** After size data population
**Contact:** See architecture team for questions
