# Fresh Database Setup with Consolidated Migration

**Last Updated:** 2025-10-13
**Migration File:** `migrations/versions/2025_10_13_0000_consolidated_fresh_start.py`
**Revision ID:** `consolidated_v1`

---

## Overview

This guide shows how to set up a **fresh SoleFlip database** using the consolidated migration. This migration contains the complete production-ready schema with all optimizations from the Senior Database Architect review.

**⚠️ IMPORTANT:** This is for **NEW/FRESH** databases only. Existing databases should continue using incremental migrations.

---

## Prerequisites

- PostgreSQL 14+ installed and running
- Python 3.9+ with virtual environment activated
- All dependencies installed (`pip install -r requirements.txt`)
- `.env` file configured with database credentials

---

## Step-by-Step Setup

### 1. Create Empty Database

```bash
# Using psql
psql -U postgres -c "CREATE DATABASE soleflip;"

# Or using createdb
createdb -U postgres soleflip

# Verify database exists
psql -U postgres -l | grep soleflip
```

### 2. Configure Environment Variables

Ensure your `.env` file has the correct database URL:

```bash
# .env
DATABASE_URL=postgresql://postgres:password@localhost/soleflip

# Required for encryption
FIELD_ENCRYPTION_KEY=your_fernet_key_here

# Environment
ENVIRONMENT=development
```

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Run Consolidated Migration

```bash
# Option 1: Using Alembic directly
alembic upgrade consolidated_v1

# Option 2: Using make command (if available)
make db-setup
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> consolidated_v1, Consolidated Production-Ready Schema
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
✅ CONSOLIDATED MIGRATION COMPLETED SUCCESSFULLY!
================================================================================

Database is now production-ready with:
  • 9 schemas (core, products, integration, transactions, pricing, analytics, auth, platforms, system)
  • 35+ tables with complete relationships
  • 6 ENUMs with schema prefixes
  • 100+ performance-optimized indexes
  • 4 views (2 analytics + 2 integration)
  • 3 triggers with automatic price tracking
  • Complete data validation constraints
  • Seed data (admin user, platforms, categories, brands)

All recommendations from Senior Database Architect review included!
================================================================================
```

### 4. Verify Database Structure

```bash
# List all schemas
psql soleflip -c "\dn"

# Expected output:
# List of schemas
#   Name        |  Owner
# --------------+----------
#  analytics    | postgres
#  auth         | postgres
#  core         | postgres
#  integration  | postgres
#  platforms    | postgres
#  pricing      | postgres
#  products     | postgres
#  public       | postgres
#  system       | postgres
#  transactions | postgres

# Count tables per schema
psql soleflip -c "
  SELECT schemaname, COUNT(*) as table_count
  FROM pg_tables
  WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  GROUP BY schemaname
  ORDER BY schemaname;
"

# Expected output:
# schemaname   | table_count
# -------------+-------------
# analytics    | 5
# auth         | 1
# core         | 8
# integration  | 8
# platforms    | 3
# pricing      | 4
# products     | 2
# system       | 2
# transactions | 2
# public       | 1

# Verify seed data
psql soleflip -c "SELECT username, email, role FROM auth.users;"
psql soleflip -c "SELECT name, slug FROM core.platforms;"
psql soleflip -c "SELECT name, slug FROM core.brands;"
```

### 5. Test Database Connection

```bash
# Using Python
python -c "
from shared.database.connection import SessionLocal
db = SessionLocal()
result = db.execute('SELECT COUNT(*) FROM core.platforms')
print(f'Platforms count: {result.scalar()}')
db.close()
"

# Expected output: Platforms count: 8
```

### 6. Run Health Check

```bash
# Start development server
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# In another terminal, test health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "timestamp": "2025-10-13T12:00:00.000Z"
# }
```

---

## Verification Checklist

After running the migration, verify the following:

### ✅ Schemas Created
```sql
SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema';
```
**Expected:** 10 schemas (core, products, integration, transactions, pricing, analytics, auth, platforms, system, public)

### ✅ Tables Created
```sql
SELECT schemaname, COUNT(*) as table_count
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname;
```
**Expected:** 35+ tables across all schemas

