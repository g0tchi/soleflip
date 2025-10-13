# Migration Chain Fix - Fresh Database Setup

**Date:** 2025-10-12
**Status:** 🔴 **CRITICAL - Blocking fresh database setup**
**Issue:** Multiple migrations have incompatible schema references

---

## Problem Summary

The migration chain has accumulated technical debt over time with inconsistent schema references:

1. **Initial schema** creates tables in different schemas:
   - `core.suppliers`, `core.brands`, `core.categories`
   - `products.products`, `products.inventory`
   - `transactions.transactions`

2. **Later migrations** reference different schemas:
   - Some expect `sales.transactions` (doesn't exist)
   - Some expect root `inventory` (actually in `products`)
   - Schema references are inconsistent across migration files

3. **Result:** Fresh database setup fails after 4-5 migrations

---

## Impact

- ❌ Cannot create fresh database from scratch
- ❌ Blocks testing of price_sources architecture
- ❌ Prevents "hard reset" as requested by user

---

## Solutions

### **Option A: Fix All Migrations (Conservative)**

**Approach:**
Go through all 20+ migration files and fix schema references

**Pros:**
- Preserves full migration history
- Can upgrade/downgrade cleanly

**Cons:**
- Time-consuming (need to fix ~20 files)
- Error-prone
- May uncover more inconsistencies

**Estimated Time:** 2-3 hours

---

### **Option B: Create Consolidated Migration (Recommended)**

**Approach:**
Create ONE new migration with the complete current schema

**Steps:**

1. **Document current working schema** (from existing database)
   ```bash
   pg_dump --schema-only soleflip > context/schema/current_schema.sql
   ```

2. **Create new consolidated migration**
   - File: `migrations/versions/2025_10_12_1600_consolidated_fresh_start.py`
   - Contains complete schema with all tables, indexes, views
   - Replaces all previous migrations for fresh installs

3. **Update alembic history**
   - Mark this as base migration for fresh installations
   - Keep old migrations for existing databases

4. **Test fresh installation**
   ```bash
   dropdb soleflip
   createdb soleflip
   alembic upgrade head
   ```

**Pros:**
- ✅ Fast (1 hour vs 2-3 hours)
- ✅ Single source of truth
- ✅ Guaranteed to work
- ✅ Easier to maintain

**Cons:**
- Loses granular migration history (but who needs it for fresh installs?)
- Existing databases still need old migrations (acceptable)

**Estimated Time:** 1 hour

---

### **Option C: Database Dump/Restore (Pragmatic)**

**Approach:**
Export existing working database, use as seed for fresh installs

**Steps:**

1. Export current working schema:
   ```bash
   pg_dump --schema-only --no-owner soleflip > seeds/fresh_database_schema.sql
   ```

2. Create fresh database script:
   ```bash
   psql -d soleflip -f seeds/fresh_database_schema.sql
   ```

3. Insert migration version record manually

**Pros:**
- ✅ Fastest solution (30 minutes)
- ✅ 100% accurate to current state

**Cons:**
- Bypasses alembic (not ideal)
- Manual version tracking needed
- Not standard practice

---

## Recommendation

**Go with Option B: Consolidated Migration**

**Reasoning:**
1. Best balance of speed vs. maintainability
2. Standard alembic practice
3. Works for both fresh installs and existing databases
4. Future-proof (no more schema reference issues)

---

## Implementation Plan (Option B)

### Phase 1: Document Current Schema (5 minutes)

**IF we have a working database:**
```bash
# From existing working database
pg_dump --schema-only soleflip > context/schema/current_working_schema.sql
```

**IF starting fresh:**
- Manually construct schema from latest migration files
- Use SQLAlchemy models as reference

---

### Phase 2: Create Consolidated Migration (40 minutes)

**File:** `migrations/versions/2025_10_12_1600_consolidated_fresh_start.py`

**Contents:**
```python
"""Consolidated schema for fresh database setup

Revision ID: consolidated_v1
Revises: None
Create Date: 2025-10-12 16:00:00

This migration contains the COMPLETE schema for fresh installations.
Existing databases should continue using the historical migration chain.
"""

def upgrade():
    # Create all schemas
    op.execute('CREATE SCHEMA IF NOT EXISTS core')
    op.execute('CREATE SCHEMA IF NOT EXISTS products')
    op.execute('CREATE SCHEMA IF NOT EXISTS integration')
    op.execute('CREATE SCHEMA IF NOT EXISTS transactions')
    op.execute('CREATE SCHEMA IF NOT EXISTS pricing')
    op.execute('CREATE SCHEMA IF NOT EXISTS analytics')

    # Create ALL tables in correct order
    # ... (full schema here)

def downgrade():
    # Drop everything
    op.execute('DROP SCHEMA IF EXISTS analytics CASCADE')
    op.execute('DROP SCHEMA IF EXISTS pricing CASCADE')
    # ... etc
```

---

### Phase 3: Configure Alembic for Dual Mode (10 minutes)

**Update:** `migrations/README_FRESH_INSTALL.md`

```markdown
# Fresh Installation

For NEW databases, use:
```bash
alembic upgrade consolidated_v1
```

For EXISTING databases, use:
```bash
alembic upgrade head
```

---

### Phase 4: Test Fresh Installation (5 minutes)

```bash
# Drop and recreate database
python scripts/reset_database.py

# Run consolidated migration
alembic upgrade consolidated_v1

# Verify all tables exist
python scripts/verify_schema.py
```

---

## Alternative: Skip Migration Issues Entirely

Given that we're doing a "hard reset" anyway, we could:

1. **Use current working database as baseline**
2. **Export just the data we need** (suppliers, products, etc.)
3. **Create consolidated migration from scratch**
4. **Import data into fresh database**

This is essentially what the user wants - a clean slate with the new architecture.

---

## Decision Needed

**User, please choose:**

1. **Option A** - Fix all 20+ migrations (2-3 hours, preserves history)
2. **Option B** - Create consolidated migration (1 hour, recommended)
3. **Option C** - Use SQL dump (30 min, bypasses alembic)

**My recommendation:** Option B

We can start fresh with the price_sources architecture and have a clean migration path going forward.

---

## Current Status

**Blocked At:** Migration `2025_08_30_0915` (Minimal safe cleanup)
**Error:** `schema "sales" does not exist` (expects sales.transactions)
**Root Cause:** Inconsistent schema naming across migration chain

**Next Steps:**
1. User confirms approach
2. Implement chosen solution
3. Test fresh database setup
4. Continue with price_sources testing
