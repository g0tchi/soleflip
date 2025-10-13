# Fresh Database Setup - Final Guide (v2.3.0)

**Status:** ✅ Production Ready
**Last Updated:** 2025-10-13
**Database Version:** consolidated_v1

---

## Quick Start (5 Minutes)

```bash
# 1. Create fresh database
python scripts/setup/create_fresh_database.py

# 2. Run consolidated migration
python -m alembic upgrade consolidated_v1

# 3. Generate size master data
python scripts/population/1_generate_sizes.py

# Done! Database is ready with 38 tables, 153 sizes, and seed data
```

---

## Complete Setup Guide

### Prerequisites

1. **PostgreSQL 14+** installed and running
2. **Python 3.11+** with dependencies installed
3. **Environment variables** configured in `.env`:
   ```bash
   DATABASE_URL=postgresql+asyncpg://user:pass@host:port/soleflip
   FIELD_ENCRYPTION_KEY=<your_fernet_key>
   ```

### Step 1: Create Fresh Database

**Option A: Using Python script**
```python
import asyncio
import asyncpg

async def create_database():
    # Connect to postgres database
    conn = await asyncpg.connect('postgresql://user:pass@host:port/postgres')

    # Terminate connections and drop existing database
    await conn.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = 'soleflip' AND pid <> pg_backend_pid()"
    )
    await conn.execute('DROP DATABASE IF EXISTS soleflip')

    # Create fresh database
    await conn.execute('CREATE DATABASE soleflip')
    print('Database soleflip created successfully')

    await conn.close()

asyncio.run(create_database())
```

**Option B: Using psql**
```bash
psql -h host -p port -U user -c "DROP DATABASE IF EXISTS soleflip"
psql -h host -p port -U user -c "CREATE DATABASE soleflip"
```

### Step 2: Run Consolidated Migration

**IMPORTANT:** Use `consolidated_v1` explicitly to avoid multiple head issues!

```bash
# Check current migration heads
python -m alembic heads

# Output should show:
# b2c8f3a1d9e4 (head) - old incremental migrations
# consolidated_v1 (head) - new consolidated migration

# Run ONLY the consolidated migration
python -m alembic upgrade consolidated_v1
```

**Expected Output:**
```
Creating schemas...
Creating enums...
Creating tables...
Tables created successfully!
Creating indexes...
Indexes created successfully!
Creating views...
Views created successfully!
Creating triggers and functions...
Triggers and functions created successfully!
Creating constraints...
Constraints created successfully!
Inserting seed data...
Seed data inserted successfully!
Adding table and column comments...
Comments added successfully!

================================================================================
CONSOLIDATED MIGRATION COMPLETED SUCCESSFULLY!
================================================================================

Database is now production-ready with:
  • 9 schemas (core, products, integration, transactions, pricing, analytics, auth, platforms, system)
  • 38 tables with complete relationships
  • 6 ENUMs with schema prefixes
  • 161 performance-optimized indexes
  • 4 views (2 analytics + 2 integration)
  • 3 triggers with automatic price tracking
  • Complete data validation constraints
  • Seed data (admin user, platforms, categories, brands)

All recommendations from Senior Database Architect review included!
================================================================================
```

**Migration Time:** 5-10 seconds

### Step 3: Generate Size Master Data

```bash
python scripts/population/1_generate_sizes.py
```

**What This Does:**
- Generates 153 size entries across all regions (US, UK, EU, CM)
- EU-based standardization for cross-region matching
- Example: US 9 = UK 8.5 = EU 42 (all have standardized_value = 42.0)

**Expected Output:**
```
================================================================================
SIZE MASTER DATA GENERATION - EU STANDARDIZATION
================================================================================

Generating size data with EU standardization...
  - US Men's sizes (3.5 - 18)...
  - US Women's sizes (5 - 15)...
  - US Youth sizes (1 - 7)...
  - UK sizes (3 - 16)...
  - EU sizes (35 - 52)...
  - CM sizes (22 - 35)...

Generated 153 size entries
Inserted 153 size records

=== VALIDATION RESULTS ===

Sizes by Region:
  CM :   27 sizes (EU range: 33.0 - 52.5)
  EU :   35 sizes (EU range: 35.0 - 52.0)
  UK :   27 sizes (EU range: 36.5 - 49.5)
  US :   64 sizes (EU range: 33.5 - 51.0)

Total sizes: 153

All sizes have standardized_value (EU-based)
No duplicate sizes found

Sample Cross-Region Matching (same standardized_value):
  US 9 (EU 42.0) matches:
    - CM 28.0
    - EU 42
    - UK 8.5
    - US 11.5W
    - US 9

================================================================================
SIZE GENERATION COMPLETED SUCCESSFULLY
================================================================================
```

---

## Verification

### Verify Database Structure

