# SoleFlipper Codebase - Detailed File Structure

## File Distribution by Component

### Domains (96 Python files total)

| Domain | Files | Key Services | Key Models | Status |
|--------|-------|--------------|-----------|--------|
| integration | ~40 | StockXService, TransformersService, ImportProcessor | ImportBatch, MarketplaceData | Production |
| inventory | 7 | InventoryService (1711 L), PredictiveInsightsService (940 L) | InventoryItem, Product | Production |
| pricing | 7 | SmartPricingService (631 L), AutoListingService (692 L), PricingEngine (620 L) | PriceRule, BrandMultiplier | Production |
| analytics | 4 | ForecastEngine (722 L) | SalesForecast, DemandPattern | Production |
| products | 5 | BrandService, CategoryService, ProductProcessor | Product, Brand, Category | Production |
| orders | 3 | OrderImportService | Transaction | Production |
| suppliers | 6 | SupplierIntelligenceService, AccountImportService | Supplier, SupplierAccount | Production |
| auth | 3 | Auth services | User, Token | Production |
| dashboard | 2 | Dashboard aggregation | - | Production |
| sales | 2 | TransactionProcessor | - | Legacy (Deprecated) |
| admin | 2 | Admin operations | - | Minimal (Not in prod) |

### Shared Modules (61 Python files total)

#### Database (6 files)
- `shared/database/models.py` - **967 lines** - SQLAlchemy ORM models
  - 15+ domain models across 6 schemas
  - EncryptedFieldMixin for sensitive data
  - TimestampMixin for audit trails
- `shared/database/connection.py` - Connection pool management
- `shared/database/session_manager.py` - Session lifecycle
- `shared/database/transaction_manager.py` - Transaction handling
- `shared/database/utils.py` - Database utilities

#### API & Types (9 files)
- `shared/api/dependencies.py` - **303 lines** - FastAPI DI
  - 8 dependency classes
  - 4 service dependencies
  - DependencyFactory pattern
- `shared/api/responses.py` - Response models
- `shared/types/service_types.py` - **545 lines** - Service types
- `shared/types/domain_types.py` - **511 lines** - Domain types
- `shared/types/api_types.py` - API types
- `shared/types/base_types.py` - Base types
- `shared/types/__init__.py` - Exports

#### Error Handling (2 files)
- `shared/error_handling/exceptions.py` - 7 exception classes
- `shared/exceptions/domain_exceptions.py` - Domain-specific exceptions

#### Monitoring (8 files)
- `shared/monitoring/health.py` - **556 lines**
- `shared/monitoring/metrics.py` - **680 lines**
- `shared/monitoring/advanced_health.py` - **674 lines**
- `shared/monitoring/apm.py` - APM integration
- `shared/monitoring/alerting.py` - Alert management
- `shared/monitoring/batch_monitor.py` - Job tracking
- `shared/monitoring/loop_detector.py` - Loop detection
- `shared/monitoring/prometheus.py` - Prometheus export

#### Events (3 files)
- `shared/events/event_bus.py` - **309 lines** - Event pub/sub
  - EventBus class with middleware
  - EventHandler wrapper
  - Domain subscriptions
- `shared/events/base_event.py` - BaseEvent class
- `shared/events/__init__.py` - Exports

#### Authentication & Security (5 files)
- `shared/auth/jwt_handler.py` - JWT tokens
- `shared/auth/password_hasher.py` - Bcrypt hashing
- `shared/auth/token_blacklist.py` - Token revocation
- `shared/security/api_security.py` - API-level security
- `shared/security/middleware.py` - Security middleware

#### Data Processing (4 files)
- `shared/processing/async_pipeline.py` - Async pipelines
- `shared/processing/streaming_processor.py` - Streaming
- `shared/processing/stages/retailer_stages.py` - **600 lines**

#### Utilities (6 files)
- `shared/utils/helpers.py` - **537 lines**
- `shared/utils/data_transformers.py` - Data conversion
- `shared/utils/validation_utils.py` - Validation
- `shared/utils/financial.py` - Financial calcs
- `shared/utils/__init__.py` - Exports

