-- ============================================================================
-- Schema Domain Restructuring Migration v2
-- Date: 2025-10-21
-- Purpose: Separate Inventory, Sales, and Product domains for better DDD
-- ============================================================================

-- This migration creates 3 separate bounded contexts:
-- 1. INVENTORY Domain - Warehouse/Operations Team
-- 2. SALES Domain - Sales/Marketing Team
-- 3. PRODUCT Domain - Product/Merchandising Team (size attributes only)

-- BEFORE (mixed responsibilities in product schema):
-- product.inventory_financial      ← Inventory concern
-- product.inventory_lifecycle      ← Inventory concern
-- product.inventory_reservation    ← Inventory concern
-- product.inventory_stock          ← Inventory concern
-- product.listing                  ← Sales concern
-- product.order                    ← Sales concern
-- product.size_availability_range  ← Product attribute
-- product.size_profile             ← Product attribute

-- AFTER (clear domain separation):
-- inventory.financial              ← Warehouse team
-- inventory.lifecycle              ← Warehouse team
-- inventory.reservation            ← Warehouse team
-- inventory.stock                  ← Warehouse team
-- sales.listing                    ← Sales team
-- sales.order                      ← Sales team
-- product.size_availability_range  ← Product team
-- product.size_profile             ← Product team

-- ============================================================================
-- MIGRATION STEPS
-- ============================================================================

-- Step 1: Create inventory schema
CREATE SCHEMA IF NOT EXISTS inventory;

-- Step 2: Move inventory tables and remove redundant naming
ALTER TABLE product.inventory_stock SET SCHEMA inventory;
ALTER TABLE inventory.inventory_stock RENAME TO stock;

ALTER TABLE product.inventory_financial SET SCHEMA inventory;
ALTER TABLE inventory.inventory_financial RENAME TO financial;

ALTER TABLE product.inventory_lifecycle SET SCHEMA inventory;
ALTER TABLE inventory.inventory_lifecycle RENAME TO lifecycle;

ALTER TABLE product.inventory_reservation SET SCHEMA inventory;
ALTER TABLE inventory.inventory_reservation RENAME TO reservation;

-- Step 3: Create sales schema
CREATE SCHEMA IF NOT EXISTS sales;

-- Step 4: Move sales tables
ALTER TABLE product.listing SET SCHEMA sales;
ALTER TABLE product.order SET SCHEMA sales;

-- Step 5: Product schema now only contains size-related attributes
-- (size_availability_range and size_profile remain in product schema)

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- After migration, verify:
-- - inventory schema has 4 tables (stock, financial, lifecycle, reservation)
-- - sales schema has 2 tables (listing, order)
-- - product schema has 2 tables (size_availability_range, size_profile)
-- - All 64 tables still present across all schemas
-- - No redundant naming (inventory.inventory_* eliminated)

-- ============================================================================
-- DOMAIN RESPONSIBILITIES
-- ============================================================================

-- INVENTORY Domain (Warehouse/Operations Team)
-- ├── stock          - Physical inventory tracking
-- ├── financial      - Purchase costs, ROI, valuation
-- ├── lifecycle      - Status tracking (received → sold → shipped)
-- └── reservation    - Temporary holds for pending orders

-- SALES Domain (Sales/Marketing Team)
-- ├── listing        - Multi-platform product listings
-- └── order          - Sales order processing

-- PRODUCT Domain (Product/Merchandising Team)
-- ├── size_availability_range  - Available size ranges per product
-- └── size_profile             - Brand-specific size adjustments

-- ============================================================================
-- BUSINESS WORKFLOW EXAMPLE
-- ============================================================================

-- 1. Warehouse Team receives inventory
INSERT INTO inventory.stock (product_id, size_id, quantity_available, location)
VALUES (1, 10, 50, 'Warehouse A');

INSERT INTO inventory.financial (product_id, size_id, purchase_price)
VALUES (1, 10, 120.00);

INSERT INTO inventory.lifecycle (product_id, size_id, received_date, lifecycle_status)
VALUES (1, 10, now(), 'in_stock');

-- 2. Sales Team creates listings
INSERT INTO sales.listing (product_id, platform_id, size_id, listing_price, quantity)
VALUES (1, 1, 10, 180.00, 10);

-- 3. Sales Team processes orders
INSERT INTO sales.order (listing_id, order_number, sale_price, status)
VALUES (1, 'ORD-12345', 175.00, 'pending');

-- 4. Warehouse Team updates inventory
UPDATE inventory.stock
SET quantity_available = quantity_available - 1,
    quantity_sold = quantity_sold + 1
WHERE product_id = 1 AND size_id = 10;

UPDATE inventory.lifecycle
SET sold_date = now(), lifecycle_status = 'sold'
WHERE product_id = 1 AND size_id = 10;

-- ============================================================================
-- BENEFITS
-- ============================================================================

-- ✅ Team Autonomy
--    - Warehouse Team works only with inventory.*
--    - Sales Team works only with sales.*
--    - Product Team works only with product.* and catalog.*

-- ✅ Bounded Contexts (DDD)
--    - Inventory Context: "Do we have stock?"
--    - Sales Context: "Can we sell it?"
--    - Product Context: "What sizes are available?"

-- ✅ Microservices-Ready
--    - Inventory Service → inventory.*
--    - Sales Service → sales.*
--    - Product Service → product.* + catalog.*

-- ✅ Clearer Naming
--    - inventory.stock (not inventory.inventory_stock)
--    - sales.listing (not sales.sales_listing)

-- ============================================================================
-- FINAL SCHEMA COUNT
-- ============================================================================

-- After this migration + previous catalog consolidation:
-- - catalog: 6 tables (brand, category, product, variants, mappings)
-- - inventory: 4 tables (stock, financial, lifecycle, reservation)
-- - sales: 2 tables (listing, order)
-- - product: 2 tables (size_availability_range, size_profile)
-- - core: 6 tables (size_master, supplier, system_*)
-- - supplier: 3 tables (account, purchase_history, settings)
-- - analytics: 9 tables (materialized views)
-- - pricing: 7 tables (rules, forecasts, KPIs)
-- - transaction: 4 tables (transactions, stockx_*)
-- - platform: 4 tables (marketplace, fees, integrations)
-- - financial: 3 tables (snapshots, contracts, ratings)
-- - integration: 4 tables (imports, events, source_prices)
-- - operations: 3 tables (fulfillment, listing_history)
-- - logging: 3 tables (audit, logs)
-- - compliance: 3 tables (rules, permissions, retention)
-- - realtime: 1 table (event_log)
-- TOTAL: 64 tables across 16 schemas

-- ============================================================================
-- NOTE
-- ============================================================================

-- This migration has been applied to the running database.
-- This file documents the changes for:
-- 1. Schema recreation (update init-databases.sql)
-- 2. Alembic migration generation
-- 3. Team onboarding and documentation
