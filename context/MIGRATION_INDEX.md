# Database Migrations Index

**Last Updated:** 2025-10-01
**Current Schema Version:** `84bc4d8b03ef`

## 📋 Active Migrations

### Latest: Multi-Platform Orders (v2.2.2)

**Migration ID:** `84bc4d8b03ef`
**Date:** 2025-10-01
**Status:** ✅ Completed

Unified order tracking across all marketplace platforms. Major architectural improvement.

**Key Changes:**
- Added `platform_id` to orders table (FK to `core.platforms`)
- Added `external_id` for generic platform order IDs
- Added `platform_fee`, `shipping_cost` tracking
- Added buyer location fields
- Made `stockx_order_number` nullable
- Migrated 1,270 legacy transactions

**Documentation:** `context/orders-multi-platform-migration.md`

**Impact:**
- ✅ **Unified Schema**: Single source of truth for all orders
- ✅ **Platform Agnostic**: Ready for eBay, GOAT, etc.
- ⚠️ **Analytics Dependencies**: 18 views still use legacy table

**Next Steps:**
- Migrate 18 analytics views to use new schema
- Update foreign key in `finance.expenses`
- Drop legacy `transactions.transactions` table

See: `context/analytics-views-migration-plan.md`

---

### Notion Sale Fields (v2.2.1)

**Migration ID:** `1fc1f0c9b64d`
**Date:** 2025-09-30
**Status:** ✅ Completed

Added 13 new fields to support comprehensive Notion sync data.

**Key Changes:**
- Added VAT tracking fields (`vat_amount`, `vat_rate`)
- Added sale metrics (`gross_sale`, `net_proceeds`, `roi`)
- Added payout tracking (`payout_received`, `payout_date`)
- Added inventory velocity (`shelf_life_days`)

**Documentation:** `context/notion/00-STATUS-REPORT.md`

---

### Marketplace Data Table (v2.2.0)

**Migration ID:** `887763befe74`
**Date:** 2025-09-29
**Status:** ✅ Completed

Created `products.marketplace_data` table for real-time platform pricing.

**Key Changes:**
- Tracks market prices, fees, availability across platforms
- Supports automated repricing
- Historical price tracking

---

## 📊 Schema Evolution Timeline

```
v2.2.2 (2025-10-01) - Multi-Platform Orders
    ↓
v2.2.1 (2025-09-30) - Notion Sale Fields
    ↓
v2.2.0 (2025-09-29) - Marketplace Data
    ↓
v2.1.0 (2025-09-19) - Business Intelligence Fields
    ↓
v2.0.0 (2025-09-19) - Supplier Accounts Management
    ↓
v1.0.0 (2025-08-30) - Initial Production Schema
```

## 🎯 Pending Migrations

### High Priority

1. **Analytics Views Migration** (Planned: 2025-10-02)
   - Migrate 18 analytics views from legacy table
   - Update `finance.expenses` foreign key
   - Drop `transactions.transactions` table
   - **Estimated Effort:** 17 hours over 3 weeks
   - **Documentation:** `context/analytics-views-migration-plan.md`

### Medium Priority

2. **Order Model Updates** (Planned: 2025-10-08)
   - Update `shared/database/models.py` Order class
   - Add platform relationship
   - Update OrderRepository
   - Add platform filtering to queries

3. **API Documentation** (Planned: 2025-10-10)
   - Update OpenAPI schemas
   - Add platform field to order endpoints
   - Document multi-platform filtering

### Low Priority

4. **Platform Adapters** (Planned: Q4 2025)
   - Implement eBay adapter
   - Implement GOAT adapter
   - Implement Grailed adapter

## 🗄️ Schema Documentation

### Core Schemas

- **`core`**: System-wide entities (platforms, config, users)
- **`products`**: Product catalog, brands, inventory
- **`transactions`**: Orders, marketplace data (unified)
- **`finance`**: Expenses, payments, supplier accounts
- **`analytics`**: Materialized views and aggregations
- **`auth`**: Authentication tokens, user roles

### Key Tables

| Table | Schema | Records | Purpose | Status |
|-------|--------|---------|---------|--------|
| `orders` | transactions | 1,309 | **Unified multi-platform orders** | ✅ Active |
| `transactions` | transactions | 1,309 | Legacy archive | ⚠️ Deprecated |
| `inventory` | products | ~2,000 | Product stock tracking | ✅ Active |
| `products` | products | ~500 | Product catalog | ✅ Active |
| `platforms` | core | 5 | Marketplace configs | ✅ Active |
| `marketplace_data` | products | ~10,000 | Real-time pricing | ✅ Active |

## 📝 Migration Best Practices

### Before Running Migrations

1. **Backup Database**
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Check Current Version**
   ```bash
   python -m alembic current
   ```

3. **Review Migration SQL**
   ```bash
   python -m alembic upgrade head --sql
   ```

### Running Migrations

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Apply specific migration
python -m alembic upgrade <revision_id>

# Rollback one migration
python -m alembic downgrade -1

# Check migration history
python -m alembic history
```

### After Running Migrations

1. **Verify Data Integrity**
   ```sql
   SELECT COUNT(*) FROM transactions.orders;
   SELECT * FROM alembic_version;
   ```

2. **Test Application**
   ```bash
   pytest tests/integration/
   ```

3. **Monitor Logs**
   ```bash
   tail -f logs/app.log
   ```

## 🚨 Rollback Procedures

### Rollback Latest Migration

```bash
# Rollback one step
python -m alembic downgrade -1

# Rollback to specific version
python -m alembic downgrade <revision_id>

# Restore from backup (nuclear option)
psql $DATABASE_URL < backup_20251001_073000.sql
```

### Known Rollback Issues

1. **Multi-Platform Migration (`84bc4d8b03ef`)**
   - Rolling back removes `platform_id` field
   - Will break any new orders created with non-StockX platforms
   - Requires manual data cleanup if rolled back

2. **Notion Fields (`1fc1f0c9b64d`)**
   - Rolling back removes 13 fields
   - Notion sync will fail until re-applied

## 🔗 Related Documentation

- **Main Migration Docs:**
  - `context/orders-multi-platform-migration.md` - Multi-platform orders
  - `context/analytics-views-migration-plan.md` - Analytics migration plan
  - `context/notion/00-STATUS-REPORT.md` - Notion integration status

- **Architecture:**
  - `CLAUDE.md` - System architecture overview
  - `shared/database/models.py` - SQLAlchemy models
  - `migrations/versions/` - All migration files

- **Developer Guides:**
  - `docs/guides/database_migrations.md` - Creating migrations
  - `docs/guides/rollback_procedures.md` - Emergency rollback

## 📞 Support

**Migration Issues:** Check logs in `migrations/logs/`
**Schema Questions:** See `shared/database/models.py`
**Emergency Rollback:** Contact DevOps team

---

**Maintained By:** Database Team
**Review Frequency:** After each migration
**Next Review:** 2025-10-15 (after analytics migration)
