# SoleFlipper Database Schema - Current State

**Generated:** 2025-10-26
**Database:** PostgreSQL 17
**Total Tables:** 53
**Total Records:** ~3,937
**Active Schemas:** 15 (cleaned up on 2025-10-26)

---

## Schema Overview

**Recent Changes (2025-10-26):**
- ✅ Removed 6 obsolete empty schemas: `forecasting`, `orders`, `platforms`, `product`, `products`, `transaction`
- ✅ Modernized all code references to use current DDD schema structure
- ✅ Aligned codebase with Gibson schema architecture



### Core Business Schemas

#### 1. **catalog** - Product Catalog Management
| Table | Records | Purpose |
|-------|---------|---------|
| `product` | 712 | Main product catalog with brand, category, SKU |
| `brand` | 65 | Brand information (Nike, adidas, Jordan, etc.) |
| `category` | 8 | Product categories (sneakers, apparel, accessories) |
| `size_master` | 20 | Gibson size system with multi-region conversion |
| `product_variant` | 20 | Product variants (colors, special editions) |
| `size_conversion` | 0 | Size conversion rules |
| `brand_history` | 2 | Brand timeline tracking |
| `brand_patterns` | 32 | Brand intelligence data for extraction |

**Key Features:**
- ✅ Intelligent brand detection from product names
- ✅ Multi-platform SKU support (style_code + generated SKU)
- ✅ Gibson-aligned size system with StockX validation

---

#### 2. **inventory** - Stock Management
| Table | Records | Purpose |
|-------|---------|---------|
| `stock` | 1,106 | Physical inventory items |
| `stock_financial` | 0 | Financial metrics per stock item |
| `stock_lifecycle` | 0 | Shelf-life and multi-platform tracking |
| `stock_reservation` | 0 | Stock holds and allocations |
| `stock_metrics` | 0 | Aggregated performance metrics (cache) |

**Key Features:**
- ✅ Product-based inventory (links to catalog.product)
- ✅ Separation of concerns (financial, lifecycle, metrics)
- ✅ Support for reservations and holds

---

#### 3. **sales** - Order Management
| Table | Records | Purpose |
|-------|---------|---------|
| `order` | 1,106 | Multi-platform order records |
| `listing` | 0 | Active product listings |
| `pricing_history` | 0 | Historical pricing data |

**Key Features:**
- ✅ Unified orders from all marketplaces (StockX, eBay, GOAT)
- ✅ StockX API integration with automatic imports
- ✅ Raw JSON storage for complete API responses
- ✅ Links to inventory.stock items

**Important Columns in `sales.order`:**
- `stockx_order_number` - Unique StockX identifier
- `inventory_item_id` - FK to inventory.stock
- `status` - Order status (COMPLETED, PENDING, etc.)
- `raw_data` - Complete StockX API response (JSONB)
- `platform_specific_data` - Extracted platform metadata (JSONB)

---

#### 4. **supplier** - Supplier Management
| Table | Records | Purpose |
|-------|---------|---------|
| `profile` | 0 | Supplier company information |
| `account` | 0 | Supplier account credentials |
| `purchase_history` | 0 | Purchase order history |
| `supplier_history` | 0 | Supplier timeline tracking |

---

#### 5. **integration** - Import & Data Processing
| Table | Records | Purpose |
|-------|---------|---------|
| `import_batches` | 14 | Import batch tracking |
| `import_records` | 0 | Individual import record status |
| `source_prices` | 0 | External price data |

**Key Features:**
- ✅ Batch tracking for CSV and API imports
- ✅ Status monitoring (pending, processing, completed, failed)
- ✅ Error logging and statistics

---

### Supporting Schemas

#### 6. **analytics** - Business Intelligence
| Table | Records | Purpose |
|-------|---------|---------|
| `inventory_status_summary` | 711 | Materialized view - inventory KPIs |
| `sales_summary_daily` | 0 | Materialized view - daily sales |
| `supplier_performance_summary` | 1 | Materialized view - supplier metrics |
| `demand_patterns` | 0 | Demand forecasting data |
| `forecast_accuracy` | 0 | ML forecast validation |
| `marketplace_data` | 0 | External marketplace trends |
| `pricing_kpis` | 0 | Pricing performance metrics |
| `sales_forecasts` | 0 | ARIMA time series forecasts |

