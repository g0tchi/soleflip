-- ============================================================================
-- Phase 2: Inventory Schema Consolidation (FIXED)
-- ============================================================================
-- Generated: 2025-11-29
-- Source: Gibson AI Analysis + Phase 1 Learnings
-- Priority: HIGH
-- Risk: MEDIUM (requires careful data migration)
-- Expected Impact: 60-80% performance improvement on inventory queries
-- ============================================================================

-- IMPORTANT: Run this script in a transaction for safety
-- Test in development/staging first!

BEGIN;

-- ============================================================================
-- PART 1: Pre-Migration Validation
-- ============================================================================

-- Validate current state
DO $$
DECLARE
  stock_count INTEGER;
  financial_count INTEGER;
  lifecycle_count INTEGER;
  metrics_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO stock_count FROM inventory.stock;
  SELECT COUNT(*) INTO financial_count FROM inventory.stock_financial;
  SELECT COUNT(*) INTO lifecycle_count FROM inventory.stock_lifecycle;
  SELECT COUNT(*) INTO metrics_count FROM inventory.stock_metrics;

  RAISE NOTICE 'Pre-migration counts:';
  RAISE NOTICE '  stock: %', stock_count;
  RAISE NOTICE '  stock_financial: %', financial_count;
  RAISE NOTICE '  stock_lifecycle: %', lifecycle_count;
  RAISE NOTICE '  stock_metrics: %', metrics_count;

  -- Validation: check for orphaned records
  IF EXISTS (
    SELECT 1 FROM inventory.stock_financial sf
    WHERE NOT EXISTS (SELECT 1 FROM inventory.stock s WHERE s.id = sf.stock_id)
  ) THEN
    RAISE WARNING 'Found orphaned records in stock_financial!';
  END IF;

  IF EXISTS (
    SELECT 1 FROM inventory.stock_lifecycle sl
    WHERE NOT EXISTS (SELECT 1 FROM inventory.stock s WHERE s.id = sl.stock_id)
  ) THEN
    RAISE WARNING 'Found orphaned records in stock_lifecycle!';
  END IF;
END $$;

-- ============================================================================
-- PART 2: Add New Columns to inventory.stock
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Adding new columns to inventory.stock...';
END $$;

-- From stock_lifecycle (unique fields)
ALTER TABLE inventory.stock
  ADD COLUMN IF NOT EXISTS listed_on_platforms JSONB,
  ADD COLUMN IF NOT EXISTS status_history JSONB;

-- From stock_metrics (essential field)
ALTER TABLE inventory.stock
  ADD COLUMN IF NOT EXISTS reserved_quantity INTEGER DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN inventory.stock.listed_on_platforms IS 'Platform listing history (from stock_lifecycle)';
COMMENT ON COLUMN inventory.stock.status_history IS 'Status change tracking (from stock_lifecycle)';
COMMENT ON COLUMN inventory.stock.reserved_quantity IS 'Currently reserved units (from stock_metrics)';

DO $$ BEGIN
  RAISE NOTICE 'New columns added successfully';
END $$;

-- ============================================================================
-- PART 3: Create Indexes on New Columns
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Creating indexes on new columns...';
END $$;

-- Reserved quantity index (enable Phase 1 commented index)
CREATE INDEX IF NOT EXISTS idx_stock_reserved
ON inventory.stock (id, reserved_quantity)
WHERE reserved_quantity > 0;

-- JSONB indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_stock_listed_platforms
ON inventory.stock USING GIN (listed_on_platforms)
WHERE listed_on_platforms IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_stock_status_history
ON inventory.stock USING GIN (status_history)
WHERE status_history IS NOT NULL;

DO $$ BEGIN
  RAISE NOTICE 'Indexes created successfully';
END $$;

-- ============================================================================
-- PART 4: Backfill Data from Old Tables
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Backfilling data from stock_lifecycle...';
END $$;

