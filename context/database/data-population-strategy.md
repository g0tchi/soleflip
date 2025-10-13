# Data Population Strategy - Fresh Database Setup

**Date:** 2025-10-13
**Status:** 🔄 Planning Phase
**Database Status:** ✅ Fresh & Empty (Migration `consolidated_v1` completed)
**Related Documents:**
- `context/database/consolidated-migration-implementation.md` - Migration documentation
- `context/architecture/senior-architect-complete-database-review.md` - Architecture review
- `docs/features/awin-stockx-money-printer.md` - AWIN-StockX integration

---

## Current Database Status

### Seed Data (✅ Populated by Migration)
- **Users:** 1 admin user
- **Platforms:** 8 sales platforms (StockX, eBay, Kleinanzeigen, Laced, GOAT, Alias, Restocks, Wethenew)
- **Brands:** 10 major brands (Nike, Adidas, Jordan, New Balance, Asics, Converse, Puma, Reebok, Vans, Yeezy)
- **Categories:** 1 category (Sneakers)

### Empty Tables (⚠️ Need Population)
- **sizes:** 0 records (critical for size matching)
- **products.products:** 0 records
- **integration.price_sources:** 0 records
- **integration.awin_products:** 0 records
- All other transactional tables: 0 records

---

## Data Population Strategy

### Phase 1: Size Master Data (🔴 CRITICAL - Blocks all size-dependent features)

**Priority:** HIGHEST
**Blocking:** Size matching, price comparison, AWIN-StockX enrichment
**Estimated Time:** 1-2 hours

#### Step 1.1: Create Size Standardization Service

**File:** `domains/products/services/size_standardization_service.py`

**Functionality:**
- Parse size strings from various formats
- Normalize to standardized format
- Support multiple regions (US, UK, EU, CM)
- Handle edge cases (half sizes, wide/narrow, kids sizes)

**Examples:**
```
Input          Region    Standardized
"US 10"        US        "10.0_US"
"10.5"         US        "10.5_US"
"UK 9"         UK        "9.0_UK"
"EU 44"        EU        "44.0_EU"
"27.5cm"       CM        "27.5_CM"
"10.5W"        US        "10.5_US_W" (women's)
"7Y"           US        "7.0_US_Y" (youth)
```

#### Step 1.2: Generate Standard Size Data

**Script:** `scripts/population/generate_sizes.py`

**Size Ranges to Generate:**
- **US Men's:** 3.5 - 18 (half sizes)
- **US Women's:** 5 - 15 (half sizes)
- **US Youth:** 1 - 7 (half sizes)
- **UK:** 3 - 16 (half sizes)
- **EU:** 35 - 52 (whole sizes)
- **CM:** 22 - 35 (half cm increments)

**Output:** ~500-600 size records with standardized_value populated

**SQL Template:**
```sql
INSERT INTO sizes (id, value, region, standardized_value)
VALUES
    (gen_random_uuid(), '10', 'US', '10.0_US'),
    (gen_random_uuid(), '10.5', 'US', '10.5_US'),
    (gen_random_uuid(), '11', 'US', '11.0_US'),
    -- ... etc
```

#### Step 1.3: Size Conversion Matrix

**Optional Enhancement:** Create size conversion table for cross-region matching

**Example Conversions:**
```
US 10 = UK 9 = EU 44 = 28cm
US 10.5 = UK 9.5 = EU 44.5 = 28.5cm
US 11 = UK 10 = EU 45 = 29cm
```

---

### Phase 2: AWIN Product Feed Import (🟡 HIGH - Core revenue driver)

**Priority:** HIGH
**Depends On:** Phase 1 (size data)
**Estimated Time:** 2-3 hours

#### Step 2.1: AWIN Feed Download & Extraction

**Existing Files:**
- `context/integrations/awin_feed_sample.csv` - Sample data (already exists)
- `context/integrations/awin_feed_sample.csv.gz` - Compressed feed (already exists)

**Script:** `scripts/population/import_awin_feed.py` (already exists?)

**Check existing scripts:**
```bash
ls scripts/ | grep awin
```

