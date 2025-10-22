-- ============================================================================
-- Schema Consolidation Migration
-- Date: 2025-10-21
-- Purpose: Consolidate product catalog tables into catalog schema
-- ============================================================================

-- This migration consolidates the product catalog structure for better
-- Domain-Driven Design following Gibson AI recommendations.

-- BEFORE (problematic structure):
-- core.brand               ← Mixed system and business data
-- core.category            ← Should be in catalog
-- product.product          ← Redundant name (schema = table)
-- catalog.product_variant  ← Already in catalog
-- catalog.product_category_mapping
-- catalog.product_platform_availability

-- AFTER (optimized structure):
-- catalog.brand            ← All catalog master data together
-- catalog.category         ← Clear domain separation
-- catalog.product          ← No redundant naming
-- catalog.product_variant
-- catalog.product_category_mapping
-- catalog.product_platform_availability

-- ============================================================================
-- MIGRATION STEPS
-- ============================================================================

-- 1. Move brand from core to catalog
ALTER TABLE core.brand SET SCHEMA catalog;

-- 2. Move category from core to catalog
ALTER TABLE core.category SET SCHEMA catalog;

-- 3. Move product from product to catalog (fixes redundant naming)
ALTER TABLE product.product SET SCHEMA catalog;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- All foreign keys are automatically updated by PostgreSQL when moving tables
-- between schemas. The following constraints remain valid:

-- catalog.product references:
--   - catalog.brand (brand_id)
--   - catalog.category (category_id)

-- catalog.product_category_mapping references:
--   - catalog.product (product_id)
--   - catalog.category (category_id)

-- catalog.product_platform_availability references:
--   - catalog.product (product_id)
--   - platform.marketplace (platform_id)

-- catalog.product_variant references:
--   - catalog.product (product_id)
--   - core.size_master (size_id)

-- ============================================================================
-- FINAL SCHEMA STRUCTURE
-- ============================================================================

-- CATALOG Schema (6 tables) - All product catalog master data
-- ├── brand                            ← Product brands (Nike, Adidas)
-- ├── category                         ← Product categories
-- ├── product                          ← Main product catalog
-- ├── product_variant                  ← Size/color variants
-- ├── product_category_mapping         ← Product-category links
-- └── product_platform_availability    ← Platform availability

-- CORE Schema (6 tables) - System-level only
-- ├── size_master                      ← Size reference data
-- ├── size_conversion                  ← Size conversions
-- ├── supplier                         ← Supplier master data
-- ├── system_config                    ← System configuration
-- ├── system_event_sourcing            ← Event sourcing
-- └── system_batch_operation           ← Batch operations

-- PRODUCT Schema (8 tables) - Inventory and operations
-- ├── inventory_financial              ← Financial tracking
-- ├── inventory_lifecycle              ← Lifecycle management
-- ├── inventory_reservation            ← Reservations
-- ├── inventory_stock                  ← Stock levels
-- ├── listing                          ← Product listings
-- ├── order                            ← Orders
-- ├── size_availability_range          ← Size availability
-- └── size_profile                     ← Size profiles

-- SUPPLIER Schema (3 tables) - Procurement domain
-- ├── account                          ← Supplier accounts
-- ├── account_purchase_history         ← Purchase history
-- └── account_setting                  ← Account settings

-- ============================================================================
-- BENEFITS
-- ============================================================================

-- ✅ Clearer domain separation (catalog vs core vs product vs supplier)
-- ✅ No redundant naming (catalog.product instead of product.product)
-- ✅ All catalog master data in one schema
-- ✅ Microservices-ready architecture
-- ✅ Better team autonomy (Merchandising vs Sourcing vs Operations)

-- ============================================================================
-- NOTE
-- ============================================================================

-- This migration has already been applied to the running database.
-- This file documents the changes for:
-- 1. Schema recreation (init-databases.sql update)
-- 2. Alembic migration generation
-- 3. Documentation purposes
