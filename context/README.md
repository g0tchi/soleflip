# SoleFlipper Context Documentation

**Version:** v2.2.3
**Last Updated:** 2025-10-01

This folder contains comprehensive documentation organized by topic for easy navigation and reference.

---

## 📁 Folder Structure

```
context/
├── migrations/          Database schema migrations and data migrations
├── integrations/        External platform integrations (Metabase, StockX, etc.)
├── architecture/        System architecture, design decisions, data models
├── refactoring/         Code quality improvements and best practices
├── archived/            Historical documentation from completed projects
├── notion/              Notion integration documentation
└── README.md            This file
```

---

## 🚀 Quick Access

### Most Frequently Used

| Document | Location | Purpose |
|----------|----------|---------|
| **Migration Index** | [migrations/MIGRATION_INDEX.md](migrations/MIGRATION_INDEX.md) | Current schema version, all migrations |
| **Metabase Quick Start** | [integrations/metabase-integration-quickstart.md](integrations/metabase-integration-quickstart.md) | 5-minute Metabase setup |
| **Architecture Overview** | [integrations/metabase-architecture-overview.md](integrations/metabase-architecture-overview.md) | System architecture diagrams |
| **Database Schema** | [architecture/database-analysis.md](architecture/database-analysis.md) | Complete database structure |
| **Code Quality Standards** | [refactoring/README.md](refactoring/README.md) | Linting, formatting, testing |

---

## 📋 Detailed Index

### 1. Migrations (`migrations/`)

**Purpose:** Database schema evolution tracking

**Key Documents:**
- **MIGRATION_INDEX.md** - Master index of all migrations (v1.0.0 → v2.2.3)
- **orders-multi-platform-migration.md** - Multi-platform order tracking (v2.2.2)
- **analytics-views-migration-plan.md** - Analytics views migration (v2.2.3)
- **migration-timeline.md** - Complete migration history
- **pci-compliance-migration.md** - Security and compliance updates

**Current Version:** v2.2.3

**Latest Migrations:**
1. Metabase Integration (v2.2.3) - 7 materialized views
2. Schema Cleanup (v2.2.3) - Removed redundant fields
3. Analytics Views (v2.2.3) - 17 views migrated
4. Multi-Platform Orders (v2.2.2) - Unified order tracking

[📖 More Details](migrations/README.md)

---

### 2. Integrations (`integrations/`)

**Purpose:** External platform integration documentation

**Key Documents:**

#### Metabase (v2.2.3) - Business Intelligence
- **metabase-integration-quickstart.md** - Quick start guide
- **metabase-architecture-overview.md** - Architecture details
- **metabase-api-integration-explained.md** - API integration guide

**Module:** `domains/integration/metabase/`

**Features:**
- 7 materialized views (executive, product, brand, platform, inventory, geography, supplier)
- 4 pre-built dashboards
- 17 REST API endpoints
- Automated refresh (hourly/daily/weekly)

#### StockX - Marketplace Integration
- **stockx-product-search-api-discovery.md** - API analysis
- **stockx-sku-strategy.md** - SKU matching logic

**Module:** `domains/integration/services/stockx_service.py`

#### Budibase (v2.2.1) - Low-Code Platform
- See: `domains/integration/budibase/`
- Archived docs: `archived/08_budibase_integration_module.md`

#### Notion - Operations Management
- See: `notion/` folder
- Automated sales/purchase data sync

[📖 More Details](integrations/README.md)

---

### 3. Architecture (`architecture/`)

**Purpose:** System design, data models, architectural decisions

**Key Documents:**

#### Database Design
- **database-analysis.md** - Complete schema structure
- **schema-consolidation-analysis.md** - Multi-schema strategy
- **transactions-schema-analysis.md** - Order tracking architecture

#### Data Architecture
- **marketplace-data-architecture.md** - Real-time pricing (v2.2.0)
- **platform-vs-direct-sales-analysis.md** - Sales channel analysis

#### Business Logic
- **roi-calculation-b2b-implementation.md** - Profit calculations
- **product-review-workflow.md** - Review system design

#### Performance
- **inventory-refresh-test-report.md** - Performance benchmarks

**Database Schemas:**
- `core` - Users, platforms, brands, suppliers
- `products` - Catalog, inventory
- `transactions` - Orders, payments
- `analytics` - Materialized views
- `finance` - Expenses, accounting

[📖 More Details](architecture/README.md)

---

### 4. Refactoring (`refactoring/`)

**Purpose:** Code quality improvements, development best practices

**Key Documents:**
- **coverage-improvement-plan.md** - Test coverage strategy (80%+ target)
- **design-principles.md** - DDD, SOLID, Clean Architecture
- **optimization-analysis.md** - Performance optimization
- **style-guide.md** - Python code style (PEP 8, black, isort)

**Quality Standards:**
- ✅ Zero linting violations (ruff)
- ✅ 100% formatting compliance (black, isort)
- ✅ Type hints on all public APIs
- ✅ 80%+ test coverage

**Tools:**
```bash
make format       # Auto-format code
make lint         # Check quality
make check        # All checks + tests
```

[📖 More Details](refactoring/README.md)

---

### 5. Archived (`archived/`)

**Purpose:** Historical documentation from completed projects

**Contents:**
- Refactoring sprint sessions (01-07, 10)
- Budibase integration projects (08-09)

**Value:**
- Historical record of decisions
- Learning resource (patterns & anti-patterns)
- Process template for future refactoring
- Context for understanding current state

