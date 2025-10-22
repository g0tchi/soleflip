-- ============================================================================
-- Supplier Domain Consolidation Migration v2.3.4
-- Date: 2025-10-21
-- Purpose: Consolidate all supplier-related data into supplier domain
-- ============================================================================

-- This migration consolidates all supplier-related data that was scattered
-- across core, supplier, and financial schemas into a single cohesive
-- supplier domain following DDD bounded context principles.

-- BEFORE (scattered across multiple schemas):
-- core.supplier                    ← Supplier master data (wrong location)
-- supplier.account                 ← Login data
-- supplier.account_purchase_history ← Purchase history (redundant prefix)
-- supplier.account_setting         ← Settings (redundant prefix)
-- financial.supplier_contract      ← Contracts (wrong domain)
-- financial.supplier_rating_history ← Ratings (wrong domain)

-- AFTER (consolidated supplier domain):
-- supplier.profile                 ← Supplier master data (clear name)
-- supplier.account                 ← Login data, payment info
-- supplier.purchase_history        ← Purchase history (no redundant prefix)
-- supplier.setting                 ← Settings (no redundant prefix)
-- supplier.contract                ← Contract terms
-- supplier.rating_history          ← Performance tracking

-- ============================================================================
-- KEY DESIGN PRINCIPLES
-- ============================================================================

-- 1. BOUNDED CONTEXT
--    All supplier-related concerns belong in one domain
--    Sourcing team owns and manages everything supplier-related

-- 2. CLEAR NAMING
--    supplier.profile (not supplier.supplier - avoids redundancy)
--    supplier.purchase_history (not account_purchase_history)
--    supplier.contract (schema provides context, not "supplier_" prefix)

-- 3. DOMAIN OWNERSHIP
--    Supplier domain = Procurement/Sourcing concerns
--    Financial domain = Only financial settlement/transactions

-- ============================================================================
-- MIGRATION STEPS
-- ============================================================================

-- Step 1: Move supplier master data from core to supplier
ALTER TABLE core.supplier SET SCHEMA supplier;
ALTER TABLE supplier.supplier RENAME TO profile;

-- Step 2: Remove redundant "account_" prefixes
ALTER TABLE supplier.account_purchase_history RENAME TO purchase_history;
ALTER TABLE supplier.account_setting RENAME TO setting;

-- Step 3: Move supplier contracts from financial to supplier
ALTER TABLE financial.supplier_contract SET SCHEMA supplier;
ALTER TABLE supplier.supplier_contract RENAME TO contract;

-- Step 4: Move supplier ratings from financial to supplier
ALTER TABLE financial.supplier_rating_history SET SCHEMA supplier;
ALTER TABLE supplier.supplier_rating_history RENAME TO rating_history;

-- Foreign keys are automatically updated by PostgreSQL

-- ============================================================================
-- SUPPLIER DOMAIN STRUCTURE
-- ============================================================================

-- supplier.profile (6 tables total)
-- ├── profile           - Supplier master data (name, contact, location)
-- ├── account           - Login credentials, payment info
-- ├── purchase_history  - Historical purchases from supplier
-- ├── setting           - Supplier-specific settings (auto-order, etc.)
-- ├── contract          - Contract terms, payment conditions
-- └── rating_history    - Performance metrics over time

-- ============================================================================
-- SOURCING TEAM WORKFLOW
-- ============================================================================

-- Example: Complete supplier management in one domain

-- 1. Create supplier profile
INSERT INTO supplier.profile (name, email, phone)
VALUES ('Footlocker Munich', 'buyer@footlocker.de', '+49-89-1234567');

-- 2. Set up account credentials
INSERT INTO supplier.account (supplier_id, login_url, username)
VALUES (1, 'https://b2b.footlocker.com', 'soleflip_buyer');

-- 3. Configure settings
INSERT INTO supplier.setting (supplier_id, auto_order_enabled, min_order_quantity)
VALUES (1, true, 10);

-- 4. Record contract
INSERT INTO supplier.contract (supplier_id, payment_terms, discount_percentage)
VALUES (1, 'NET30', 5.0);