**Expected Output:** ~10,000 - 50,000 AWIN products with:
- Product name, brand, description
- Price (retail/sale)
- Merchant info
- Deep link for affiliate tracking
- EAN/GTIN (critical for StockX matching)

**Table:** `integration.awin_products`

#### Step 2.2: Initial AWIN Data Validation

**Checks:**
- EAN/GTIN format validation (13 digits)
- Price data completeness
- Brand recognition (match to core.brands)
- Sneaker filtering (exclude non-sneaker products)

**Quality Metrics:**
- Valid EAN rate: >80%
- Brand match rate: >60%
- Price completeness: >95%

---

### Phase 3: StockX Catalog Sync (🟡 HIGH - Required for enrichment)

**Priority:** HIGH
**Depends On:** Phase 1 (size data), Phase 2 (AWIN products for matching)
**Estimated Time:** 4-6 hours (API rate limits)

#### Step 3.1: StockX Authentication Setup

**Existing Guide:** `docs/guides/stockx_auth_setup.md`

**Requirements:**
- StockX API credentials (CLIENT_ID, CLIENT_SECRET)
- OAuth2 token management
- Rate limit handling (max requests per minute)

**Service:** `domains/integration/services/stockx_catalog_service.py` (already exists?)

#### Step 3.2: StockX Product Search by EAN

**API Endpoints:**
- `GET /catalog/search` - Search by GTIN/EAN
- `GET /catalog/products/{id}/variants` - Get all sizes/variants
- `GET /catalog/market-data/products/{id}` - Get market pricing

**Process:**
1. Take AWIN products with valid EANs
2. Search StockX catalog by EAN
3. Store product match results
4. Fetch variant data (all sizes)
5. Fetch market data (prices by size)

**Tables:**
- `products.products` - StockX product catalog
- `sizes` - Used for size matching
- `integration.awin_enrichment_jobs` - Track enrichment status

#### Step 3.3: StockX Market Data Import

**Data Points per Product/Size:**
- Current bid (highest buyer offer)
- Current ask (lowest seller offer)
- Last sale price
- Sales volume (last 72h)
- Price premium vs retail

**Table:** `integration.price_sources`
- `source_type`: 'stockxapi'
- `price_type`: 'resale'

**Expected Output:** 1,000 - 10,000 enriched products with StockX market data

---

### Phase 4: Profit Opportunity Analysis (🟢 MEDIUM - Business intelligence)

**Priority:** MEDIUM
**Depends On:** Phase 2 (AWIN data), Phase 3 (StockX data)
**Estimated Time:** 1 hour

#### Step 4.1: Validate Profit Opportunities View

**View:** `integration.profit_opportunities_v2`

**Test Query:**
```sql
SELECT
    product_name,
    awin_price,
    stockx_price,
    potential_profit,
    profit_margin_percent
FROM integration.profit_opportunities_v2
WHERE potential_profit > 20  -- €20+ profit
ORDER BY potential_profit DESC
LIMIT 50;
```

**Expected Results:** List of AWIN products with profitable StockX resale opportunities

#### Step 4.2: Create Analytics Dashboard Data

**View:** `analytics.brand_trend_analysis`

**Metrics:**
- Top brands by profit opportunity
- Average profit margin by brand
- Price trends over time
- Best performing size ranges

---

### Phase 5: Historical Data Import (🔵 LOW - Nice to have)

**Priority:** LOW
**Depends On:** Phase 1-4
**Estimated Time:** Variable (depends on data volume)

#### Step 5.1: Import Historical Orders (if available)

**Sources:**
- StockX order history CSV exports
- eBay order exports
- Manual transaction records

**Table:** `transactions.orders`

**Multi-Platform Support:** Already built-in (platform_id FK to core.platforms)

#### Step 5.2: Import Historical Inventory (if available)

**Sources:**
- Spreadsheet exports
- Previous database dumps
- Physical inventory counts

**Table:** `products.inventory`

---

## Data Population Scripts

### Script Organization

**Directory:** `scripts/population/`