-- Migrate stock_lifecycle data
UPDATE inventory.stock s
SET
  listed_on_platforms = sl.listed_on_platforms,
  status_history = sl.status_history
FROM inventory.stock_lifecycle sl
WHERE s.id = sl.stock_id;

-- Report migration stats
DO $$
DECLARE
  migrated_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO migrated_count
  FROM inventory.stock
  WHERE listed_on_platforms IS NOT NULL OR status_history IS NOT NULL;

  RAISE NOTICE 'Migrated lifecycle data for % records', migrated_count;
END $$;

DO $$ BEGIN
  RAISE NOTICE 'Backfilling data from stock_metrics...';
END $$;

-- Migrate stock_metrics reserved_quantity
UPDATE inventory.stock s
SET reserved_quantity = COALESCE(sm.reserved_quantity, 0)
FROM inventory.stock_metrics sm
WHERE s.id = sm.stock_id;

-- Report reservation stats
DO $$
DECLARE
  reserved_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO reserved_count
  FROM inventory.stock
  WHERE reserved_quantity > 0;

  RAISE NOTICE 'Found % records with reservations', reserved_count;
END $$;

-- ============================================================================
-- PART 5: Create Materialized View for Stock Metrics
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Creating stock_metrics materialized view...';
END $$;

-- Drop view if exists (for re-running script)
DROP MATERIALIZED VIEW IF EXISTS inventory.stock_metrics_view CASCADE;

-- Create materialized view (replaces stock_metrics table)
CREATE MATERIALIZED VIEW inventory.stock_metrics_view AS
SELECT
  s.id as stock_id,
  s.quantity as total_quantity,
  s.quantity - COALESCE(s.reserved_quantity, 0) as available_quantity,
  s.reserved_quantity,
  s.gross_purchase_price as total_cost,
  -- Expected profit calculation
  CASE
    WHEN s.roi_percentage IS NOT NULL AND s.roi_percentage > 0
    THEN s.gross_purchase_price * (s.roi_percentage / 100)
    ELSE NULL
  END as expected_profit,
  now() as last_calculated_at,
  s.created_at,
  s.updated_at
FROM inventory.stock s;

-- Create unique index for fast lookups
CREATE UNIQUE INDEX idx_stock_metrics_view_stock_id
ON inventory.stock_metrics_view (stock_id);

-- Create additional indexes
CREATE INDEX idx_stock_metrics_view_available
ON inventory.stock_metrics_view (available_quantity)
WHERE available_quantity > 0;

DO $$ BEGIN
  RAISE NOTICE 'Materialized view created successfully';
END $$;

-- ============================================================================
-- PART 6: Create Refresh Function
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Creating refresh function...';
END $$;

-- Function to refresh stock metrics view
CREATE OR REPLACE FUNCTION inventory.refresh_stock_metrics()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY inventory.stock_metrics_view;
  RAISE NOTICE 'Stock metrics view refreshed at %', now();
END;
$$;

COMMENT ON FUNCTION inventory.refresh_stock_metrics() IS
  'Refreshes the stock_metrics materialized view. Schedule to run hourly.';

-- Initial refresh
SELECT inventory.refresh_stock_metrics();

-- ============================================================================
-- PART 7: Data Integrity Validation
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Validating data integrity...';
END $$;

DO $$
DECLARE
  stock_count INTEGER;
  migrated_lifecycle INTEGER;
  migrated_metrics INTEGER;
  has_reservations INTEGER;
  view_count INTEGER;