#### Other (8 files)
- `shared/repositories/base_repository.py` - **282 lines** - Generic CRUD
- `shared/repositories/__init__.py`
- `shared/performance/` - Query optimization, caching
- `shared/middleware/` - Compression, ETag
- `shared/logging/logger.py` - Structured logging
- `shared/caching/dashboard_cache.py` - Redis caching
- `shared/decorators/error_handling.py` - Error decorators
- `shared/validation/financial_validators.py` - Financial validation
- `shared/services/payment_provider.py` - Payment integration
- `shared/config/settings.py` - Configuration
- `shared/streaming/response.py` - Streaming responses

### Tests (23 unit/integration files + conftest)

```
tests/
├── unit/
│   ├── services/
│   │   ├── test_brand_service.py
│   │   ├── test_inventory_service.py
│   │   ├── test_stockx_service.py
│   │   └── test_brand_extractor_service.py
│   ├── repositories/
│   │   └── test_import_repository.py
│   ├── middleware/
│   │   └── test_etag_middleware.py
│   └── test_*.py (8 additional unit tests)
├── integration/
│   ├── api/
│   │   ├── test_products_api.py
│   │   ├── test_orders_api.py
│   │   ├── test_import_status.py
│   │   └── test_stockx_webhook.py
│   ├── test_import_pipeline.py
│   └── test_comprehensive_fixtures.py
├── fixtures/
│   ├── database_fixtures.py
│   ├── model_factories.py
│   ├── api_fixtures.py
│   └── __init__.py
├── conftest.py
└── load_testing.py
```

### Scripts (Multiple categories, ~50 files)

#### CLI Tools
- `cli/cli.py` - **1,275 lines** - Main CLI
- `cli/awin.py` - **574 lines** - AWIN integration CLI
- `cli/config.py` - Configuration management
- `cli/db.py` - Database operations
- `cli/security.py` - Security utilities
- `cli/shopify.py` - Shopify integration
- `cli/stockx_real.py` - StockX operations
- `cli/utils.py` - Utilities
- `cli/demo.py` - Demo commands

#### Pricing Scripts
- `scripts/pricing/forecast_cli.py` - **711 lines**
- `scripts/pricing/pricing_cli.py` - **599 lines**

#### Brand Intelligence
- `scripts/brand_intelligence/populate_brand_deep_dive.py` - **584 lines**

#### Database Maintenance
- `scripts/database/` - Migration, backup, maintenance scripts

#### Analysis & Debug
- `scripts/analysis/` - Data analysis scripts
- `scripts/debug/` - Debugging utilities

#### Deployment
- `scripts/deployment/` - Deployment automation
- `scripts/ci/` - CI/CD helpers

#### Other
- `scripts/find_stockx_awin_matches.py`
- `scripts/check_enrichment_status.py`
- `scripts/create_metabase_supplier_views.py`
- And 20+ other utility scripts

### Configuration & Root Files

| File | Lines | Purpose |
|------|-------|---------|
| main.py | 472 | FastAPI application entry point |
| pyproject.toml | 227 | Project configuration |
| Makefile | 200+ | Development commands |
| Dockerfile | 73 | Container image |
| alembic.ini | 99 | Database migration config |
| .env.example | - | Environment template |
| docker-compose.yml | 217 | Multi-service orchestration |
| docker-compose.nas.yml | 217 | NAS-optimized compose |
| docker-compose.local.yml | 181 | Local development compose |

### Documentation (docs/ directory)

- `CLAUDE.md` - Project guidelines (this file)
- `README.md` - Project overview
- `CHANGELOG.md` - Version history
- `DEPLOYMENT.md` - Deployment guide
- `CONSOLIDATED_MIGRATION_DELIVERY.md` - Migration tracking
- `database-schema-complete-analysis.md` - Schema documentation
- `schema_enhancements.md` - Schema improvements
- Setup guides, deployment guides, feature documentation
- Reports and analysis documents

## Code Statistics Summary

