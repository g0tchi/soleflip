-- Create multiple databases for the SoleFlip platform
-- This script runs automatically when PostgreSQL container starts

-- Create databases
CREATE DATABASE soleflip;
CREATE DATABASE metabase;
CREATE DATABASE n8n;
CREATE DATABASE budibase;

-- Create user for each service if needed (optional, using default postgres user)
-- CREATE USER soleflip_user WITH PASSWORD 'soleflip_password';
-- CREATE USER metabase_user WITH PASSWORD 'metabase_password';
-- CREATE USER n8n_user WITH PASSWORD 'n8n_password';
-- CREATE USER budibase_user WITH PASSWORD 'budibase_password';

-- Grant privileges (using default postgres user for simplicity)
-- GRANT ALL PRIVILEGES ON DATABASE soleflip TO postgres;
-- GRANT ALL PRIVILEGES ON DATABASE metabase TO postgres;
-- GRANT ALL PRIVILEGES ON DATABASE n8n TO postgres;
-- GRANT ALL PRIVILEGES ON DATABASE budibase TO postgres;

-- Connect to soleflip database and create extensions
\c soleflip;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Connect to metabase database and create extensions
\c metabase;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Connect to n8n database and create extensions
\c n8n;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Connect to budibase database and create extensions
\c budibase;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";