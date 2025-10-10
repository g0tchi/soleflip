-- Fix User Roles - Convert lowercase to uppercase ENUM values
-- Problem: DB has 'admin' but enum expects 'ADMIN'

-- 1. Check current user roles
SELECT id, username, email, role
FROM auth.users;

-- 2. Fix the roles to match enum (ADMIN, USER, READONLY)
UPDATE auth.users
SET role = 'ADMIN'
WHERE role = 'admin';

UPDATE auth.users
SET role = 'USER'
WHERE role = 'user';

UPDATE auth.users
SET role = 'READONLY'
WHERE role = 'readonly';

-- 3. Verify the fix
SELECT id, username, email, role, is_active
FROM auth.users;