**Materialized Views:**
- 🔄 Need periodic refresh (CONCURRENTLY recommended)
- ⚡ Pre-aggregated for dashboard performance

---

#### 7. **pricing** - Smart Pricing Engine
| Table | Records | Purpose |
|-------|---------|---------|
| `brand_multipliers` | 0 | Brand-specific pricing rules |
| `market_prices` | 0 | Current market pricing data |
| `price_history` | 0 | Historical price tracking |
| `price_rules` | 0 | Automated pricing rules |

---

#### 8. **compliance** - Business Rules & RBAC
| Table | Records | Purpose |
|-------|---------|---------|
| `business_rules` | 0 | Configurable business logic |
| `data_retention_policies` | 0 | GDPR compliance rules |
| `user_permissions` | 0 | Role-based access control |

**Gibson Feature:**
- ✅ Flexible rule engine for automated decisions
- ✅ Audit-ready retention policies

---

#### 9. **operations** - Operational Data
| Table | Records | Purpose |
|-------|---------|---------|
| `listing_history` | 0 | Listing status change audit trail |
| `order_fulfillment` | 0 | Shipping and delivery tracking |
| `supplier_platform_integration` | 0 | API sync configurations |

---

#### 10. **core** - System Configuration
| Table | Records | Purpose |
|-------|---------|---------|
| `system_config` | 4 | Encrypted system settings |
| `sizes` | 86 | Legacy size system |
| `size_validation_log` | 40 | StockX size validation results |
| `supplier_performance` | 0 | Legacy supplier metrics |

**Current System Config:**
- `stockx_api_key` - StockX API credentials (encrypted)
- `stockx_client_id` - OAuth client ID (encrypted)
- `stockx_client_secret` - OAuth secret (encrypted)
- `stockx_refresh_token` - OAuth refresh token (encrypted)

---

#### 11. **auth** - Authentication
| Table | Records | Purpose |
|-------|---------|---------|
| `users` | 0 | User accounts with encrypted credentials |

---

#### 12. **platform** - Marketplace Management
| Table | Records | Purpose |
|-------|---------|---------|
| `marketplace` | 0 | External platform configurations |

---

#### 13. **financial** - Financial Transactions
| Table | Records | Purpose |
|-------|---------|---------|
| `transaction` | 0 | Financial transaction records |

---

#### 14. **logging** - Event & Audit Logs
| Table | Records | Purpose |
|-------|---------|---------|
| `event_store` | 0 | Domain events |
| `system_logs` | 0 | Application logs |
| `stockx_presale_markings` | 0 | StockX pre-sale tracking |

---

#### 15. **realtime** - Live Events
| Table | Records | Purpose |
|-------|---------|---------|
| `event_log` | 0 | Real-time notifications (WebSocket/SSE) |

---

## Key Relationships

### Product → Orders Flow
```
catalog.brand ←─┐
                │
catalog.category ←─┼─── catalog.product ←─── inventory.stock ←─── sales.order
                   │
catalog.size_master ─┘
```

### StockX Import Flow
```
StockX API → integration.import_batches
                     ↓
           domains.orders.services.order_import_service
                     ↓
           ┌─────────┴─────────┐
           ↓                   ↓
    catalog.product      inventory.stock
           ↓                   ↓
           └────── sales.order ┘
```

---

## Important Schema Details

### catalog.product (712 records)

**Core Columns:**
- `id` - UUID (PK)
- `sku` - VARCHAR (UNIQUE, NOT NULL) - **Uses style_code if available**
- `style_code` - VARCHAR (NULL) - Real manufacturer code (e.g., "DV0982-100")
- `name` - VARCHAR (NOT NULL)
- `brand_id` - UUID (FK → catalog.brand)
- `category_id` - UUID (FK → catalog.category)
- `stockx_product_id` - VARCHAR - StockX product UUID

