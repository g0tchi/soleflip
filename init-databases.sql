-- Initialize separate databases for each service
-- This script runs automatically when PostgreSQL container starts for the first time

-- Create database for n8n
CREATE DATABASE n8n;

-- Create database for Metabase
CREATE DATABASE metabase;

-- Create database for Memori MCP Server (optional)
CREATE DATABASE memori;

-- Create database for Budibase
CREATE DATABASE budibase;

-- Main soleflip database already created by POSTGRES_DB env var

-- Grant all privileges (user 'soleflip' is created by POSTGRES_USER env var)
GRANT ALL PRIVILEGES ON DATABASE n8n TO soleflip;
GRANT ALL PRIVILEGES ON DATABASE metabase TO soleflip;
GRANT ALL PRIVILEGES ON DATABASE memori TO soleflip;
GRANT ALL PRIVILEGES ON DATABASE budibase TO soleflip;
GRANT ALL PRIVILEGES ON DATABASE soleflip TO soleflip;

-- Optional: Create additional schemas or extensions if needed
\c soleflip;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c n8n;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c metabase;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c memori;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For embeddings (if available)

\c budibase;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
