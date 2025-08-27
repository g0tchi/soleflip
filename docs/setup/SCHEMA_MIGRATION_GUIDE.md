# 🗄️ Schema Migration Guide: Platform Table Move

## 📋 Overview

This migration moves the `platforms` table from `sales` schema to `core` schema to improve architectural consistency.

## 🔄 Changes Made

### Before (❌ Incorrect Architecture)
```sql
-- Platforms were in sales schema (domain-specific)
sales.platforms (id, name, slug, fee_percentage, active)
sales.transactions (platform_id REFERENCES sales.platforms.id, ...)

-- Master data was split across schemas
core.brands, core.categories, core.sizes  -- Master data
sales.platforms                          -- Also master data, but wrong schema!
```

### After (✅ Correct Architecture)
```sql
-- All master data consolidated in core schema
core.platforms (id, name, slug, fee_percentage, supports_fees, active)
core.brands (id, name, slug)
core.categories (id, name, slug, parent_id)
core.sizes (id, category_id, value, region)

-- Sales schema only contains transactional data
sales.transactions (platform_id REFERENCES core.platforms.id, ...)
```

## 🎯 Architectural Benefits

### 1. **Consistent Master Data Location**
- All reference/lookup tables now in `core` schema
- Clear separation between master data and transactional data

### 2. **Cross-Domain Accessibility**
- Integration services can reference platforms directly
- Product services can link to platform information
- No circular dependencies between domains

### 3. **Enhanced Platform Model**
- Added `supports_fees` boolean for platforms without explicit fees (like Alias)
- Better documentation and relationships

## 🚀 Migration Details

### Migration File: `002_move_platforms_to_core.py`

**What it does:**
1. ✅ Creates new `core.platforms` table with enhanced schema
2. ✅ Migrates existing data from `sales.platforms` (if exists)
3. ✅ Updates foreign key constraint in `sales.transactions`
4. ✅ Drops old `sales.platforms` table
5. ✅ Seeds default platform data (StockX, Alias, GOAT, eBay, Manual)

**Rollback capability:**
- Full downgrade support to restore old schema structure
- Data preservation during both upgrade and downgrade

## 🔧 Running the Migration

### Apply Migration
```bash
# Run the migration
alembic upgrade head

# Verify schema structure
psql -d soleflip -c "\dt core.*"
psql -d soleflip -c "SELECT name, slug, supports_fees FROM core.platforms;"
```

### Rollback (if needed)
```bash
# Rollback to previous version
alembic downgrade -1

# Verify rollback
psql -d soleflip -c "\dt sales.*"
```

## 📊 Default Platform Data

The migration seeds the following platforms:

| Name | Slug | Fee % | Supports Fees | Status |
|------|------|--------|---------------|---------|
| StockX | stockx | 9.5% | ✅ Yes | Active |
| Alias | alias | 0.0% | ❌ No | Active |
| GOAT | goat | 9.5% | ✅ Yes | Active |
| eBay | ebay | 10.0% | ✅ Yes | Active |
| Manual Sale | manual | 0.0% | ❌ No | Active |

## 🔍 Code Changes

### SQLAlchemy Models
```python
# OLD: Platform in sales schema
class Platform(Base):
    __table_args__ = {'schema': 'sales'}  # ❌ Wrong schema

# NEW: Platform in core schema  
class Platform(Base):
    __table_args__ = {'schema': 'core'}   # ✅ Correct schema
    supports_fees = Column(Boolean, default=True)  # ✅ New field

# Transaction updated to reference core
class Transaction(Base):
    platform_id = Column(UUID, ForeignKey("core.platforms.id"))  # ✅ Updated
```

### Import References
```python
# All platform references now point to core schema
from shared.database.models import Platform  # ✅ References core.platforms
```

## ✅ Verification Checklist

After running the migration, verify:

- [ ] `core.platforms` table exists with all expected columns
- [ ] `sales.platforms` table no longer exists
- [ ] `sales.transactions.platform_id` references `core.platforms.id`
- [ ] Default platform data is seeded
- [ ] All foreign key constraints are valid
- [ ] Application starts without schema errors

## 🚨 Important Notes

### For Developers
- Update any hardcoded schema references from `sales.platforms` to `core.platforms`
- The Platform model import remains the same - SQLAlchemy handles schema internally

### For DBAs
- This migration requires brief downtime for constraint updates
- Data is preserved during migration - no data loss expected
- Backup database before running in production

### For API Users
- No API changes required - all endpoints work the same
- Platform functionality enhanced with better fee handling

## 🎉 Result

Clean, consistent database architecture with:
- ✅ Master data consolidated in `core` schema
- ✅ Transactional data isolated in domain schemas  
- ✅ Clear separation of concerns
- ✅ Enhanced platform model with better fee handling
- ✅ Support for fee-less platforms (Alias)