**Pricing Fields:**
- `retail_price` - NUMERIC
- `avg_resale_price` - NUMERIC
- `lowest_ask` - NUMERIC
- `highest_bid` - NUMERIC
- `recommended_sell_faster` - NUMERIC
- `recommended_earn_more` - NUMERIC

**Metadata:**
- `enrichment_data` - JSONB - Additional product data
- `last_enriched_at` - TIMESTAMP

**Status:**
- ✅ 643/712 products (90.31%) have `style_code`
- ✅ New imports use `style_code` as `sku` when available
- ✅ Brand detection active (BrandExtractorService)
- ✅ Category detection active (CategoryDetectionService)

---

### inventory.stock (1,106 records)

**Core Columns:**
- `id` - UUID (PK)
- `product_id` - UUID (FK → catalog.product)
- `size_id` - UUID (FK → catalog.size_master or core.sizes)
- `quantity` - INTEGER (NOT NULL)
- `status` - VARCHAR (NOT NULL) - "available", "sold", "reserved"
- `location` - VARCHAR

**Tracking:**
- `external_ids` - JSONB - Platform-specific identifiers
- `notes` - TEXT

**Timestamps:**
- `created_at` - TIMESTAMP
- `updated_at` - TIMESTAMP

---

### sales.order (1,106 records)

**Core Columns:**
- `id` - UUID (PK)
- `stockx_order_number` - VARCHAR (UNIQUE) - StockX identifier
- `inventory_item_id` - UUID (FK → inventory.stock)
- `status` - VARCHAR - Order status
- `amount` - NUMERIC
- `currency_code` - VARCHAR

**Financial:**
- `gross_sale` - NUMERIC
- `net_proceeds` - NUMERIC
- `gross_profit` - NUMERIC
- `net_profit` - NUMERIC
- `roi` - NUMERIC

**Platform Data:**
- `raw_data` - JSONB - **Complete StockX API response**
- `platform_specific_data` - JSONB - Extracted metadata

**Timestamps:**
- `stockx_created_at` - TIMESTAMP - Order creation on StockX
- `last_stockx_updated_at` - TIMESTAMP
- `sold_at` - TIMESTAMP
- `created_at` - TIMESTAMP - Import timestamp

---

## Database Statistics

**Total Tables:** 53
**Active Schemas:** 15 (down from 21 after cleanup)
**Total Records:** ~3,937
**Obsolete Schemas Removed:** 6 (forecasting, orders, platforms, product, products, transaction)

**Data Distribution:**
- Orders: 1,106 (sales.order)
- Inventory Items: 1,106 (inventory.stock)
- Products: 712 (catalog.product)
- Brands: 65 (catalog.brand)
- Sizes: 86 (core.sizes - legacy) + 20 (catalog.size_master - Gibson)
- Import Batches: 14 (integration.import_batches)

---

## Recent Schema Enhancements

### 2025-10-26 - Schema Cleanup & Modernization
**Changes:**
- ✅ Deleted 6 obsolete empty schemas (forecasting, orders, platforms, product, products, transaction)
- ✅ Created cleanup migration: `2025_10_25_2100_cleanup_obsolete_schemas.py`
- ✅ Modernized 12+ code files to use current DDD schemas:
  - `products.products` → `catalog.product`
  - `products.inventory` → `inventory.stock`
  - `core.brands` → `catalog.brand`
  - `core.categories` → `catalog.category`
  - `transactions.transactions` → `sales.order`

**Origin:** Obsolete schemas created by `consolidated_fresh_start` migration (Oct 13) became unused after DDD restructuring (Oct 22, v2.3.4)

**Files Updated:**
- `domains/integration/api/router.py`
- `domains/products/api/router.py`
- `domains/dashboard/api/router.py`
- `domains/analytics/api/router.py`
- `domains/inventory/services/inventory_service.py`
- `shared/monitoring/advanced_health.py`
- `shared/streaming/response.py`
- And 5 more integration service files

