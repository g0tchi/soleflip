-- Check schema issues found during API testing
-- Date: 2025-10-09
-- Issue: Dashboard and Inventory endpoints failing

-- 1. Check if sales.transactions exists (should be transactions.transactions)
SELECT schemaname, tablename
FROM pg_tables
WHERE tablename = 'transactions' OR tablename LIKE '%transaction%'
ORDER BY schemaname, tablename;

-- 2. Check inventory table columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'products' AND table_name = 'inventory'
ORDER BY ordinal_position;

-- 3. Check if sale_overview column exists
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'products'
  AND table_name = 'inventory'
  AND column_name = 'sale_overview';

-- 4. List all schemas
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
ORDER BY schema_name;