### ✅ ENUMs Created
```sql
SELECT n.nspname as schema, t.typname as enum_name
FROM pg_type t
JOIN pg_namespace n ON t.typnamespace = n.oid
WHERE t.typtype = 'e'
ORDER BY n.nspname, t.typname;
```
**Expected:** 6 enums (source_type_enum, price_type_enum, condition_enum, inventory_status, sales_platform, user_role)

### ✅ Indexes Created
```sql
SELECT schemaname, COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname;
```
**Expected:** 100+ indexes

### ✅ Views Created
```sql
SELECT schemaname, viewname
FROM pg_views
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
```
**Expected:** 4 views (brand_trend_analysis, brand_loyalty_analysis, latest_prices, profit_opportunities_v2)

### ✅ Triggers Created
```sql
SELECT trigger_schema, trigger_name, event_object_table
FROM information_schema.triggers
WHERE trigger_schema NOT IN ('pg_catalog', 'information_schema');
```
**Expected:** 3 triggers (trigger_calculate_inventory_analytics, awin_price_change_trigger, price_change_trigger)

### ✅ Functions Created
```sql
SELECT n.nspname as schema, p.proname as function_name
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND p.prokind = 'f';
```
**Expected:** 3 functions (calculate_inventory_analytics, track_awin_price_changes, track_price_changes)

### ✅ Foreign Keys Created
```sql
SELECT COUNT(*) as fk_count
FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY'
  AND table_schema NOT IN ('pg_catalog', 'information_schema');
```
**Expected:** 50+ foreign keys

### ✅ CHECK Constraints Created
```sql
SELECT table_schema, table_name, constraint_name
FROM information_schema.table_constraints
WHERE constraint_type = 'CHECK'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;
```
**Expected:** 15+ CHECK constraints

### ✅ Seed Data Inserted
```sql
-- Admin user
SELECT COUNT(*) FROM auth.users WHERE role = 'admin';
-- Expected: 1

-- Platforms
SELECT COUNT(*) FROM core.platforms;
-- Expected: 8

-- Brands
SELECT COUNT(*) FROM core.brands;
-- Expected: 10

-- Categories
SELECT COUNT(*) FROM core.categories;
-- Expected: 1
```

---

## Post-Setup Tasks

### 1. Populate Size Standardization

The `sizes` table needs standardized values for size matching to work:

```bash
# Run size standardization script (to be created)
python scripts/populate_size_standardization.py

# Or manually:
psql soleflip < scripts/size_standardization.sql
```

**Size conversion table:** See `docs/database/size-standardization.md`

### 2. Import Initial Data (Optional)

If you have existing data to import:

```bash
# Import products
python scripts/import_products.py data/products.csv

# Import inventory
python scripts/import_inventory.py data/inventory.csv

# Import Awin feed
python scripts/import_awin_sample_feed.py
```

### 3. Set Up Cron Jobs (Production)

```bash
# Add to crontab
crontab -e

# Example jobs:
# Sync StockX orders every hour
0 * * * * cd /path/to/soleflip && /path/to/venv/bin/python -m domains.integration.cli sync_stockx_orders

# Update market prices every 6 hours
0 */6 * * * cd /path/to/soleflip && /path/to/venv/bin/python -m domains.integration.cli update_market_prices

# Generate analytics daily at 2 AM
0 2 * * * cd /path/to/soleflip && /path/to/venv/bin/python -m domains.analytics.cli generate_daily_reports
```

### 4. Configure Database Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/var/backups/soleflip"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump soleflip | gzip > "$BACKUP_DIR/soleflip_$DATE.sql.gz"