BEGIN
  -- Count records
  SELECT COUNT(*) INTO stock_count FROM inventory.stock;
  SELECT COUNT(*) INTO migrated_lifecycle
    FROM inventory.stock
    WHERE listed_on_platforms IS NOT NULL OR status_history IS NOT NULL;
  SELECT COUNT(*) INTO migrated_metrics
    FROM inventory.stock
    WHERE reserved_quantity IS NOT NULL;
  SELECT COUNT(*) INTO has_reservations
    FROM inventory.stock
    WHERE reserved_quantity > 0;
  SELECT COUNT(*) INTO view_count FROM inventory.stock_metrics_view;

  RAISE NOTICE 'Data validation results:';
  RAISE NOTICE '  Total stock records: %', stock_count;
  RAISE NOTICE '  Migrated lifecycle data: %', migrated_lifecycle;
  RAISE NOTICE '  Migrated metrics data: %', migrated_metrics;
  RAISE NOTICE '  Records with reservations: %', has_reservations;
  RAISE NOTICE '  Materialized view records: %', view_count;

  -- Validation checks
  IF view_count != stock_count THEN
    RAISE WARNING 'View count (%) does not match stock count (%)!', view_count, stock_count;
  ELSE
    RAISE NOTICE '✓ View count matches stock count';
  END IF;

  -- Check for data consistency
  IF EXISTS (
    SELECT 1 FROM inventory.stock s
    JOIN inventory.stock_financial sf ON s.id = sf.stock_id
    WHERE s.purchase_price IS DISTINCT FROM sf.purchase_price
       OR s.gross_purchase_price IS DISTINCT FROM sf.gross_purchase_price
  ) THEN
    RAISE WARNING 'Found inconsistent financial data between stock and stock_financial!';
  ELSE
    RAISE NOTICE '✓ Financial data consistent';
  END IF;
END $$;

-- ============================================================================
-- PART 8: Create Backup Tables (Safety Net)
-- ============================================================================

DO $$ BEGIN
  RAISE NOTICE 'Creating backup tables...';
END $$;

-- Backup old tables before dropping (in Part 10)
CREATE TABLE IF NOT EXISTS inventory.stock_financial_backup AS
SELECT * FROM inventory.stock_financial;

CREATE TABLE IF NOT EXISTS inventory.stock_lifecycle_backup AS
SELECT * FROM inventory.stock_lifecycle;

CREATE TABLE IF NOT EXISTS inventory.stock_metrics_backup AS
SELECT * FROM inventory.stock_metrics;

DO $$
DECLARE
  fin_count INTEGER;
  life_count INTEGER;
  met_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO fin_count FROM inventory.stock_financial_backup;
  SELECT COUNT(*) INTO life_count FROM inventory.stock_lifecycle_backup;
  SELECT COUNT(*) INTO met_count FROM inventory.stock_metrics_backup;
  
  RAISE NOTICE 'Backup tables created';
  RAISE NOTICE '  stock_financial_backup: % rows', fin_count;
  RAISE NOTICE '  stock_lifecycle_backup: % rows', life_count;
  RAISE NOTICE '  stock_metrics_backup: % rows', met_count;
END $$;

-- ============================================================================
-- FINAL VALIDATION
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '==================================================================';
  RAISE NOTICE 'Phase 2 Migration Complete!';
  RAISE NOTICE '==================================================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Update application code (see phase2-code-migration-guide.md)';
  RAISE NOTICE '2. Run comprehensive tests';
  RAISE NOTICE '3. Monitor performance improvements';
  RAISE NOTICE '4. After 2 weeks: Drop old tables if everything is stable';
  RAISE NOTICE '';
  RAISE NOTICE 'Expected improvements:';
  RAISE NOTICE '  - Inventory queries: 60-80%% faster';
  RAISE NOTICE '  - Eliminated 3 unnecessary JOINs';
  RAISE NOTICE '  - Simplified codebase';
  RAISE NOTICE '';
  RAISE NOTICE 'IMPORTANT: Old tables NOT dropped automatically';
  RAISE NOTICE 'Verify everything works correctly before dropping old tables';
  RAISE NOTICE '';
  RAISE NOTICE 'To drop old tables after verification, run:';
  RAISE NOTICE '  DROP TABLE inventory.stock_financial CASCADE;';
  RAISE NOTICE '  DROP TABLE inventory.stock_lifecycle CASCADE;';
  RAISE NOTICE '  DROP TABLE inventory.stock_metrics CASCADE;';
END $$;

COMMIT;