```python
import asyncio
import asyncpg

async def verify():
    conn = await asyncpg.connect('postgresql://user:pass@host:port/soleflip')

    # Check alembic version
    version = await conn.fetchval('SELECT version_num FROM alembic_version')
    print(f'Alembic Version: {version}')  # Should be: consolidated_v1

    # Count schemas
    schemas = await conn.fetch('''
        SELECT nspname FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        AND nspname NOT LIKE 'pg_%'
    ''')
    print(f'Schemas: {len(schemas)}')  # Should be: 10

    # Count tables
    tables = await conn.fetchval('''
        SELECT COUNT(*) FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    ''')
    print(f'Tables: {tables}')  # Should be: 38

    # Check seed data
    users = await conn.fetchval('SELECT COUNT(*) FROM auth.users')
    platforms = await conn.fetchval('SELECT COUNT(*) FROM core.platforms')
    brands = await conn.fetchval('SELECT COUNT(*) FROM core.brands')
    sizes = await conn.fetchval('SELECT COUNT(*) FROM products.sizes')

    print(f'\nSeed Data:')
    print(f'  Users: {users}')  # Should be: 1
    print(f'  Platforms: {platforms}')  # Should be: 8
    print(f'  Brands: {brands}')  # Should be: 10
    print(f'  Sizes: {sizes}')  # Should be: 153

    await conn.close()

asyncio.run(verify())
```

**Expected Output:**
```
Alembic Version: consolidated_v1
Schemas: 10
Tables: 38

Seed Data:
  Users: 1
  Platforms: 8
  Brands: 10
  Sizes: 153
```

---

## Critical Issue: Multiple Migration Heads

### The Problem

Alembic has **2 migration heads**:
1. `b2c8f3a1d9e4` - Old incremental migrations (26+ files)
2. `consolidated_v1` - New consolidated migration (1 file)

If you run `alembic upgrade head` without specifying which head, **BOTH migrations will run** and create duplicate tables!

### The Solution

**ALWAYS specify `consolidated_v1` explicitly:**

```bash
# ✅ CORRECT
python -m alembic upgrade consolidated_v1

# ❌ WRONG - Will run BOTH migration chains!
python -m alembic upgrade head
```

### Why This Happens

The old incremental migrations (`2025_08_14_*.py` through `2025_10_12_*.py`) form one migration chain ending at `b2c8f3a1d9e4`.

The new consolidated migration (`2025_10_13_0000_consolidated_fresh_start.py`) starts from scratch and creates everything fresh.

Both have `Revises: None` (no parent), making them both "heads" in Alembic's terminology.

### Future Considerations

For existing databases that already ran the old migrations, you should:
1. Continue using incremental migrations (`alembic upgrade b2c8f3a1d9e4`)
2. Do NOT run consolidated migration on existing databases

For fresh databases (new installations):
1. Use consolidated migration ONLY (`alembic upgrade consolidated_v1`)
2. Ignore old incremental migrations

---

## Database Schema Overview

### 10 Schemas (Domain-Driven Design)

1. **core** - Master data (brands, categories, platforms, suppliers)
2. **products** - Product catalog, inventory, **sizes**
3. **integration** - External data (StockX, AWIN, price sources)
4. **transactions** - Multi-platform orders and transactions
5. **pricing** - Smart pricing rules and brand multipliers
6. **analytics** - Forecasting, KPIs, market analysis
7. **auth** - User authentication and authorization
8. **platforms** - Platform-specific data (StockX orders, listings)
9. **system** - System configuration and logging
10. **public** - Alembic version table only

### 38 Tables Created

**Core Schema (9 tables):**
- brands, brand_patterns, categories, platforms
- suppliers, supplier_accounts, supplier_history, supplier_performance
- account_purchase_history

**Products Schema (3 tables):**
- **sizes** (moved from public schema per architect recommendation!)
- products (with StockX enrichment fields)
- inventory (with business intelligence fields)

**Integration Schema (8 tables):**
- **price_sources** (unified price architecture - eliminates 70% redundancy!)
- price_history, awin_products, awin_price_history, awin_enrichment_jobs
- market_prices (legacy), import_batches, import_records

**Transactions Schema (2 tables):**
- orders (multi-platform support: StockX, eBay, GOAT, etc.)
- transactions

**Pricing Schema (4 tables):**
- brand_multipliers, price_rules
- market_prices (legacy), price_history (legacy)

**Analytics Schema (5 tables):**
- demand_patterns, forecast_accuracy, marketplace_data
- pricing_kpis, sales_forecasts

**Auth Schema (1 table):**
- users (with role-based access: admin, user, readonly)

**Platforms Schema (3 tables):**
- stockx_orders, stockx_listings, pricing_history

**System Schema (2 tables):**
- config (key-value store for system settings)
- logs (system event logging)

### Seed Data Included

**Admin User:**
```
Username: admin
Email: admin@soleflip.com
Role: admin
Password: (encrypted with bcrypt)
```

**8 Platforms:**
StockX, eBay, Kleinanzeigen, Laced, GOAT, Alias, Restocks, Wethenew

**10 Brands:**
Nike, Adidas, Jordan, New Balance, Asics, Converse, Puma, Reebok, Vans, Yeezy

**1 Category:**
Sneakers

---

## Size Standardization Details

### What is standardized_value?