# Keep only last 30 days
find "$BACKUP_DIR" -name "soleflip_*.sql.gz" -mtime +30 -delete
```

---

## Troubleshooting

### Error: "relation already exists"

**Problem:** You're trying to run the migration on a database that already has tables.

**Solution:** This migration is for fresh databases only. Either:
1. Drop the existing database and start fresh:
   ```bash
   dropdb soleflip
   createdb soleflip
   alembic upgrade consolidated_v1
   ```
2. Continue using incremental migrations on the existing database:
   ```bash
   alembic upgrade head
   ```

### Error: "schema does not exist"

**Problem:** The migration depends on schemas created earlier in the same migration.

**Solution:** This shouldn't happen with the consolidated migration. If it does, check that you're running the latest version of Alembic:
```bash
pip install --upgrade alembic
```

### Error: "could not create unique index"

**Problem:** There's duplicate data that violates a unique constraint.

**Solution:** This shouldn't happen on a fresh database. If it does:
1. Check that the database is truly empty
2. Check for any pre-existing data in the public schema

### Error: "permission denied for schema"

**Problem:** The database user doesn't have permission to create schemas.

**Solution:** Grant necessary permissions:
```sql
-- As superuser
GRANT CREATE ON DATABASE soleflip TO your_user;
GRANT ALL ON SCHEMA public TO your_user;
```

### Migration is Very Slow

**Problem:** Migration takes > 30 seconds.

**Possible causes:**
1. Database connection is slow (network issue)
2. Insufficient resources (CPU, RAM)
3. Disk I/O bottleneck

**Solution:**
1. Check database connection: `psql soleflip -c "SELECT 1"`
2. Monitor resources: `top` or `htop`
3. Use faster disk (SSD recommended)

---

## Rollback

If you need to rollback the migration:

```bash
# Rollback to base (empty database)
alembic downgrade base

# This will:
# - Drop all views
# - Drop all triggers and functions
# - Drop all tables
# - Drop all enums
# - Drop all schemas
```

**⚠️ WARNING:** This will delete ALL data in the database!

---

## Performance Benchmarks

Expected performance on a fresh database:

| Metric | Time | Notes |
|--------|------|-------|
| Schema creation | < 1s | 9 schemas |
| Enum creation | < 1s | 6 enums |
| Table creation | 3-5s | 35+ tables |
| Index creation | 2-3s | 100+ indexes |
| View creation | < 1s | 4 views |
| Trigger creation | < 1s | 3 triggers |
| Constraint creation | 1-2s | 15+ constraints |
| Seed data insertion | < 1s | ~20 records |
| **Total** | **5-10s** | Complete migration |

**Hardware:** Standard laptop (8GB RAM, SSD)
**PostgreSQL:** 14.x

---

## Next Steps

After successful setup:

1. ✅ **Read the architecture docs**
   - `docs/database-schema-complete-analysis.md`
   - `context/architecture/senior-architect-complete-database-review.md`

2. ✅ **Set up development environment**
   - Start development server: `make dev`
   - Run tests: `pytest`
   - Check code quality: `make lint`

3. ✅ **Import sample data**
   - Awin product feed
   - StockX catalog data
   - Supplier accounts

4. ✅ **Configure integrations**
   - StockX API credentials
   - Awin affiliate credentials
   - Payment provider tokens

5. ✅ **Deploy to staging**
   - Test complete workflow
   - Verify integrations
   - Performance testing

---

## FAQ

### Q: Can I use this migration on an existing database?

**A:** No. This migration is designed for fresh databases only. Existing databases should continue using incremental migrations (`alembic upgrade head`).

### Q: What if I want to add custom modifications?

**A:** For fresh installations, modify the consolidated migration file before running it. For existing databases, create a new incremental migration.

### Q: How do I update the seed data?

**A:** Edit the "INSERT SEED DATA" section in the migration file (section 8). The migration uses `ON CONFLICT DO NOTHING` so it's safe to run multiple times.

### Q: Can I skip the seed data?

**A:** No. The admin user and default platforms are required for the application to work. However, you can delete them after the migration completes.

### Q: How often should I regenerate this migration?

**A:** Only when there are significant schema changes or new architect recommendations. For minor changes, use incremental migrations.

### Q: What's the difference between this and running all 26 migrations?

**A:** This migration:
- ✅ Runs faster (5-10s vs 30s)
- ✅ Works on fresh databases (26 migrations have broken chain)
- ✅ Includes all architect recommendations (26 migrations missing some)
- ✅ Has complete documentation (26 migrations scattered)
- ✅ Has comprehensive seed data (26 migrations partial)

---

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the migration output for error messages
3. Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-14-main.log`
4. Verify database connection: `psql soleflip -c "SELECT version()"`
5. Check Alembic version: `alembic --version`

---

## References

- **Migration File:** `migrations/versions/2025_10_13_0000_consolidated_fresh_start.py`
- **Summary Document:** `docs/setup/CONSOLIDATED_MIGRATION_SUMMARY.md`
- **Schema Analysis:** `docs/database-schema-complete-analysis.md`
- **Architect Review:** `context/architecture/senior-architect-complete-database-review.md`

---

**Last Updated:** 2025-10-13
**Version:** 1.0
**Status:** Production Ready ✅