**Highlights:**
- Complete 7-day refactoring sprint (2024-09-24 to 2024-09-28)
- Achievement: 80%+ test coverage, zero linting violations
- Budibase integration implementation

[📖 More Details](archived/README.md)

---

### 6. Notion (`notion/`)

**Purpose:** Notion integration and automation

**Key Documents:**
- **00-STATUS-REPORT.md** - Current status and metrics
- **01-implementation-completion.md** - Implementation details
- **02-schema-analysis.md** - Database schema mapping
- **03-sync-strategy.md** - Synchronization approach
- **04-purchase-data-analysis.md** - Purchase data tracking
- **05-automation-strategy.md** - Automation workflows
- **06-budibase-migration-plan.md** - Budibase migration
- **README.md** - Overview and index

**Features:**
- Automated sales data sync from Notion to PostgreSQL
- Purchase data tracking
- Multi-platform transaction support
- Inventory management

[📖 More Details](notion/README.md)

---

## 🎯 Common Tasks

### I want to...

**...understand the current database schema**
→ Read [architecture/database-analysis.md](architecture/database-analysis.md)

**...setup Metabase dashboards**
→ Follow [integrations/metabase-integration-quickstart.md](integrations/metabase-integration-quickstart.md)

**...check migration status**
→ See [migrations/MIGRATION_INDEX.md](migrations/MIGRATION_INDEX.md)

**...understand code quality standards**
→ Review [refactoring/README.md](refactoring/README.md)

**...learn about StockX integration**
→ Read [integrations/stockx-product-search-api-discovery.md](integrations/stockx-product-search-api-discovery.md)

**...see refactoring history**
→ Browse [archived/README.md](archived/README.md)

**...understand Notion sync**
→ Check [notion/README.md](notion/README.md)

---

## 📊 System Overview

### Current Version: v2.2.3

**Architecture:**
- Domain-Driven Design (DDD)
- Multi-schema PostgreSQL database
- Repository pattern
- Event-driven updates
- REST API (FastAPI)

**Integrations:**
- ✅ Metabase (BI) - v2.2.3
- ✅ Budibase (Low-Code) - v2.2.1
- ✅ StockX (Marketplace)
- ✅ Notion (Operations)
- 🔜 eBay (Planned)
- 🔜 GOAT (Planned)

**Code Quality:**
- ✅ 80%+ test coverage
- ✅ Zero linting violations
- ✅ Type hints on all APIs
- ✅ Async/await patterns

**Performance:**
- ✅ Optimized connection pooling
- ✅ Strategic database indexing
- ✅ Materialized views for analytics
- ✅ Redis caching
- ✅ Streaming responses

---

## 🔍 Search Guide

### By Topic

- **Migrations:** `migrations/`
- **Integrations:** `integrations/`
- **Architecture:** `architecture/`
- **Code Quality:** `refactoring/`
- **History:** `archived/`
- **Notion:** `notion/`

### By Date

- **2025-10-01:** Metabase integration (v2.2.3)
- **2025-10-01:** Analytics views migration
- **2025-10-01:** Multi-platform orders (v2.2.2)
- **2025-09-30:** Notion sale fields (v2.2.1)
- **2025-09-29:** Marketplace data table (v2.2.0)
- **2024-09-28:** Refactoring sprint completion

### By Module

- **Metabase:** `integrations/metabase-*.md` + `domains/integration/metabase/`
- **Budibase:** `archived/08_budibase_*.md` + `domains/integration/budibase/`
- **StockX:** `integrations/stockx-*.md` + `domains/integration/services/`
- **Notion:** `notion/*.md` + `domains/integration/notion/`

---

## 📚 Related Documentation

### In Repository

- **Code Documentation:** `domains/*/README.md`
- **API Documentation:** `http://localhost:8000/docs` (when running)
- **Main README:** `../README.md`
- **CLAUDE.md:** `../CLAUDE.md` (development commands)

### External Resources

- **Metabase Docs:** https://www.metabase.com/docs/
- **Budibase Docs:** https://docs.budibase.com/
- **StockX API:** Internal documentation
- **Notion API:** https://developers.notion.com/

---

## 🤝 Contributing

When adding new documentation:

1. **Choose the right folder:**
   - Database changes → `migrations/`
   - External integrations → `integrations/`
   - System design → `architecture/`
   - Code quality → `refactoring/`
   - Completed projects → `archived/`

2. **Update the relevant README** in that folder

3. **Update this main README** if it's a major addition

4. **Follow naming conventions:**
   - Use lowercase with hyphens: `my-document-name.md`
   - Include dates for versioned docs: `2025-10-01-feature-name.md`
   - Be descriptive: `metabase-integration-quickstart.md` not `mb-quick.md`

---

## 📞 Quick Reference

### Development

```bash
# Start API
uvicorn main:app --reload

# Run tests
pytest --cov

# Format code
make format

# Apply migrations
alembic upgrade head
```

### Metabase

```bash
# Setup Metabase views
python domains/integration/metabase/setup_metabase.py

# Refresh all views
curl -X POST "http://localhost:8000/api/v1/metabase/sync/all"

# Open Metabase
http://localhost:6400
```

### Documentation

```bash
# API Documentation
http://localhost:8000/docs

# Context Documentation
cd context/
```

---

**Last Updated:** 2025-10-01
**Version:** v2.2.3
**Maintained by:** SoleFlipper Development Team