```
scripts/population/
├── 1_generate_sizes.py           # Generate size master data
├── 2_import_awin_feed.py          # Import AWIN product feed
├── 3_enrich_with_stockx.py        # StockX catalog sync & enrichment
├── 4_validate_profit_opps.py     # Test profit opportunities view
├── 5_import_historical_orders.py  # Optional: historical data
└── README.md                      # Script usage guide
```

### Script Template Structure

```python
#!/usr/bin/env python3
"""
Script: [name]
Purpose: [description]
Dependencies: [list dependencies]
Estimated Runtime: [time]
"""

import asyncio
import asyncpg
from datetime import datetime

async def main():
    # 1. Connect to database
    conn = await asyncpg.connect('postgresql://...')

    # 2. Validate prerequisites
    # Check dependent data exists

    # 3. Load/generate data
    # Read from file, API, or generate

    # 4. Transform data
    # Clean, validate, normalize

    # 5. Insert into database
    # Use transactions for safety

    # 6. Verify results
    # Count records, run sanity checks

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Data Quality Checklist

### Phase 1: Size Data
- [ ] All size regions covered (US, UK, EU, CM)
- [ ] Half sizes included for US/UK
- [ ] standardized_value format consistent
- [ ] No duplicate size values per region
- [ ] Size conversion matrix tested

### Phase 2: AWIN Data
- [ ] AWIN feed extracted successfully
- [ ] EAN/GTIN validation >80% pass rate
- [ ] Brand matching >60% success rate
- [ ] Prices complete and valid
- [ ] Sneaker filtering applied

### Phase 3: StockX Data
- [ ] API authentication working
- [ ] Product search by EAN functional
- [ ] Variant data (sizes) imported
- [ ] Market pricing data complete
- [ ] Size matching between AWIN and StockX working

### Phase 4: Profit Analysis
- [ ] profit_opportunities_v2 view returns results
- [ ] Profit calculations accurate
- [ ] Profit margins reasonable (5-50%)
- [ ] Brand trends show realistic patterns

---

## Success Metrics

### Data Volume Targets

**Minimum Viable Dataset:**
- Sizes: 500+ records
- AWIN Products: 5,000+ records
- StockX Products: 1,000+ records
- Price Sources: 10,000+ records (StockX market data)
- Profit Opportunities: 100+ viable matches

**Production Dataset:**
- Sizes: 600+ records (all regions)
- AWIN Products: 50,000+ records
- StockX Products: 10,000+ enriched products
- Price Sources: 100,000+ price records
- Profit Opportunities: 1,000+ viable matches

### Data Quality Targets

- **Size standardization:** 100% (all sizes have standardized_value)
- **EAN validation:** >80% valid GTINs
- **Brand matching:** >70% successful matches
- **Price completeness:** >95% records have valid prices
- **Profit opportunity accuracy:** >90% margin calculations within ±5%

---

## Rollback Strategy

### If Data Population Fails

**Option 1: Partial Rollback (Transaction-based)**
```sql
-- Each script uses BEGIN/COMMIT, so failed script = no changes
-- Re-run individual script after fixing issue
```

**Option 2: Full Database Reset**
```bash
# Drop database
psql -h 192.168.2.45 -p 2665 -U metabaseuser -c "DROP DATABASE soleflip;"

# Recreate fresh
psql -h 192.168.2.45 -p 2665 -U metabaseuser -c "CREATE DATABASE soleflip;"

# Re-run migration
alembic upgrade head

# Start population from Phase 1
```

**Option 3: Schema-Specific Cleanup**
```sql
-- Clean specific tables without full reset
TRUNCATE integration.awin_products CASCADE;
TRUNCATE integration.price_sources CASCADE;
TRUNCATE products.products CASCADE;
-- etc...
```

---

## Monitoring & Validation

### Real-Time Monitoring During Population

**Metrics to Track:**
- Records inserted per minute
- Error rate (failed inserts)
- API rate limit usage (StockX)
- Database connection pool status
- Transaction rollback rate

**Monitoring Script:** `scripts/population/monitor_progress.py`

### Post-Population Validation

**Validation Queries:**
```sql
-- Size data completeness
SELECT
    region,
    COUNT(*) as total,
    COUNT(standardized_value) as with_standard,
    COUNT(*) - COUNT(standardized_value) as missing_standard
