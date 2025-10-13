# Multi-Source Pricing Architecture Refactoring

**Status**: 🚧 In Progress
**Version**: v2.3.0
**Created**: 2025-10-12
**Purpose**: Eliminate data redundancy and create unified pricing architecture

---

## 📋 Executive Summary

### Problem Statement

**Current State (v2.2.9):**
- Product data duplicated across multiple tables (`awin_products`, `products.products`)
- Pricing data fragmented across sources (StockX, Awin, future: eBay, GOAT)
- Awin merchants not linked to existing `core.suppliers` infrastructure
- Difficult to compare prices across multiple sources
- Redundant storage of brand, name, SKU, EAN for each source

**Challenges:**
```
integration.awin_products:
  - product_name: "Jordan 3 Retro OG Rare Air (TD)"
  - brand_name: "Jordan"
  - ean: "0197862948967"
  - retail_price_cents: 5000
  - merchant_name: "size?Official DE"

products.products:
  - name: "Jordan 3 Retro OG Rare Air (TD)"  ❌ DUPLICATE
  - brand: "Jordan"                           ❌ DUPLICATE
  - ean: "0197862948967"                      ❌ DUPLICATE
  - lowest_ask: 19500 (StockX resale price)
```

### Solution Architecture

**Target State (v2.3.0):**
- Single source of truth for product data (`products.products`)
- Unified price sources table (`integration.price_sources`)
- Support for multiple price providers (StockX, Awin, eBay, GOAT, etc.)
- Automatic price history tracking
- Linked to existing supplier infrastructure

**Benefits:**
- ✅ **-70% Storage**: Eliminate product data duplication
- ✅ **Multi-Source**: Unified interface for all price providers
- ✅ **Scalable**: Add new sources without schema changes
- ✅ **Consistent**: Single point of truth for product master data
- ✅ **Integrated**: Full supplier history and analytics support

---

## 🏗️ Architecture Design

### New Database Schema

```sql
-- ============================================================================
-- MASTER PRODUCT DATA (Single Source of Truth)
-- ============================================================================
products.products
├── id                 UUID PRIMARY KEY
├── sku                VARCHAR(100)
├── brand_id           UUID → brands(id)
├── name               VARCHAR(500)
├── ean                VARCHAR(20)          -- Universal product identifier
├── style_code         VARCHAR(200)
├── category           VARCHAR(100)
├── description        TEXT
├── images             JSONB
└── enrichment_data    JSONB

-- ============================================================================
-- MULTI-SOURCE PRICING (Replaces awin_products pricing data)
-- ============================================================================
integration.price_sources
├── id                    UUID PRIMARY KEY
├── product_id            UUID → products.products(id)
├── source_type           ENUM('stockx', 'awin', 'ebay', 'goat', 'klekt')
├── source_product_id     VARCHAR(100)     -- External ID from source
├── price_type            ENUM('resale', 'retail', 'auction')
├── price_cents           INTEGER
├── currency              VARCHAR(3) DEFAULT 'EUR'
├── stock_quantity        INTEGER
├── in_stock              BOOLEAN
├── condition             VARCHAR(50)       -- 'new', 'used', 'deadstock'
├── source_url            TEXT
├── affiliate_link        TEXT             -- For affiliate sources (Awin)
├── supplier_id           UUID → suppliers(id)  -- Links to existing suppliers
├── last_updated          TIMESTAMP
├── created_at            TIMESTAMP
└── UNIQUE(product_id, source_type, source_product_id)

-- ============================================================================
-- PRICE HISTORY (Automatic tracking)
-- ============================================================================
integration.price_history
├── id                    UUID PRIMARY KEY
├── price_source_id       UUID → price_sources(id)
├── price_cents           INTEGER
├── in_stock              BOOLEAN
├── recorded_at           TIMESTAMP
└── INDEX(price_source_id, recorded_at)
```

### Source Type Mapping