The `products.sizes.standardized_value` column uses **EU sizes as the universal standard** for cross-region matching.

### Conversion Formulas

```python
# US Men's → EU
us_mens_to_eu = lambda us: us + 33
# Example: US 9 → EU 42

# US Women's → EU
us_womens_to_eu = lambda us: us + 30.5
# Example: US W 7 → EU 37.5

# US Youth → EU
us_youth_to_eu = lambda us: us + 32.5
# Example: US Y 5 → EU 37.5

# UK → EU
uk_to_eu = lambda uk: uk + 33.5
# Example: UK 8 → EU 41.5

# CM → EU (approximate)
cm_to_eu = lambda cm: cm * 1.5
# Example: 28cm → EU 42

# EU → EU (direct mapping)
# Example: EU 42 → EU 42
```

### Cross-Region Matching Example

```sql
-- Find all sizes that match US 9
SELECT value, region, standardized_value
FROM products.sizes
WHERE standardized_value = (
    SELECT standardized_value
    FROM products.sizes
    WHERE region = 'US' AND value = '9'
);

-- Results:
-- US 9     (EU 42.0)
-- UK 8.5   (EU 42.0)
-- EU 42    (EU 42.0)
-- CM 28.0  (EU 42.0)
-- US 11.5W (EU 42.0)
```

This enables the `integration.profit_opportunities_v2` view to match products across different marketplaces even when they use different size systems!

---

## Troubleshooting

### Issue: "Multiple head revisions are present"

**Error:**
```
Multiple head revisions are present for given argument 'head';
please specify a specific target revision
```

**Solution:**
```bash
# Use consolidated_v1 explicitly
python -m alembic upgrade consolidated_v1
```

### Issue: "Table already exists"

**Cause:** You ran `alembic upgrade head` which ran BOTH migration chains.

**Solution:**
1. Drop database completely
2. Recreate fresh
3. Run `alembic upgrade consolidated_v1` (NOT `head`!)

### Issue: "sizes table not found" or "relation does not exist"

**Cause:** Old code may reference `public.sizes` instead of `products.sizes`.

**Solution:** Update code to reference `products.sizes`:
```python
# ❌ OLD
from shared.database.models import sizes

# ✅ NEW
from products.models import Size
```

### Issue: "standardized_value is null"

**Cause:** Sizes table exists but size generation script wasn't run.

**Solution:**
```bash
python scripts/population/1_generate_sizes.py
```

---

## Next Steps

After fresh database setup, proceed with data population:

1. **✅ Step 1: Size Master Data** (DONE - 153 sizes generated)

2. **Step 2: AWIN Product Feed Import**
   ```bash
   python scripts/population/2_import_awin_feed.py
   ```
   - Imports AWIN affiliate product feed
   - ~10,000 - 50,000 products with retail prices
   - EAN/GTIN data for StockX matching

3. **Step 3: StockX Catalog Sync**
   ```bash
   python scripts/population/3_enrich_with_stockx.py
   ```
   - Search StockX by EAN from AWIN products
   - Fetch market data (bids, asks, last sales)
   - Populate `integration.price_sources` with resale prices

4. **Step 4: Profit Opportunity Analysis**
   ```bash
   python scripts/population/4_validate_profit_opps.py
   ```
   - Test `integration.profit_opportunities_v2` view
   - Verify AWIN-StockX matching works
   - Identify profitable arbitrage opportunities

See `context/database/data-population-strategy.md` for complete details.

---

## Architecture Improvements (v2.3.0)

### From Senior Database Architect Review

**Grade:** B+ → A- (after fixes)

**Improvements Implemented:**

1. ✅ **Consolidated Migration** - Fresh database setup in 5 seconds
2. ✅ **sizes → products.sizes** - Proper schema organization
3. ✅ **Size Standardization** - EU-based cross-region matching
4. ✅ **Schema Prefixes on ENUMs** - Better organization
5. ✅ **Unified price_sources** - Eliminates 70% data redundancy
6. ✅ **161 Performance-Optimized Indexes** - Comprehensive coverage
7. ✅ **4 Analytical Views** - Profit opportunities, brand analysis
8. ✅ **3 Automatic Triggers** - Timestamp updates, price tracking
9. ✅ **Complete Seed Data** - Admin user, platforms, brands

**Remaining Work (Future):**

- **HIGH:** Migrate legacy price data to `integration.price_sources`
- **MEDIUM:** Implement partitioning for `price_history` and `system_logs`
- **MEDIUM:** Add audit trail (`created_by` / `updated_by` columns)
- **LOW:** Materialize expensive views for dashboard performance

---

## Related Documentation

- **`context/database/consolidated-migration-implementation.md`** - Complete migration documentation
- **`context/database/data-population-strategy.md`** - Data population guide
- **`context/architecture/senior-architect-complete-database-review.md`** - Full architecture review
- **`docs/database-schema-complete-analysis.md`** - Detailed schema analysis

---

**Document Status:** ✅ Complete and Tested
**Last Verified:** 2025-10-13
**Next Review:** After data population phase
