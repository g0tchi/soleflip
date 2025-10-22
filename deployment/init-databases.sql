-- Initialize separate databases for each service
-- This script runs automatically when PostgreSQL container starts for the first time

-- Create database for n8n
CREATE DATABASE n8n;

-- Create database for Metabase
CREATE DATABASE metabase;

-- Main soleflip database already created by POSTGRES_DB env var

-- Grant all privileges (user 'soleflip' is created by POSTGRES_USER env var)
GRANT ALL PRIVILEGES ON DATABASE n8n TO soleflip;
GRANT ALL PRIVILEGES ON DATABASE metabase TO soleflip;
GRANT ALL PRIVILEGES ON DATABASE soleflip TO soleflip;

-- Connect to soleflip database and set up schemas and extensions
\c soleflip;

-- Create PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Domain-Driven Design Schema Structure (based on Gibson AI project modules)
-- Core business domains
CREATE SCHEMA IF NOT EXISTS core;           -- Brands, Categories, Sizes, Suppliers, System Config
CREATE SCHEMA IF NOT EXISTS product;        -- Products, Inventory, Listings, Orders, Stock Management
CREATE SCHEMA IF NOT EXISTS catalog;        -- Product Variants, Category Mapping, Platform Availability
CREATE SCHEMA IF NOT EXISTS pricing;        -- Price Rules, Market Prices, Forecasts, KPIs
CREATE SCHEMA IF NOT EXISTS supplier;       -- Supplier Accounts, Purchases, Settings
CREATE SCHEMA IF NOT EXISTS platform;       -- Marketplaces, Integrations, Fees, Size Display

-- Transaction and operations
CREATE SCHEMA IF NOT EXISTS transaction;    -- Orders, Transactions, StockX Listings/Orders
CREATE SCHEMA IF NOT EXISTS operations;     -- Fulfillment, Listing History, Platform Integration
CREATE SCHEMA IF NOT EXISTS financial;      -- Price Snapshots, Contracts, Ratings

-- Analytics and reporting
CREATE SCHEMA IF NOT EXISTS analytics;      -- Sales Summary, Performance, Profitability Analysis
CREATE SCHEMA IF NOT EXISTS realtime;       -- Real-time Event Logs

-- Integration and data management
CREATE SCHEMA IF NOT EXISTS integration;    -- Import Batches, Event Store, Source Prices
CREATE SCHEMA IF NOT EXISTS logging;        -- Audit Trail, System Logs, StockX Presale Marking

-- Compliance and security
CREATE SCHEMA IF NOT EXISTS compliance;     -- Business Rules, Retention Policies, Permissions

-- Legacy/additional schemas (for backward compatibility with existing Alembic migrations)
CREATE SCHEMA IF NOT EXISTS auth;           -- User authentication
CREATE SCHEMA IF NOT EXISTS inventory;      -- Inventory management
CREATE SCHEMA IF NOT EXISTS sales;          -- Sales tracking
CREATE SCHEMA IF NOT EXISTS platforms;      -- Platform-specific data
CREATE SCHEMA IF NOT EXISTS orders;         -- Order processing
CREATE SCHEMA IF NOT EXISTS forecasting;    -- Forecasting models

-- Grant schema usage permissions to soleflip user
GRANT USAGE ON SCHEMA core TO soleflip;
GRANT USAGE ON SCHEMA product TO soleflip;
GRANT USAGE ON SCHEMA catalog TO soleflip;
GRANT USAGE ON SCHEMA pricing TO soleflip;
GRANT USAGE ON SCHEMA supplier TO soleflip;
GRANT USAGE ON SCHEMA platform TO soleflip;
GRANT USAGE ON SCHEMA transaction TO soleflip;
GRANT USAGE ON SCHEMA operations TO soleflip;
GRANT USAGE ON SCHEMA financial TO soleflip;
GRANT USAGE ON SCHEMA analytics TO soleflip;
GRANT USAGE ON SCHEMA realtime TO soleflip;
GRANT USAGE ON SCHEMA integration TO soleflip;
GRANT USAGE ON SCHEMA logging TO soleflip;
GRANT USAGE ON SCHEMA compliance TO soleflip;
GRANT USAGE ON SCHEMA auth TO soleflip;
GRANT USAGE ON SCHEMA inventory TO soleflip;
GRANT USAGE ON SCHEMA sales TO soleflip;
GRANT USAGE ON SCHEMA platforms TO soleflip;
GRANT USAGE ON SCHEMA orders TO soleflip;
GRANT USAGE ON SCHEMA forecasting TO soleflip;

-- Grant all privileges on all tables in schemas (for future tables)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA product TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA catalog TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA pricing TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA supplier TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA platform TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA transaction TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA operations TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA financial TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA realtime TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA integration TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA logging TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA compliance TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA inventory TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sales TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA platforms TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA orders TO soleflip;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA forecasting TO soleflip;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA product GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA catalog GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA pricing GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA supplier GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA transaction GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA operations GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA financial GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA realtime GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA integration GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA logging GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA compliance GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA inventory GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA platforms GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA orders GRANT ALL ON TABLES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA forecasting GRANT ALL ON TABLES TO soleflip;

-- Set default privileges for sequences (for auto-increment support)
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA product GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA catalog GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA pricing GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA supplier GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA transaction GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA operations GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA financial GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA realtime GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA integration GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA logging GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA compliance GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA inventory GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA platforms GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA orders GRANT ALL ON SEQUENCES TO soleflip;
ALTER DEFAULT PRIVILEGES IN SCHEMA forecasting GRANT ALL ON SEQUENCES TO soleflip;

-- Set up n8n database
\c n8n;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set up Metabase database
\c metabase;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