| Source Type | Description | Price Type | Example |
|-------------|-------------|------------|---------|
| `stockx` | StockX marketplace | `resale` | Lowest ask, highest bid |
| `awin` | Awin affiliate network | `retail` | Retail price from size?Official, JD Sports |
| `ebay` | eBay marketplace | `auction` / `retail` | Buy-it-now, auction prices |
| `goat` | GOAT marketplace | `resale` | Instant ship prices |
| `klekt` | Klekt marketplace | `resale` | European resale prices |

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                     │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
    ┌────▼──────┐    ┌─────▼──────┐    ┌─────▼──────┐
    │  StockX   │    │    Awin    │    │    eBay    │
    │    API    │    │    Feed    │    │    API     │
    └────┬──────┘    └─────┬──────┘    └─────┬──────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              PRODUCT ENRICHMENT SERVICE                     │
│  1. Extract/Create product in products.products             │
│  2. Store price in integration.price_sources                │
│  3. Link to supplier if applicable                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  UNIFIED DATA MODEL                         │
│                                                             │
│  products.products          integration.price_sources      │
│  ├─ Master product data     ├─ StockX resale              │
│  ├─ Single source of truth  ├─ Awin retail                │
│  └─ No redundancy           ├─ eBay auction                │
│                             └─ Future sources              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    ANALYTICS LAYER                          │
│  - Profit opportunity detection                             │
│  - Price comparison across sources                          │
│  - Historical price trends                                  │
│  - Supplier performance analytics                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Migration Strategy

### Phase 1: Create New Schema (No Data Loss)

**Goal**: Add new tables alongside existing structure

1. Create `integration.price_sources` table
2. Create `integration.price_history` table
3. Add indexes for performance
4. Keep `integration.awin_products` table intact (for rollback)

**Migration File**: `2025_10_12_1400_create_price_sources_tables.py`

### Phase 2: Migrate Existing Data

**Goal**: Populate new tables from existing data

**Awin Products Migration:**
```sql
-- Step 1: Ensure all Awin products exist in products.products
INSERT INTO products.products (sku, name, brand_id, ean, style_code, created_at)
SELECT
  COALESCE(ap.mpn, ap.awin_product_id) as sku,
  ap.product_name,
  b.id as brand_id,
  ap.ean,
  ap.product_model,
  NOW()
FROM integration.awin_products ap
LEFT JOIN core.brands b ON LOWER(b.name) = LOWER(ap.brand_name)
WHERE ap.matched_product_id IS NULL  -- Only create if not already matched
ON CONFLICT (ean) DO UPDATE
  SET updated_at = NOW();

-- Step 2: Migrate prices to price_sources
INSERT INTO integration.price_sources (
  product_id,
  source_type,
  source_product_id,
  price_type,
  price_cents,
  currency,
  stock_quantity,
  in_stock,
  affiliate_link,
  supplier_id,
  last_updated,
  created_at
)
SELECT
  COALESCE(ap.matched_product_id, p.id) as product_id,
  'awin' as source_type,
  ap.awin_product_id as source_product_id,
  'retail' as price_type,
  ap.retail_price_cents,
  ap.currency,
  ap.stock_quantity,
  ap.in_stock,
  ap.affiliate_link,
  s.id as supplier_id,  -- Link to suppliers table
  ap.last_updated,
  ap.created_at
FROM integration.awin_products ap
LEFT JOIN products.products p ON p.ean = ap.ean
LEFT JOIN core.suppliers s ON s.name = ap.merchant_name
WHERE ap.retail_price_cents IS NOT NULL;
```

**StockX Prices Migration:**
```sql
-- Migrate StockX lowest_ask to price_sources
INSERT INTO integration.price_sources (
  product_id,
  source_type,
  source_product_id,
  price_type,
  price_cents,
  currency,
  in_stock,
  last_updated,
  created_at
)
SELECT
  p.id as product_id,
  'stockx' as source_type,
  p.stockx_product_id as source_product_id,
  'resale' as price_type,
  p.lowest_ask as price_cents,
  'EUR' as currency,
  true as in_stock,  -- StockX always has "virtual" stock
  p.last_enriched_at,
  p.created_at
FROM products.products p
WHERE p.lowest_ask IS NOT NULL
  AND p.stockx_product_id IS NOT NULL;
```

### Phase 3: Update Services

**Affected Services:**
1. `AwinFeedImportService` → Use `PriceSourceService`
2. `StockXCatalogService` → Store prices in `price_sources`
3. `AwinStockXEnrichmentService` → Update to new model
4. New: `PriceComparisonService` for multi-source analysis

### Phase 4: Update API Endpoints

