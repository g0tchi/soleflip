# Database Migrations Documentation

This folder contains documentation related to database schema migrations and data migrations.

## 📋 Index

### Active Migrations

- **[MIGRATION_INDEX.md](MIGRATION_INDEX.md)** - Master index of all migrations (v1.0.0 → v2.2.3)
  - Current schema version tracking
  - Migration timeline
  - Pending migrations
  - Integration modules

### Completed Migrations (v2.2.x)

- **[orders-multi-platform-migration.md](orders-multi-platform-migration.md)** - Multi-Platform Orders (v2.2.2)
  - Unified order tracking across all marketplaces
  - Migration from single-platform to multi-platform schema
  - 1,270 legacy transactions migrated
  - Platform-agnostic architecture

- **[analytics-views-migration-plan.md](analytics-views-migration-plan.md)** - Analytics Views Migration (v2.2.3)
  - Migrated 17 analytics views from legacy schema
  - Updated finance.expenses foreign key
  - Dropped transactions.transactions table
  - Field mapping reference

### Historical Migrations

- **[migration-timeline.md](migration-timeline.md)** - Complete migration history
  - All schema changes from v1.0.0 onwards
  - Migration dependencies
  - Rollback procedures

- **[pci-compliance-migration.md](pci-compliance-migration.md)** - PCI Compliance Updates
  - Sensitive data encryption
  - Field security enhancements
  - Compliance validation

## 🎯 Quick Reference

### Current Schema Version
**v2.2.3** (2025-10-01)

### Latest Migrations
1. Metabase Integration (v2.2.3) - 7 materialized views
2. Schema Cleanup (v2.2.3) - Removed redundant fields
3. Analytics Views Migration (v2.2.3) - 17 views migrated
4. Multi-Platform Orders (v2.2.2) - Unified order tracking

### Migration Commands
```bash
# Apply pending migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current
```

## 📚 Related Documentation

- **Integration Modules:** `../integrations/`
- **Architecture Decisions:** `../architecture/`
- **Notion Integration:** `../notion/`

---

**Last Updated:** 2025-10-01
