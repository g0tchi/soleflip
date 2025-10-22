# Soleflip Database Schema Structure

## Overview
This database follows Domain-Driven Design (DDD) principles with 64 tables organized across 14 schemas.

**Last Updated:** 2025-10-21 (Schema Consolidation v2.3.1)

## Schema Organization

### 📦 CATALOG Schema (6 tables)
**Purpose:** Product catalog master data - all product-related reference data

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `brand` | Product brands (Nike, Adidas, etc.) | name, slug, description |
| `category` | Product categories (Sneakers, Apparel) | name, slug, parent_id |
| `product` | Main product catalog | sku, name, brand_id, category_id |
| `product_variant` | Size/color variants | product_id, size_id, color |
| `product_category_mapping` | Product-category associations | product_id, category_id |
| `product_platform_availability` | Platform availability windows | product_id, platform_id |

**Use Cases:**
- Merchandising team manages product catalog
- Customer search and filtering
- Product presentation and categorization

---

### ⚙️ CORE Schema (6 tables)
**Purpose:** System-level infrastructure and shared resources

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `size_master` | Size reference data | size_value, gender, size_standard |
| `size_conversion` | Size conversions (US↔EU↔UK) | source_size, target_size |
| `supplier` | Supplier master data | name, email, phone |
| `system_config` | System configuration | key, value, category |
| `system_event_sourcing` | Event sourcing log | event_type, aggregate_id |
| `system_batch_operation` | Batch job tracking | operation_type, status |

**Use Cases:**
- System administration
- Multi-tenant configuration
- Size standardization across platforms

---

### 📦 PRODUCT Schema (8 tables)
**Purpose:** Inventory management and order operations

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `inventory_financial` | Financial cost tracking | product_id, cost_price, margin |
| `inventory_lifecycle` | Product lifecycle state | product_id, lifecycle_stage |
| `inventory_reservation` | Stock reservations | product_id, quantity, expires_at |
| `inventory_stock` | Current stock levels | product_id, quantity, location |
| `listing` | Platform listings | product_id, platform_id, price |
| `order` | Customer orders | order_number, total_amount, status |
| `size_availability_range` | Available size ranges | product_id, min_size, max_size |
| `size_profile` | Size fit profiles | product_id, fits_true_to_size |

**Use Cases:**
- Inventory management
- Stock tracking and reservations
- Order fulfillment

---

### 🏭 SUPPLIER Schema (3 tables)
**Purpose:** Procurement and supplier relationship management

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `account` | Supplier accounts | supplier_id, email, credentials |
| `account_purchase_history` | Purchase records | supplier_id, product_id, cost |
| `account_setting` | Supplier preferences | supplier_id, auto_order, min_quantity |

**Use Cases:**
- Sourcing team manages supplier relationships
- Purchase tracking and performance
- Automated ordering workflows

---

### 💰 PRICING Schema (7 tables)
**Purpose:** Pricing strategies and market analysis

| Table | Purpose |
|-------|---------|
| `brand_multiplier` | Brand-specific pricing rules |
| `demand_pattern` | Demand forecasting data |
| `kpi` | Key performance indicators |
| `market_price` | Market price tracking |
| `price_history` | Historical pricing data |
| `price_rule` | Automated pricing rules |
| `sales_forecast` | Sales predictions |

---

### 💵 TRANSACTION Schema (4 tables)
**Purpose:** Financial transactions and order processing

| Table | Purpose |
|-------|---------|
| `transaction` | All sales transactions |
| `pricing_history` | Transaction price changes |
| `stockx_listing` | StockX platform listings |
| `stockx_order` | StockX platform orders |

---

### 📊 ANALYTICS Schema (9 tables)
**Purpose:** Business intelligence and reporting (materialized views)

| Table | Purpose |
|-------|---------|
| `current_inventory_status_mv` | Real-time inventory snapshot |
| `daily_sales_summary_mv` | Daily sales aggregates |
| `marketplace_data` | Multi-platform comparison |
| `marketplace_summary` | Platform performance summary |
| `monthly_pl_summary_mv` | P&L monthly rollup |
| `platform_performance_comparison_mv` | Cross-platform metrics |
| `product_profitability_analysis_mv` | Product profitability |
| `supplier_performance` | Supplier metrics |
| `supplier_performance_dashboard_mv` | Supplier dashboard |

---

### 🔗 INTEGRATION Schema (4 tables)
**Purpose:** External system integration and data import

| Table | Purpose |
|-------|---------|
| `event_store` | Integration events log |
| `import_batch` | Bulk import batches |
| `import_record` | Individual import records |
| `source_price` | External price sources |

