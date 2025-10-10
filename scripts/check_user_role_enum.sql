-- Check what values the user_role enum actually has in PostgreSQL

-- Method 1: Query the enum type directly
SELECT
    e.enumlabel as enum_value,
    e.enumsortorder as sort_order
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname = 'user_role'
ORDER BY e.enumsortorder;

-- Method 2: Check the actual column type
SELECT
    column_name,
    data_type,
    udt_name,
    udt_schema
FROM information_schema.columns
WHERE table_schema = 'auth'
AND table_name = 'users'
AND column_name = 'role';
