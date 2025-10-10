-- Create Test User with known password
-- Password: test123
-- BCrypt hash generated for "test123"

-- Delete test user if exists
DELETE FROM auth.users WHERE username = 'testuser';

-- Insert test user
-- Password is: test123
INSERT INTO auth.users (id, email, username, hashed_password, role, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'test@soleflip.local',
    'testuser',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxKzQc3jG',  -- test123
    'admin',
    true,
    NOW(),
    NOW()
);

-- Verify
SELECT id, username, email, role, is_active, created_at
FROM auth.users
WHERE username = 'testuser';