---

### 🏢 PLATFORM Schema (4 tables)
**Purpose:** Marketplace platform management

| Table | Purpose |
|-------|---------|
| `fee` | Platform fee structures |
| `integration` | Platform API configs |
| `marketplace` | Supported marketplaces |
| `size_display` | Platform size display rules |

---

### 📝 LOGGING Schema (3 tables)
**Purpose:** Audit trails and system logs

| Table | Purpose |
|-------|---------|
| `audit_trail` | User action audit log |
| `stockx_presale_marking` | StockX presale tracking |
| `system_log` | Application error logs |

---

### ⚖️ COMPLIANCE Schema (3 tables)
**Purpose:** Business rules and permissions

| Table | Purpose |
|-------|---------|
| `business_rule` | Configurable business rules |
| `data_retention_policy` | Data lifecycle policies |
| `user_permission` | Access control |

---

### 🚚 OPERATIONS Schema (3 tables)
**Purpose:** Fulfillment and logistics

| Table | Purpose |
|-------|---------|
| `listing_history` | Listing state changes |
| `order_fulfillment` | Fulfillment tracking |
| `supplier_platform_integration` | Supplier-platform links |

---

### 💼 FINANCIAL Schema (3 tables)
**Purpose:** Financial contracts and snapshots

| Table | Purpose |
|-------|---------|
| `product_price_snapshot` | Point-in-time pricing |
| `supplier_contract` | Supplier agreements |
| `supplier_rating_history` | Supplier rating tracking |

---

### ⚡ REALTIME Schema (1 table)
**Purpose:** Real-time event processing

| Table | Purpose |
|-------|---------|
| `event_log` | Real-time event stream |

---

## Key Design Principles

### 1. Domain-Driven Design (DDD)
Each schema represents a **bounded context** with clear responsibilities:
- **CATALOG**: Merchandising and product presentation
- **SUPPLIER**: Procurement and sourcing
- **PRODUCT**: Inventory and operations
- **CORE**: System infrastructure

### 2. Team Autonomy
Schema separation enables team independence:
- **Merchandising Team** → Works with `catalog.*`
- **Sourcing Team** → Works with `supplier.*`
- **Operations Team** → Works with `product.*`
- **System Team** → Manages `core.*`

### 3. Microservices-Ready
Each schema can become an independent microservice:
- Catalog Service (catalog.*)
- Supplier Service (supplier.*)
- Inventory Service (product.*)
- Analytics Service (analytics.*)

### 4. No Redundant Naming
✅ Good: `catalog.product`, `supplier.account`
❌ Bad: `products.products`, `product.product`

## Migration History

### v2.3.1 (2025-10-21) - Schema Consolidation
- Moved `core.brand` → `catalog.brand`
- Moved `core.category` → `catalog.category`
- Moved `product.product` → `catalog.product`
- **Result**: Clearer domain separation, eliminated redundant naming

### v2.3.0 (2025-10-21) - Complete Gibson Schema
- Migrated all 64 tables from Gibson AI MySQL to PostgreSQL
- Created 14 domain-specific schemas
- Implemented multi-tenant architecture with soft deletes

## Database Files

| File | Purpose |
|------|---------|
| `init-databases.sql` | Schema creation and permissions |
| `schema-tables.sql` | Phase 1 tables (core modules) |
| `schema-tables-phase2.sql` | Phase 2 tables (remaining modules) |
| `schema-consolidation-migration.sql` | v2.3.1 catalog consolidation |

## Common Queries

### Get all products with brand and category
```sql
SELECT
    p.name AS product,
    b.name AS brand,
    c.name AS category
FROM catalog.product p
JOIN catalog.brand b ON p.brand_id = b.id
JOIN catalog.category c ON p.category_id = c.id
WHERE p.deleted_at IS NULL;
```

### Check inventory for a product
```sql
SELECT
    p.name,
    s.quantity,
    s.location
FROM catalog.product p
JOIN product.inventory_stock s ON p.id = s.product_id
WHERE p.sku = 'DJ0950-101';
```

### Supplier performance
```sql
SELECT * FROM analytics.supplier_performance_dashboard_mv
ORDER BY total_purchases DESC;
```

## Notes

- All tables use `BIGSERIAL` for primary keys
- Multi-tenancy supported via `tenant_id` column
- Soft deletes via `deleted_at` column
- Versioning via `version` column
- UUID support for distributed systems
- Timestamps: `date_created`, `date_updated`