FROM sizes
GROUP BY region;

-- AWIN brand matching rate
SELECT
    COUNT(*) as total_products,
    COUNT(brand_id) as matched_brands,
    ROUND(COUNT(brand_id)::numeric / COUNT(*)::numeric * 100, 2) as match_rate_pct
FROM integration.awin_products;

-- StockX enrichment rate
SELECT
    COUNT(DISTINCT awin_product_id) as total_awin_products,
    COUNT(DISTINCT CASE WHEN stockx_product_id IS NOT NULL THEN awin_product_id END) as enriched,
    ROUND(COUNT(DISTINCT CASE WHEN stockx_product_id IS NOT NULL THEN awin_product_id END)::numeric /
          COUNT(DISTINCT awin_product_id)::numeric * 100, 2) as enrichment_rate_pct
FROM integration.awin_enrichment_jobs;

-- Profit opportunities count
SELECT COUNT(*) as viable_opportunities
FROM integration.profit_opportunities_v2
WHERE potential_profit > 10;
```

---

## Next Steps

### Immediate Actions (Today)

1. **Create Phase 1 Scripts:**
   - [ ] `scripts/population/1_generate_sizes.py` - Size master data generation
   - [ ] Test size standardization logic
   - [ ] Run script and validate results

2. **Verify Existing AWIN Scripts:**
   - [ ] Check if `scripts/import_awin_sample_feed.py` exists and works
   - [ ] Test with sample data (`context/integrations/awin_feed_sample.csv`)
   - [ ] Document any issues or improvements needed

3. **Review StockX Integration:**
   - [ ] Verify StockX API credentials configured
   - [ ] Test authentication flow
   - [ ] Document rate limits and batch sizes

### Short-Term Actions (This Week)

4. **Complete Phase 2-3:**
   - [ ] Import AWIN feed (5,000-50,000 products)
   - [ ] Enrich top 1,000 products with StockX data
   - [ ] Validate profit opportunities

5. **Create Monitoring Dashboard:**
   - [ ] SQL queries for data quality metrics
   - [ ] Metabase dashboards for business intelligence
   - [ ] Automated data validation checks

### Long-Term Actions (Next 2 Weeks)

6. **Production Data Pipeline:**
   - [ ] Scheduled AWIN feed refresh (daily)
   - [ ] Automated StockX price updates (hourly)
   - [ ] Real-time profit opportunity alerts
   - [ ] Historical data migration (if applicable)

---

## Appendix

### Related Files

**Documentation:**
- `context/database/consolidated-migration-implementation.md` - Migration details
- `docs/features/awin-stockx-money-printer.md` - Business logic documentation
- `docs/guides/stockx_auth_setup.md` - StockX API setup guide

**Existing Scripts (to verify):**
- `scripts/import_awin_sample_feed.py` - AWIN import
- `scripts/test_stockx_ean_search.py` - StockX search testing
- `scripts/find_stockx_awin_matches.py` - Matching logic
- `scripts/analyze_awin_profit_opportunities.py` - Profit analysis

**Integration Services:**
- `domains/integration/services/awin_feed_service.py` - AWIN processing
- `domains/integration/services/stockx_catalog_service.py` - StockX API
- `domains/integration/services/awin_stockx_enrichment_service.py` - Enrichment
- `domains/integration/services/unified_price_import_service.py` - Price imports

### Environment Variables Required

```bash
# StockX API (for Phase 3)
STOCKX_CLIENT_ID=your_client_id
STOCKX_CLIENT_SECRET=your_client_secret

# AWIN Affiliate (for Phase 2)
AWIN_PUBLISHER_ID=your_publisher_id  # Optional
AWIN_API_TOKEN=your_api_token        # Optional

# Database (already configured)
DATABASE_URL=postgresql+asyncpg://metabaseuser:metabasepass@192.168.2.45:2665/soleflip
```

---

**Document Status:** 🔄 Draft - Ready for Implementation
**Last Updated:** 2025-10-13
**Next Review:** After Phase 1 completion