**Modified Endpoints:**
```python
# BEFORE (v2.2.9)
GET /awin/profit-opportunities
  → Joins awin_products with products.products

# AFTER (v2.3.0)
GET /integration/profit-opportunities
  → Joins price_sources (retail) with price_sources (resale)
  → Source-agnostic: Works for any retail vs resale comparison
```

### Phase 5: Cleanup (After Verification)

**Deprecate old tables:**
- Rename `integration.awin_products` → `integration.awin_products_legacy`
- Keep for 30 days as backup
- Drop after verification

---

## 🚀 Fresh Start Implementation

### Complete Database Reset Procedure

**Step 1: Backup Existing Data**
```bash
# Backup current database
python scripts/database/create_backup.py

# Export critical data
pg_dump -U postgres -d soleflip \
  -t integration.awin_products \
  -t products.products \
  > backups/pre_refactor_data.sql
```

**Step 2: Reset Database to Base**
```bash
# Drop all tables
alembic downgrade base

# Verify clean state
psql -U postgres -d soleflip -c "\dt *.*"
```

**Step 3: Apply New Migrations**
```bash
# Run all migrations INCLUDING new price_sources
alembic upgrade head

# Verify new schema
psql -U postgres -d soleflip -c "
  SELECT table_schema, table_name
  FROM information_schema.tables
  WHERE table_schema IN ('integration', 'products', 'core')
  ORDER BY table_schema, table_name;
"
```

**Step 4: Fresh Data Import**

**4a. Import Suppliers First**
```python
# scripts/fresh_import/01_import_suppliers.py
from domains.suppliers.services.supplier_service import SupplierService

suppliers = [
    {
        "name": "size?Official DE",
        "country": "DE",
        "website_url": "https://www.sizeer.de/",
        "supplier_type": "affiliate_retail",
        "founded_year": 2000,
        "instagram_handle": "@sizeofficial"
    },
    # Add more suppliers...
]

for supplier_data in suppliers:
    await supplier_service.create_supplier(supplier_data)
```

**4b. Import Awin Feed (New Architecture)**
```python
# scripts/fresh_import/02_import_awin_feed.py
from domains.integration.services.awin_import_service_v2 import AwinImportServiceV2

service = AwinImportServiceV2(session)

# This will now:
# 1. Create/update products in products.products
# 2. Store prices in integration.price_sources
# 3. Link to supplier_id automatically
await service.import_feed(
    feed_url="https://...",
    merchant_id=12345,
    supplier_name="size?Official DE"
)
```

**4c. Enrich with StockX**
```python
# scripts/fresh_import/03_enrich_stockx.py
from domains.integration.services.stockx_enrichment_service_v2 import StockXEnrichmentServiceV2

service = StockXEnrichmentServiceV2(session)

# This will now:
# 1. Match products by EAN
# 2. Store StockX prices in integration.price_sources
# 3. Store product details in products.products.enrichment_data
await service.enrich_all_products(rate_limit=60)
```

---

## 📈 Benefits Analysis

### Storage Reduction

**Before (v2.2.9):**
```
integration.awin_products (1,150 products):
  - product_name: 500 bytes × 1,150 = 575 KB
  - brand_name: 200 bytes × 1,150 = 230 KB
  - description: 1,000 bytes × 1,150 = 1,150 KB
  - Total redundancy: ~2 MB per 1,000 products
```

**After (v2.3.0):**
```
products.products: 1× product data
integration.price_sources: Only price + metadata
  → 70% storage reduction
  → Faster queries (less data to scan)
```

### Query Performance

**Before:**
```sql
-- Complex JOIN with duplicate data
SELECT ap.*, p.*
FROM integration.awin_products ap
JOIN products.products p ON ap.ean = p.ean
WHERE ap.in_stock = true;
```

**After:**
```sql
-- Clean JOIN on indexed columns
SELECT p.*, ps_retail.price_cents as retail, ps_resale.price_cents as resale
FROM products.products p
LEFT JOIN integration.price_sources ps_retail
  ON p.id = ps_retail.product_id AND ps_retail.source_type = 'awin'
LEFT JOIN integration.price_sources ps_resale
  ON p.id = ps_resale.product_id AND ps_resale.source_type = 'stockx';
```