-- 5. Track performance
INSERT INTO supplier.rating_history (supplier_id, quality_rating, delivery_rating)
VALUES (1, 4.5, 4.8);

-- 6. Record purchase
INSERT INTO supplier.purchase_history (supplier_id, product_id, quantity, unit_price)
VALUES (1, 1, 50, 120.00);

-- ============================================================================
-- SINGLE-DOMAIN QUERIES
-- ============================================================================

-- All supplier data accessible from one schema:

-- Supplier overview with all related data
SELECT
    p.name as supplier_name,
    p.email,
    a.login_url,
    s.auto_order_enabled,
    c.payment_terms,
    c.discount_percentage,
    r.quality_rating,
    r.delivery_rating
FROM supplier.profile p
LEFT JOIN supplier.account a ON p.id = a.supplier_id
LEFT JOIN supplier.setting s ON p.id = s.supplier_id
LEFT JOIN supplier.contract c ON p.id = c.supplier_id
LEFT JOIN supplier.rating_history r ON p.id = r.supplier_id
WHERE p.id = 1;

-- Purchase analysis
SELECT
    p.name as supplier,
    COUNT(ph.id) as total_purchases,
    SUM(ph.quantity * ph.unit_price) as total_spent,
    AVG(ph.unit_price) as avg_unit_price
FROM supplier.profile p
JOIN supplier.purchase_history ph ON p.id = ph.supplier_id
GROUP BY p.name
ORDER BY total_spent DESC;

-- Top-rated suppliers
SELECT
    p.name,
    AVG(r.quality_rating) as avg_quality,
    AVG(r.delivery_rating) as avg_delivery,
    c.discount_percentage
FROM supplier.profile p
JOIN supplier.rating_history r ON p.id = r.supplier_id
JOIN supplier.contract c ON p.id = c.supplier_id
GROUP BY p.name, c.discount_percentage
HAVING AVG(r.quality_rating) >= 4.0
ORDER BY avg_quality DESC, avg_delivery DESC;

-- ============================================================================
-- BENEFITS OF CONSOLIDATION
-- ============================================================================

-- ✅ Single Source of Truth
--    All supplier data in one domain - no confusion

-- ✅ Team Autonomy
--    Sourcing team owns and manages all supplier concerns

-- ✅ Clearer Naming
--    No redundant prefixes (supplier.profile not supplier.supplier)
--    Schema provides context (purchase_history not account_purchase_history)

-- ✅ Simpler Queries
--    No cross-schema joins (everything in supplier.*)

-- ✅ Microservices-Ready
--    Supplier Service can manage all supplier.* tables independently

-- ✅ Domain-Driven Design
--    Follows bounded context principle - one aggregate for supplier

-- ============================================================================
-- SCHEMA COUNTS AFTER MIGRATION
-- ============================================================================

-- supplier: 6 tables (↑ from 3)
-- core: 5 tables (↓ from 6 - removed supplier)
-- financial: 2 tables (↓ from 4 - removed supplier_*)
-- Total: 62 tables (no change)

-- ============================================================================
-- FINAL DOMAIN STRUCTURE
-- ============================================================================

-- CATALOG Domain (6 tables) - Product catalog
-- INVENTORY Domain (4 tables) - Stock management
-- SALES Domain (3 tables) - Multi-platform sales
-- SUPPLIER Domain (6 tables) - Procurement & sourcing ← CONSOLIDATED
-- FINANCIAL Domain (2 tables) - Financial settlement (cleaned up)
-- PRODUCT Domain (2 tables) - Size attributes
-- CORE Domain (5 tables) - System infrastructure (cleaned up)
-- PLATFORM Domain (4 tables) - Marketplace management
-- + 9 additional specialized domains

-- ============================================================================
-- NOTE
-- ============================================================================

-- This migration has been applied to the running database.
-- This file documents the changes for:
-- 1. Schema recreation (update init-databases.sql)
-- 2. Alembic migration generation
-- 3. Team onboarding (Sourcing team documentation)