**Result:** Clean, consistent schema structure ready for git upload

---

### 2025-10-25 - style_code Integration
**Changes:**
- ✅ Added `style_code` extraction from StockX API
- ✅ Use `style_code` as `sku` for new products (when available)
- ✅ Backfilled 642 existing products with `style_code`
- ✅ Enhanced product matching across systems

**Files Modified:**
- `domains/orders/services/order_import_service.py`

**Database Impact:**
- 643/712 products now have manufacturer SKU codes
- Improved integration with external systems

---

### 2025-10-24 - Bulk StockX Import
**Event:**
- 1,106 orders imported
- 711 products created
- 86 sizes added

**Duration:** 8 minutes (17:54-18:02 UTC)

---

## Gibson Alignment Status

✅ **Aligned Schemas:** 12/15
✅ **Size System:** Dual (Gibson + Legacy)
✅ **Brand Intelligence:** Active
✅ **Category Detection:** Active
✅ **Materialized Views:** 3 configured

**PostgreSQL-Only Features** (not synced to Gibson):
- `auth.users` - Local authentication
- `catalog.brand_history` - Brand timeline
- `catalog.brand_patterns` - Brand intelligence
- `supplier.supplier_history` - Supplier timeline
- `analytics.forecast_accuracy` - ML metrics
- `core.sizes` - Legacy size system
- `core.size_validation_log` - StockX validation

---

## Maintenance Notes

### Materialized Views Refresh
```sql
-- Recommended: Hourly refresh via cron
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.inventory_status_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.sales_summary_daily;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.supplier_performance_summary;
```

### Data Cleanup
```sql
-- Remove old realtime events (7 days)
DELETE FROM realtime.event_log WHERE sent_at < now() - interval '7 days';

-- Compliance-based deletion (from retention policies)
-- See: docs/schema_enhancements.md
```

---

## API Integration Points

### StockX Integration
**Endpoints:**
- `POST /api/v1/integration/stockx/import-orders-background` - Historical order import
- `GET /api/v1/integration/stockx/credentials/status` - Credential status
- `GET /api/v1/integration/import-status/{batch_id}` - Import tracking

**Services:**
- `domains/integration/services/stockx_service.py` - StockX API client
- `domains/orders/services/order_import_service.py` - Order processing

**Features:**
- ✅ OAuth2 refresh token flow
- ✅ Automatic product creation with brand/category detection
- ✅ style_code extraction and SKU generation
- ✅ Background task processing

---

## Migration History

**Latest Migrations:**
1. `2025_10_22_1722_add_gibson_size_system.py` - Gibson size system
2. `2025_10_25_1800_move_size_tables_to_catalog.py` - Size tables reorganization
3. `2025_10_25_1900_add_brand_supplier_history.py` - History tracking
4. `2025_10_25_2000_add_gibson_features.py` - Gibson features integration

**Migration Tool:** Alembic
**Auto-apply:** On startup (via `shared/database/connection.py`)

---

## Performance Optimizations

### Indexes
- ✅ Unique constraints on SKU, stockx_order_number
- ✅ Foreign key indexes on all relationships
- ✅ JSONB GIN indexes on raw_data, platform_specific_data

### Connection Pooling
- Pool size: 15
- Max overflow: 20
- Pre-ping: Enabled (NAS-aware)

---

## Future Enhancements

### Planned
- [ ] Complete stock_financial population
- [ ] Stock lifecycle tracking implementation
- [ ] Real-time event system activation
- [ ] Automated materialized view refresh
- [ ] Price history tracking activation

### Under Consideration
- [ ] Multi-currency support enhancement
- [ ] Advanced forecasting models
- [ ] Supplier API integrations
- [ ] Automated listing management

---

**Document Version:** 1.1
**Last Updated:** 2025-10-26
**Maintained By:** Development Team

**Version History:**
- v1.1 (2025-10-26): Schema cleanup - removed 6 obsolete schemas, modernized code references
- v1.0 (2025-10-25): Initial comprehensive documentation with style_code integration