### Scalability

**Adding New Source (Before):**
```
1. Create new table: ebay_products
2. Duplicate all product fields
3. Create new import service
4. Create new API endpoints
5. Update profit detection logic
6. 2-3 days development time
```

**Adding New Source (After):**
```
1. Add 'ebay' to source_type ENUM
2. Use existing PriceSourceService
3. Profit detection works automatically
4. 2-3 hours development time
```

---

## 🔍 Data Integrity Checks

### Pre-Migration Validation

```sql
-- Check for products without EAN
SELECT COUNT(*) FROM integration.awin_products WHERE ean IS NULL;
-- Expected: <5% of products

-- Check for duplicate EANs in products
SELECT ean, COUNT(*)
FROM products.products
WHERE ean IS NOT NULL
GROUP BY ean
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Verify supplier exists
SELECT DISTINCT merchant_name
FROM integration.awin_products
WHERE merchant_name NOT IN (SELECT name FROM core.suppliers);
-- Should return merchants that need to be added as suppliers
```

### Post-Migration Validation

```sql
-- Verify all Awin products migrated
SELECT
  (SELECT COUNT(*) FROM integration.awin_products WHERE retail_price_cents IS NOT NULL) as old_count,
  (SELECT COUNT(*) FROM integration.price_sources WHERE source_type = 'awin') as new_count;
-- old_count should equal new_count

-- Verify price accuracy
SELECT
  ap.awin_product_id,
  ap.retail_price_cents as old_price,
  ps.price_cents as new_price
FROM integration.awin_products ap
JOIN integration.price_sources ps ON ps.source_product_id = ap.awin_product_id
WHERE ap.retail_price_cents != ps.price_cents;
-- Expected: 0 rows (prices should match exactly)

-- Verify product linkage
SELECT COUNT(*)
FROM integration.price_sources ps
WHERE ps.product_id IS NULL;
-- Expected: 0 (all prices should link to a product)
```

---

## 🎯 Success Metrics

### Technical Metrics
- ✅ **Storage Reduction**: >60% reduction in product data storage
- ✅ **Query Performance**: <100ms for profit opportunity queries
- ✅ **Data Integrity**: 100% of products correctly linked
- ✅ **Zero Data Loss**: All historical data preserved

### Business Metrics
- ✅ **Time to Add Source**: <4 hours (from 2-3 days)
- ✅ **Price Comparison**: Real-time across all sources
- ✅ **Scalability**: Support for 10+ price sources
- ✅ **Maintainability**: Single service for all sources

---

## 📝 Migration Timeline

| Phase | Duration | Status | Description |
|-------|----------|--------|-------------|
| 1. Documentation | 1 hour | ✅ Done | Architecture docs, migration plan |
| 2. Schema Creation | 30 min | 🚧 In Progress | Create price_sources tables |
| 3. Service Updates | 2 hours | ⏳ Pending | Update import/enrichment services |
| 4. Data Migration Scripts | 1 hour | ⏳ Pending | Scripts to migrate existing data |
| 5. API Updates | 1 hour | ⏳ Pending | Update endpoints for new model |
| 6. Testing | 2 hours | ⏳ Pending | Verify all functionality |
| 7. Fresh Start | 30 min | ⏳ Pending | Reset + reimport with new structure |
| **Total** | **~8 hours** | | |

---

## 🔄 Rollback Plan

If issues arise during migration:

```bash
# Restore backup
psql -U postgres -d soleflip < backups/pre_refactor_data.sql

# Downgrade migration
alembic downgrade <previous_revision>

# Verify data integrity
python scripts/database/check_database_integrity.py
```

**Data Safety:**
- ✅ Original `awin_products` table kept as `_legacy` for 30 days
- ✅ Full database backup before migration
- ✅ Row-by-row validation during migration
- ✅ Automated integrity checks

---

## 📚 References

- **Current Architecture**: `context/architecture/current-data-model.md`
- **Price Sources API**: `docs/api/price-sources-endpoints.md` (to be created)
- **Migration Scripts**: `migrations/versions/2025_10_12_*`
- **Fresh Start Guide**: `context/setup/fresh-database-setup.md` (to be created)

---

**Status**: 🚧 Ready for implementation
**Next Steps**: Create database migration, update services, test fresh import