### By Type
- **Domain Code**: ~40,000 lines (domains/ + shared/)
- **Test Code**: ~15,000 lines (tests/)
- **Scripts**: ~10,000 lines (scripts/ + cli/)
- **Configuration**: ~1,500 lines (config files)
- **Documentation**: ~50 files

### By Size Distribution
- Files < 100 lines: ~180 (55%)
- Files 100-300 lines: ~90 (28%)
- Files 300-500 lines: ~25 (8%)
- Files 500-1000 lines: ~24 (7%)
- Files > 1000 lines: 5 (2%)

### Largest Files (Top 15)
1. inventory_service.py - 1,711 lines ⚠️
2. cli/cli.py - 1,275 lines ⚠️
3. integration/api/router.py - 983 lines ⚠️
4. shared/database/models.py - 967 lines ⚠️
5. predictive_insights_service.py - 940 lines ⚠️
6. stockx_catalog_service.py - 811 lines ⚠️
7. inventory/api/router.py - 770 lines ⚠️
8. transformers.py - 738 lines ⚠️
9. forecast_engine.py - 722 lines ⚠️
10. scripts/pricing/forecast_cli.py - 711 lines ⚠️
11. auto_listing_service.py - 692 lines ⚠️
12. products/api/router.py - 694 lines ⚠️
13. metrics.py - 680 lines ⚠️
14. advanced_health.py - 674 lines ⚠️
15. dead_stock_service.py - 659 lines ⚠️

## Code Organization Metrics

### Classes & Functions
- **Total Service Classes**: 29
- **Total Repository Classes**: 5
- **Total API Routers**: 33
- **Total Event Handlers**: 3 domains with handlers
- **Type Classes**: 50+ types defined

### Dependency Counts
- **Files with inter-domain imports**: 20
- **Circular dependencies detected**: None (good!)
- **Wildcard imports**: 0 (good!)

### Testing
- **Test Files**: 23
- **Test Classes**: 40+
- **Test Functions**: 150+
- **Test Markers**: 130 (unit, integration, api, slow, database)
- **Coverage Target**: 80%

## Migration History (14 major migrations)

1. 2025_08_14 - Initial schema
2. 2025_08_27 - Pricing and analytics schemas
3. 2025_08_30 - Cleanup
4. 2025_09_18 - Inventory index
5. 2025_09_19 - Selling schema
6. 2025_09_20 - PCI compliance
7. 2025_10_01 - Multi-platform orders
8. 2025_10_10 - Style code length
9. 2025_10_10 - Product enrichment (simplified)
10. 2025_10_11 - Supplier history
11. 2025_10_12 - AWIN enrichment
12. 2025_10_13 - Consolidated fresh start
13. 2025_10_20 - Merge migration heads
14. 2025_10_21 - Complete Gibson schema (all 54 tables)
15. 2025_10_22 - Gibson size system
16. 2025_10_22 - Product enrichment fields
17. 2025_10_25 - Cleanup obsolete schemas
18. 2025_10_25 - Gibson features

## Production Readiness

### Code Quality
- ✅ Black formatted
- ✅ isort organized imports
- ✅ ruff linted
- ✅ mypy type checked (strict mode)
- ✅ 80% test coverage

### Architecture
- ✅ Domain-Driven Design
- ✅ Repository pattern
- ✅ Service layer
- ✅ Dependency injection
- ✅ Event-driven communication

### Operations
- ✅ Structured logging
- ✅ Health checks (3 endpoints)
- ✅ Metrics collection
- ✅ APM integration
- ✅ Alert management
- ✅ Docker/Kubernetes ready

### Security
- ✅ JWT authentication
- ✅ Password hashing
- ✅ Token blacklist
- ✅ Field encryption
- ✅ API security middleware
- ✅ CORS configured
- ✅ Compression enabled

### Database
- ✅ Async SQLAlchemy 2.0
- ✅ Connection pooling (NAS-optimized)
- ✅ Alembic migrations
- ✅ Multi-schema support
- ✅ Query optimization

