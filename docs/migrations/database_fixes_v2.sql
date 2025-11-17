-- ============================================================================
-- SoleFlipper Database Fixes (v2 - Corrected)
-- Date: 2025-11-17
-- Purpose: Fix missing Foreign Keys, constraints, and add performance indexes
-- ============================================================================

BEGIN;

-- ============================================================================
-- SECTION 1: CRITICAL - Add Missing Foreign Keys
-- ============================================================================

-- Fix 1: sales.order → inventory.stock FK
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'order_inventory_item_id_fkey'
    ) THEN
        ALTER TABLE sales."order"
        ADD CONSTRAINT order_inventory_item_id_fkey
        FOREIGN KEY (inventory_item_id)
        REFERENCES inventory.stock(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE;
        RAISE NOTICE 'Added FK: sales.order → inventory.stock';
    ELSE
        RAISE NOTICE 'FK order_inventory_item_id_fkey already exists';
    END IF;
END $$;

-- Fix 2: sales.order → platform.marketplace FK
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'order_platform_id_fkey'
    ) THEN
        ALTER TABLE sales."order"
        ADD CONSTRAINT order_platform_id_fkey
        FOREIGN KEY (platform_id)
        REFERENCES platform.marketplace(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE;
        RAISE NOTICE 'Added FK: sales.order → platform.marketplace';
    ELSE
        RAISE NOTICE 'FK order_platform_id_fkey already exists';
    END IF;
END $$;

-- Fix 3: inventory.stock → catalog.product FK
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'inventory'
          AND table_name = 'stock'
          AND column_name = 'product_id'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'stock_product_id_fkey'
        ) THEN
            ALTER TABLE inventory.stock
            ADD CONSTRAINT stock_product_id_fkey
            FOREIGN KEY (product_id)
            REFERENCES catalog.product(id)
            ON DELETE RESTRICT
            ON UPDATE CASCADE;
            RAISE NOTICE 'Added FK: inventory.stock → catalog.product';
        ELSE
            RAISE NOTICE 'FK stock_product_id_fkey already exists';
        END IF;
    ELSE
        RAISE WARNING 'Column inventory.stock.product_id does not exist - skipping FK';
    END IF;
END $$;

-- Fix 4: inventory.stock → catalog.sizes FK
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'inventory'
          AND table_name = 'stock'
          AND column_name = 'size_id'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'stock_size_id_fkey'
        ) THEN
            ALTER TABLE inventory.stock
            ADD CONSTRAINT stock_size_id_fkey
            FOREIGN KEY (size_id)
            REFERENCES catalog.sizes(id)
            ON DELETE RESTRICT
            ON UPDATE CASCADE;
            RAISE NOTICE 'Added FK: inventory.stock → catalog.sizes';
        ELSE
            RAISE NOTICE 'FK stock_size_id_fkey already exists';
        END IF;
    ELSE
        RAISE WARNING 'Column inventory.stock.size_id does not exist - skipping FK';
    END IF;
END $$;

-- ============================================================================
-- SECTION 2: HIGH PRIORITY - Fix Constraints
-- ============================================================================

-- Fix 5: Make sales.order.platform_id NOT NULL
DO $$
DECLARE
    stockx_id UUID;
    null_count INT;
BEGIN
    -- Get StockX platform ID
    SELECT id INTO stockx_id
    FROM platform.marketplace
    WHERE slug = 'stockx'
    LIMIT 1;

    IF stockx_id IS NULL THEN
        RAISE WARNING 'StockX platform not found - cannot set default platform_id';
    ELSE
        -- Count NULL values
        SELECT COUNT(*) INTO null_count
        FROM sales."order"
        WHERE platform_id IS NULL;

        IF null_count > 0 THEN
            -- Update NULL platform_id to StockX
            UPDATE sales."order"
            SET platform_id = stockx_id
            WHERE platform_id IS NULL;
            RAISE NOTICE 'Set platform_id for % orders to StockX (%)', null_count, stockx_id;
        ELSE
            RAISE NOTICE 'No NULL platform_id values found';
        END IF;

        -- Add NOT NULL constraint
        ALTER TABLE sales."order"
        ALTER COLUMN platform_id SET NOT NULL;
        RAISE NOTICE 'Set sales.order.platform_id to NOT NULL';
    END IF;
END $$;

-- Fix 6: Make sales.order.stockx_order_number NULLABLE
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'sales'
          AND table_name = 'order'
          AND column_name = 'stockx_order_number'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE sales."order"
        ALTER COLUMN stockx_order_number DROP NOT NULL;
        RAISE NOTICE 'Set sales.order.stockx_order_number to NULLABLE';
    ELSE
        RAISE NOTICE 'sales.order.stockx_order_number is already NULLABLE';
    END IF;
END $$;

-- ============================================================================
-- SECTION 3: OPTIMIZATION - Add Performance Indexes
-- ============================================================================

-- Fix 7: Partial index for product enrichment - description NULL
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_product_description_null
    ON catalog.product(id)
    WHERE description IS NULL;
    RAISE NOTICE 'Created partial index: idx_product_description_null';
END $$;

-- Fix 8: Partial index for product enrichment - retail_price NULL
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_product_retail_price_null
    ON catalog.product(id)
    WHERE retail_price IS NULL;
    RAISE NOTICE 'Created partial index: idx_product_retail_price_null';
END $$;

-- Fix 9: Partial index for product enrichment - release_date NULL
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_product_release_date_null
    ON catalog.product(id)
    WHERE release_date IS NULL;
    RAISE NOTICE 'Created partial index: idx_product_release_date_null';
END $$;

-- Fix 10: Composite index for enrichment status check
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_product_enrichment_status
    ON catalog.product(id, description, retail_price, release_date)
    WHERE description IS NULL
       OR retail_price IS NULL
       OR release_date IS NULL;
    RAISE NOTICE 'Created composite index: idx_product_enrichment_status';
END $$;

-- ============================================================================
-- SECTION 4: VERIFICATION
-- ============================================================================

-- Verify Foreign Keys
DO $$
DECLARE
    fk_count INT;
BEGIN
    SELECT COUNT(*) INTO fk_count
    FROM pg_constraint
    WHERE contype = 'f'
      AND connamespace = 'sales'::regnamespace
      AND conrelid = 'sales.order'::regclass;
    RAISE NOTICE 'sales.order now has % foreign keys', fk_count;

    IF fk_count < 3 THEN
        RAISE WARNING 'Expected at least 3 FKs on sales.order, found %', fk_count;
    END IF;
END $$;

-- Verify Indexes
DO $$
DECLARE
    idx_count INT;
BEGIN
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE schemaname = 'catalog'
      AND tablename = 'product'
      AND (indexname LIKE '%enrichment%' OR indexname LIKE '%null%');
    RAISE NOTICE 'catalog.product has % enrichment-related indexes', idx_count;
END $$;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '=== Database fixes completed successfully! ===';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. COMMIT this transaction if all looks good';
    RAISE NOTICE '  2. Test order imports (StockX, eBay, GOAT)';
    RAISE NOTICE '  3. Test product enrichment workflow';
    RAISE NOTICE '  4. Verify FK cascade behavior';
    RAISE NOTICE '  5. Update Memori documentation';
END $$;

-- Auto-commit
COMMIT;
