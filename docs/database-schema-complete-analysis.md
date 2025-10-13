# Complete Database Schema Analysis

**Generated:** 2025-10-12
**Purpose:** Comprehensive analysis of all migration files to understand complete database structure
**Migration Files Analyzed:** 26 files from initial schema (2025-08-14) to price sources (2025-10-12)

---

## Executive Summary

The SoleFlip database uses PostgreSQL with a **multi-schema architecture** following Domain-Driven Design principles. The schema has evolved through 26 migrations, creating a sophisticated system for sneaker resale business operations.

**Total Schemas:** 7 (core, products, integration, transactions, pricing, analytics, auth, platforms)
**Total Tables:** 35+ tables
**Key Features:** StockX integration, multi-platform orders, Awin product feed, price sources unification, supplier accounts

---

## 1. Schemas Overview

### 1.1 Core Schema (`core`)
**Purpose:** Master data and reference tables for business entities

**Tables:**
- `suppliers` - Supplier/retailer master data
- `brands` - Brand catalog
- `categories` - Product categories
- `platforms` - Sales platforms (StockX, eBay, GOAT, etc.)
- `brand_patterns` - Brand identification patterns
- `supplier_accounts` - Supplier account credentials
- `account_purchase_history` - Purchase tracking per account
- `supplier_performance` - Monthly supplier KPIs
- `supplier_history` - Historical supplier events

### 1.2 Products Schema (`products`)
**Purpose:** Product catalog and inventory management

**Tables:**
- `products` - Product master data with enrichment fields
- `inventory` - Inventory items with financial tracking
- `sizes` - Size catalog (no schema prefix)

### 1.3 Integration Schema (`integration`)
**Purpose:** External data sources and integrations

**Tables:**
- `import_batches` - Import job tracking
- `import_records` - Individual import records
- `market_prices` - External market price data (legacy)
- `awin_products` - Awin affiliate feed products
- `awin_price_history` - Awin price changes
- `awin_enrichment_jobs` - Enrichment job tracking
- `price_sources` - **NEW:** Unified price data from all sources
- `price_history` - **NEW:** Historical price tracking

### 1.4 Transactions Schema (`transactions`)
**Purpose:** Order and transaction processing

**Tables:**
- `transactions` - Legacy transaction records (being phased out)
- `orders` - **Multi-platform orders** (replaces transactions)

### 1.5 Pricing Schema (`pricing`)
**Purpose:** Pricing rules and market data

**Tables:**
- `price_rules` - Pricing logic configurations
- `brand_multipliers` - Brand-specific adjustments
- `price_history` - Historical price tracking (pricing context)
- `market_prices` - External market prices (pricing context)

### 1.6 Analytics Schema (`analytics`)
**Purpose:** Business intelligence and forecasting

**Tables:**
- `sales_forecasts` - Predictive sales data
- `forecast_accuracy` - Model performance tracking
- `demand_patterns` - Historical demand analysis
- `pricing_kpis` - Key performance indicators
- `marketplace_data` - Marketplace listing data

### 1.7 Auth Schema (`auth`)
**Purpose:** Authentication and authorization

**Tables:**
- `users` - User accounts with roles

### 1.8 Platforms Schema (`platforms`)
**Purpose:** Platform-specific integrations (formerly `selling`)

**Tables:**
- `stockx_listings` - StockX active listings
- `stockx_orders` - StockX order details
- `pricing_history` - StockX listing price changes

### 1.9 Public Schema (no prefix)
**Purpose:** System-level and shared tables

**Tables:**
- `system_config` - System configuration (encrypted)
- `system_logs` - Application logs
- `sizes` - Global size catalog

---

## 2. Detailed Table Structures

### 2.1 Core Schema Tables

#### `core.suppliers`
**Purpose:** Master supplier/retailer data

**Columns:**
- `id` UUID PRIMARY KEY
- `name` VARCHAR(100) NOT NULL
- `slug` VARCHAR(100) UNIQUE NOT NULL
- `display_name` VARCHAR(150)
- `supplier_type` VARCHAR(50) NOT NULL
- `business_size` VARCHAR(30)
- Contact: `contact_person`, `email`, `phone`, `website`
- Address: `address_line1`, `address_line2`, `city`, `state_province`, `postal_code`, `country`
- Tax: `tax_id`, `vat_number`, `business_registration`
- Return Policy: `return_policy_days`, `return_policy_text`, `return_conditions`, `accepts_exchanges`, `restocking_fee_percent`
- Payment: `payment_terms`, `credit_limit`, `discount_percent`, `minimum_order_amount`
- Ratings: `rating`, `reliability_score`, `quality_score`
- Status: `status` VARCHAR(20) NOT NULL, `preferred`, `verified`
- Shipping: `average_processing_days`, `ships_internationally`, `accepts_returns_by_mail`, `provides_authenticity_guarantee`
- API: `has_api`, `api_endpoint`, `api_key_encrypted` TEXT
- Stats: `total_orders_count`, `total_order_value`, `average_order_value`, `last_order_date`
- Meta: `notes` TEXT, `internal_notes` TEXT, `tags` JSONB
- **NEW** (Supplier History): `founded_year` INTEGER, `founder_name` VARCHAR(200), `instagram_handle`, `instagram_url`, `facebook_url`, `twitter_handle`, `logo_url`, `supplier_story` TEXT, `closure_date` DATE, `closure_reason` TEXT
- **NEW** (Supplier Intelligence): `supplier_category` VARCHAR(50), `vat_rate` DECIMAL(4,2), `return_policy` TEXT, `default_email` VARCHAR(255)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_suppliers_instagram` ON `instagram_handle`
- `idx_suppliers_founded_year` ON `founded_year`

**Relationships:**
- Referenced by: `products.inventory`, `integration.price_sources`, `core.supplier_accounts`, `core.account_purchase_history`, `core.supplier_performance`, `core.supplier_history`

---

#### `core.brands`
**Purpose:** Brand catalog

**Columns:**
- `id` UUID PRIMARY KEY
- `name` VARCHAR(100) NOT NULL
- `slug` VARCHAR(100) UNIQUE NOT NULL
- Timestamps: `created_at`, `updated_at`

**Relationships:**
- Referenced by: `products.products`, `pricing.price_rules`, `pricing.brand_multipliers`, `analytics.*`

---

#### `core.categories`
**Purpose:** Product categories

**Columns:**
- `id` UUID PRIMARY KEY
- `name` VARCHAR(100) NOT NULL
- `slug` VARCHAR(100) UNIQUE NOT NULL
- Timestamps: `created_at`, `updated_at`

**Relationships:**
- Referenced by: `products.products`, `sizes`, `pricing.price_rules`, `analytics.*`

---

#### `core.platforms`
**Purpose:** Sales platforms (StockX, eBay, GOAT, etc.)

**Columns:**
- `id` UUID PRIMARY KEY
- `name` VARCHAR(100) NOT NULL
- `slug` VARCHAR(100) UNIQUE NOT NULL
- Timestamps: `created_at`, `updated_at`

**Relationships:**
- Referenced by: `transactions.transactions`, `transactions.orders`, `analytics.marketplace_data`, `pricing.price_rules`

---

#### `core.brand_patterns`
**Purpose:** Brand identification patterns for auto-detection

**Columns:**
- `id` UUID PRIMARY KEY
- `brand_id` UUID NOT NULL FK → `core.brands.id`
- `pattern_type` VARCHAR(50) NOT NULL
- `pattern` VARCHAR(255) UNIQUE NOT NULL
- `priority` INTEGER NOT NULL
- Timestamps: `created_at`, `updated_at`

**Relationships:**
- FK: `brand_id` → `core.brands.id`

---

#### `core.supplier_accounts`
**Purpose:** Supplier account credentials for automated purchasing

**Columns:**
- `id` UUID PRIMARY KEY
- `supplier_id` UUID NOT NULL FK → `core.suppliers.id` (CASCADE)
- `email` VARCHAR(150) NOT NULL
- `password_hash` TEXT
- `proxy_config` TEXT
- Personal Info: `first_name`, `last_name`
- Address: `address_line_1`, `address_line_2`, `city`, `country_code`, `zip_code`, `state_code`, `phone_number`
- **REMOVED (PCI Compliance):** ~~`cc_number_encrypted`, `cvv_encrypted`~~
- **NEW (PCI Compliant):** `payment_provider` VARCHAR(50), `payment_method_token` VARCHAR(255), `payment_method_last4` VARCHAR(4), `payment_method_brand` VARCHAR(20)
- Payment (Metadata): `expiry_month` INTEGER, `expiry_year` INTEGER
- Preferences: `browser_preference` VARCHAR(50), `list_name` VARCHAR(100)
- Status: `account_status` VARCHAR(30) DEFAULT 'active', `is_verified` BOOLEAN DEFAULT false
- Stats: `last_used_at` TIMESTAMP, `total_purchases` INTEGER DEFAULT 0, `total_spent` DECIMAL(12,2) DEFAULT 0, `success_rate` DECIMAL(5,2) DEFAULT 0, `average_order_value` DECIMAL(10,2) DEFAULT 0
- Meta: `notes` TEXT
- Timestamps: `created_at`, `updated_at`

**Constraints:**
- UNIQUE (`supplier_id`, `email`)

**Indexes:**
- `idx_supplier_accounts_supplier_id` ON `supplier_id`
- `idx_supplier_accounts_email` ON `email`
- `idx_supplier_accounts_status` ON `account_status`
- `idx_supplier_accounts_last_used` ON `last_used_at`

**Relationships:**
- FK: `supplier_id` → `core.suppliers.id` (CASCADE)
- Referenced by: `core.account_purchase_history`

---

#### `core.account_purchase_history`
**Purpose:** Track purchases made through supplier accounts

**Columns:**
- `id` UUID PRIMARY KEY
- `account_id` UUID NOT NULL FK → `core.supplier_accounts.id` (CASCADE)
- `supplier_id` UUID NOT NULL FK → `core.suppliers.id` (CASCADE)
- `product_id` UUID FK → `products.products.id` (SET NULL)
- `order_reference` VARCHAR(100)
- `purchase_amount` DECIMAL(12,2) NOT NULL
- `purchase_date` TIMESTAMP NOT NULL
- `purchase_status` VARCHAR(30) NOT NULL
- `success` BOOLEAN DEFAULT false
- `failure_reason` TEXT
- `response_time_ms` INTEGER
- `ip_address` VARCHAR(45)
- `user_agent` VARCHAR(500)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_purchase_history_account_id` ON `account_id`
- `idx_purchase_history_supplier_id` ON `supplier_id`
- `idx_purchase_history_date` ON `purchase_date`
- `idx_purchase_history_status` ON `purchase_status`

**Relationships:**
- FK: `account_id` → `core.supplier_accounts.id` (CASCADE)
- FK: `supplier_id` → `core.suppliers.id` (CASCADE)
- FK: `product_id` → `products.products.id` (SET NULL)

---

#### `core.supplier_performance`
**Purpose:** Monthly supplier performance KPIs

**Columns:**
- `id` INTEGER PRIMARY KEY
- `supplier_id` UUID NOT NULL FK → `core.suppliers.id`
- `month_year` DATE NOT NULL
- `total_orders` INTEGER DEFAULT 0
- `avg_delivery_time` DECIMAL(4,1)
- `return_rate` DECIMAL(5,2)
- `avg_roi` DECIMAL(5,2)
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_supplier_performance_month` ON `month_year`
- `idx_supplier_performance_supplier` ON `supplier_id`

**Relationships:**
- FK: `supplier_id` → `core.suppliers.id`

---

#### `core.supplier_history`
**Purpose:** Historical events and milestones for suppliers

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `supplier_id` UUID NOT NULL FK → `core.suppliers.id` (CASCADE)
- `event_date` DATE NOT NULL
- `event_type` VARCHAR(50) NOT NULL (founded, opened_store, closed_store, expansion, rebranding, controversy, milestone, closure)
- `event_title` VARCHAR(200) NOT NULL
- `event_description` TEXT
- `impact_level` VARCHAR(20) DEFAULT 'medium' (low, medium, high, critical)
- `source_url` VARCHAR(500)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_supplier_history_supplier_date` ON (`supplier_id`, `event_date`)
- `idx_supplier_history_event_type` ON `event_type`

**Relationships:**
- FK: `supplier_id` → `core.suppliers.id` (CASCADE)

---

### 2.2 Products Schema Tables

#### `products.products`
**Purpose:** Product master data with StockX enrichment

**Columns:**
- `id` UUID PRIMARY KEY
- `sku` VARCHAR(100) UNIQUE NOT NULL
- `brand_id` UUID FK → `core.brands.id`
- `category_id` UUID NOT NULL FK → `core.categories.id`
- `name` VARCHAR(255) NOT NULL
- `description` TEXT
- `retail_price` DECIMAL(10,2)
- `avg_resale_price` DECIMAL(10,2)
- `release_date` TIMESTAMP(TZ)
- **NEW (StockX Enrichment):**
  - `stockx_product_id` VARCHAR(100) - StockX product identifier
  - `style_code` VARCHAR(200) - Nike/Adidas style code (increased from 50)
  - `enrichment_data` JSONB - Complete StockX catalog data
  - `lowest_ask` DECIMAL(10,2) - Current lowest ask on StockX
  - `highest_bid` DECIMAL(10,2) - Current highest bid on StockX
  - `recommended_sell_faster` DECIMAL(10,2) - StockX recommendation
  - `recommended_earn_more` DECIMAL(10,2) - StockX recommendation
  - `last_enriched_at` TIMESTAMP(TZ) - Last enrichment timestamp
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_products_sku_lookup` ON `sku`
- `idx_products_brand_id` ON `brand_id`
- `idx_products_category_id` ON `category_id`
- `ix_products_stockx_product_id` ON `stockx_product_id`
- `ix_products_last_enriched_at` ON `last_enriched_at`

**Relationships:**
- FK: `brand_id` → `core.brands.id`
- FK: `category_id` → `core.categories.id`
- Referenced by: `products.inventory`, `pricing.*`, `analytics.*`, `integration.price_sources`, `integration.awin_products`

---

#### `products.inventory`
**Purpose:** Inventory items with financial and performance tracking

**Columns:**
- `id` UUID PRIMARY KEY
- `product_id` UUID NOT NULL FK → `products.products.id`
- `size_id` UUID NOT NULL FK → `sizes.id`
- `supplier_id` UUID FK → `core.suppliers.id`
- `quantity` INTEGER NOT NULL
- `purchase_price` DECIMAL(10,2)
- `purchase_date` TIMESTAMP(TZ)
- `supplier` VARCHAR(100) (legacy text field)
- `status` VARCHAR(50) NOT NULL
- `notes` TEXT
- **NEW (Notion Parity - Purchase):**
  - `delivery_date` TIMESTAMP(TZ)
  - `gross_purchase_price` DECIMAL(10,2) - Price including VAT
  - `vat_amount` DECIMAL(10,2)
  - `vat_rate` DECIMAL(5,2) DEFAULT 19.00
- **NEW (Business Intelligence):**
  - `shelf_life_days` INTEGER - Days since purchase
  - `profit_per_shelf_day` DECIMAL(10,2) - PAS metric
  - `roi_percentage` DECIMAL(5,2) - Return on Investment
  - ~~`sale_overview` TEXT~~ (REMOVED - redundant with orders.shelf_life_days)
- **NEW (Multi-Platform):**
  - `location` VARCHAR(50)
  - `listed_stockx` BOOLEAN DEFAULT false
  - `listed_alias` BOOLEAN DEFAULT false
  - `listed_local` BOOLEAN DEFAULT false
- **NEW (Advanced Status):**
  - `detailed_status` ENUM(inventory_status) - incoming, available, consigned, need_shipping, packed, outgoing, sale_completed, cancelled
- **NEW (External IDs):**
  - `external_ids` JSONB - Platform-specific IDs
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_inventory_status` ON `status`
- `idx_inventory_product_id` ON `product_id`
- `idx_inventory_created_at` ON `created_at`
- `idx_inventory_status_created_at` ON (`status`, `created_at`)
- `idx_inventory_shelf_life` ON `shelf_life_days`
- `idx_inventory_roi` ON `roi_percentage`
- `idx_inventory_location` ON `location`
- `idx_inventory_delivery_date` ON `delivery_date`

**Triggers:**
- `trigger_calculate_inventory_analytics` - Auto-calculates shelf_life_days, roi_percentage, sale_overview

**Relationships:**
- FK: `product_id` → `products.products.id`
- FK: `size_id` → `sizes.id`
- FK: `supplier_id` → `core.suppliers.id`
- Referenced by: `transactions.transactions`, `transactions.orders`, `analytics.marketplace_data`

---

#### `sizes` (Public Schema)
**Purpose:** Global size catalog with standardization

**Columns:**
- `id` UUID PRIMARY KEY
- `category_id` UUID FK → `core.categories.id`
- `value` VARCHAR(20) NOT NULL - Display value (e.g., "US 9", "EU 42")
- `standardized_value` DECIMAL(4,1) - Normalized size for matching
- `region` VARCHAR(10) NOT NULL - US, EU, UK, etc.
- Timestamps: `created_at`, `updated_at`

**Relationships:**
- FK: `category_id` → `core.categories.id`
- Referenced by: `products.inventory`, `integration.price_sources`

---

### 2.3 Integration Schema Tables

#### `integration.import_batches`
**Purpose:** Track bulk import jobs

**Columns:**
- `id` UUID PRIMARY KEY
- `source` VARCHAR(50) NOT NULL
- `total_records` INTEGER NOT NULL
- `status` VARCHAR(50) NOT NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `completed_at` TIMESTAMP

**Relationships:**
- Referenced by: `integration.import_records`

---

#### `integration.import_records`
**Purpose:** Individual records from import batches

**Columns:**
- `id` UUID PRIMARY KEY
- `batch_id` UUID NOT NULL FK → `integration.import_batches.id`
- `source_data` JSONB NOT NULL
- `processed_data` JSONB
- `validation_errors` JSONB
- `status` VARCHAR(50)
- `processing_started_at` TIMESTAMP
- `processing_completed_at` TIMESTAMP
- `error_message` TEXT
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_import_record_status` ON `status`

**Relationships:**
- FK: `batch_id` → `integration.import_batches.id`

---

#### `integration.market_prices` (Legacy)
**Purpose:** External market price data (superseded by price_sources)

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `product_id` UUID NOT NULL FK → `products.products.id`
- `source` VARCHAR(100) NOT NULL - Data source (awin, webgains, etc.)
- `supplier_name` VARCHAR(100) NOT NULL
- `external_id` VARCHAR(255)
- `buy_price` DECIMAL(10,2) NOT NULL
- `currency` VARCHAR(3) DEFAULT 'EUR'
- `availability` VARCHAR(50)
- `stock_qty` INTEGER
- `product_url` TEXT
- `last_updated` TIMESTAMP DEFAULT now()
- `created_at` TIMESTAMP DEFAULT now()
- `raw_data` JSONB

**Indexes:**
- `idx_market_prices_product_id` ON `product_id`
- `idx_market_prices_source` ON `source`
- `idx_market_prices_supplier` ON `supplier_name`
- `idx_market_prices_price` ON `buy_price`
- `idx_market_prices_updated` ON `last_updated`
- `idx_market_prices_quickflip` ON (`product_id`, `buy_price`, `last_updated`)

**Relationships:**
- FK: `product_id` → `products.products.id`

---

#### `integration.awin_products`
**Purpose:** Awin affiliate feed product data

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- **Awin IDs:**
  - `awin_product_id` VARCHAR(50) UNIQUE NOT NULL
  - `merchant_product_id` VARCHAR(100)
  - `merchant_id` INTEGER NOT NULL
  - `merchant_name` VARCHAR(200)
  - `data_feed_id` INTEGER
- **Product Info:**
  - `product_name` VARCHAR(500) NOT NULL
  - `brand_name` VARCHAR(200)
  - `brand_id` INTEGER
  - `ean` VARCHAR(20)
  - `product_gtin` VARCHAR(20)
  - `mpn` VARCHAR(100)
  - `product_model` VARCHAR(200)
- **Pricing (in cents):**
  - `retail_price_cents` INTEGER
  - `store_price_cents` INTEGER
  - `rrp_price_cents` INTEGER
  - `currency` VARCHAR(3) DEFAULT 'EUR'
- **Product Details:**
  - `description` TEXT
  - `short_description` TEXT
  - `colour` VARCHAR(100)
  - `size` VARCHAR(20)
  - `material` VARCHAR(200)
- **Stock:**
  - `in_stock` BOOLEAN DEFAULT false
  - `stock_quantity` INTEGER DEFAULT 0
  - `delivery_time` VARCHAR(100)
- **Images:**
  - `image_url` VARCHAR(1000)
  - `thumbnail_url` VARCHAR(1000)
  - `alternate_images` JSON
- **Links:**
  - `affiliate_link` VARCHAR(2000)
  - `merchant_link` VARCHAR(2000)
- **Matching:**
  - `matched_product_id` UUID
  - `match_confidence` DECIMAL(3,2)
  - `match_method` VARCHAR(50)
- **StockX Enrichment:**
  - `stockx_product_id` UUID
  - `stockx_url_key` VARCHAR(200)
  - `stockx_style_id` VARCHAR(100)
  - `stockx_lowest_ask_cents` INTEGER
  - `stockx_highest_bid_cents` INTEGER
  - `profit_cents` INTEGER
  - `profit_percentage` DECIMAL(5,2)
  - `last_enriched_at` TIMESTAMP
  - `enrichment_status` VARCHAR(20) DEFAULT 'pending' (pending, matched, not_found, error)
- Timestamps: `last_updated`, `feed_import_date`, `created_at`, `updated_at`

**Indexes:**
- `idx_awin_ean` ON `ean`
- `idx_awin_merchant` ON `merchant_id`
- `idx_awin_brand` ON `brand_name`
- `idx_awin_matched_product` ON `matched_product_id`
- `idx_awin_in_stock` ON `in_stock`
- `idx_awin_last_updated` ON `last_updated`
- `idx_awin_stockx_product_id` ON `stockx_product_id`
- `idx_awin_profit` ON `profit_cents`
- `idx_awin_enrichment_status` ON `enrichment_status`

**Triggers:**
- `awin_price_change_trigger` - Tracks price changes to `awin_price_history`

**Relationships:**
- Referenced by: `integration.awin_price_history`

---

#### `integration.awin_price_history`
**Purpose:** Track Awin product price changes

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `awin_product_id` VARCHAR(50) NOT NULL FK → `integration.awin_products.awin_product_id` (CASCADE)
- `price_cents` INTEGER NOT NULL
- `in_stock` BOOLEAN
- `recorded_at` TIMESTAMP DEFAULT NOW()

**Indexes:**
- `idx_awin_price_history_product` ON `awin_product_id`
- `idx_awin_price_history_date` ON `recorded_at`

**Relationships:**
- FK: `awin_product_id` → `integration.awin_products.awin_product_id` (CASCADE)

---

#### `integration.awin_enrichment_jobs`
**Purpose:** Track enrichment job progress

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `job_type` VARCHAR(50) NOT NULL (stockx_match, price_update, etc.)
- `status` VARCHAR(20) NOT NULL (pending, running, completed, failed)
- **Progress:**
  - `total_products` INTEGER
  - `processed_products` INTEGER DEFAULT 0
  - `matched_products` INTEGER DEFAULT 0
  - `failed_products` INTEGER DEFAULT 0
- **Results:**
  - `results_summary` JSON
  - `error_log` TEXT
- Timestamps: `started_at`, `completed_at`, `created_at`, `updated_at`

**Indexes:**
- `idx_awin_enrichment_jobs_status` ON `status`
- `idx_awin_enrichment_jobs_created` ON `created_at`

---

#### `integration.price_sources` ⭐ **NEW - Unified Architecture**
**Purpose:** Unified price data from all sources (StockX, Awin, eBay, etc.)

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- **Product Relationship:**
  - `product_id` UUID NOT NULL FK → `products.products.id` (CASCADE)
  - `size_id` UUID FK → `sizes.id` (SET NULL)
- **Source Identification:**
  - `source_type` ENUM(source_type_enum) NOT NULL (stockx, awin, ebay, goat, klekt, restocks, stockxapi)
  - `source_product_id` VARCHAR(100) NOT NULL
  - `source_name` VARCHAR(200) - Display name (e.g., "size?Official DE")
- **Price Information:**
  - `price_type` ENUM(price_type_enum) NOT NULL (resale, retail, auction, wholesale)
  - `price_cents` INTEGER NOT NULL
  - `currency` VARCHAR(3) DEFAULT 'EUR' NOT NULL
- **Stock Information:**
  - `stock_quantity` INTEGER
  - `in_stock` BOOLEAN DEFAULT false NOT NULL
  - `condition` ENUM(condition_enum) DEFAULT 'new' (new, like_new, used_excellent, used_good, used_fair, deadstock)
- **URLs:**
  - `source_url` TEXT
  - `affiliate_link` TEXT
- **Relationships:**
  - `supplier_id` UUID FK → `core.suppliers.id` (SET NULL)
- **Metadata:**
  - `metadata` JSON - Source-specific data
- Timestamps: `last_updated`, `created_at`, `updated_at`

**Constraints:**
- CHECK: `price_cents >= 0`
- CHECK: `stock_quantity >= 0` OR NULL
- CHECK: `currency ~ '^[A-Z]{3}$'`
- CHECK: `last_updated <= NOW()` OR NULL

**Unique Constraints (Partial Indexes):**
- `uq_price_source_with_size` UNIQUE (`product_id`, `source_type`, `source_product_id`, `size_id`) WHERE `size_id IS NOT NULL`
- `uq_price_source_without_size` UNIQUE (`product_id`, `source_type`, `source_product_id`) WHERE `size_id IS NULL`

**Indexes:**
- `idx_price_sources_product_id` ON `product_id`
- `idx_price_sources_source_type` ON `source_type`
- `idx_price_sources_price_type` ON `price_type`
- `idx_price_sources_product_source` ON (`product_id`, `source_type`)
- `idx_price_sources_source_price_type` ON (`source_type`, `price_type`)
- `idx_price_sources_in_stock` ON `in_stock`
- `idx_price_sources_supplier` ON `supplier_id`
- `idx_price_sources_size` ON `size_id`
- `idx_price_sources_last_updated` ON `last_updated`
- `idx_price_sources_price_cents` ON `price_cents`
- **Partial Indexes for Profit Queries:**
  - `idx_price_sources_retail_active` ON (`product_id`, `size_id`, `price_cents`) WHERE `price_type = 'retail' AND in_stock = true`
  - `idx_price_sources_resale_active` ON (`product_id`, `size_id`, `price_cents`) WHERE `price_type = 'resale' AND in_stock = true`

**Triggers:**
- `price_change_trigger` - Logs price changes to `integration.price_history`

**Relationships:**
- FK: `product_id` → `products.products.id` (CASCADE)
- FK: `size_id` → `sizes.id` (SET NULL)
- FK: `supplier_id` → `core.suppliers.id` (SET NULL)
- Referenced by: `integration.price_history`

---

#### `integration.price_history` ⭐ **NEW**
**Purpose:** Historical price tracking for all sources

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `price_source_id` UUID NOT NULL FK → `integration.price_sources.id` (CASCADE)
- `price_cents` INTEGER NOT NULL
- `in_stock` BOOLEAN
- `stock_quantity` INTEGER
- `recorded_at` TIMESTAMP DEFAULT NOW() NOT NULL

**Indexes:**
- `idx_price_history_source` ON `price_source_id`
- `idx_price_history_recorded` ON `recorded_at`
- `idx_price_history_source_date` ON (`price_source_id`, `recorded_at`)

**Relationships:**
- FK: `price_source_id` → `integration.price_sources.id` (CASCADE)

---

### 2.4 Transactions Schema Tables

#### `transactions.transactions` (Legacy)
**Purpose:** Legacy transaction records (being phased out)

**Columns:**
- `id` UUID PRIMARY KEY
- `inventory_id` UUID NOT NULL FK → `products.inventory.id`
- `platform_id` UUID NOT NULL FK → `core.platforms.id`
- `transaction_date` TIMESTAMP(TZ) NOT NULL
- `sale_price` DECIMAL(10,2) NOT NULL
- `platform_fee` DECIMAL(10,2) NOT NULL
- `shipping_cost` DECIMAL(10,2) NOT NULL
- `net_profit` DECIMAL(10,2) NOT NULL
- `status` VARCHAR(50) NOT NULL
- `external_id` VARCHAR(100)
- `buyer_destination_country` VARCHAR(100)
- `buyer_destination_city` VARCHAR(100)
- `notes` TEXT
- **REMOVED:** ~~`buyer_id`~~ (cleanup migration)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_transaction_date` ON `transaction_date`
- `idx_transaction_inventory_id` ON `inventory_id`
- `idx_transaction_date_status` ON (`transaction_date`, `status`)

**Relationships:**
- FK: `inventory_id` → `products.inventory.id`
- FK: `platform_id` → `core.platforms.id`

---

#### `transactions.orders` ⭐ **Multi-Platform Orders**
**Purpose:** Unified multi-platform order management (replaces transactions)

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `listing_id` UUID NOT NULL FK → `platforms.stockx_listings.id`
- **Platform Support:**
  - `platform_id` UUID NOT NULL FK → `core.platforms.id`
  - `stockx_order_number` VARCHAR(100) (nullable, StockX-specific)
  - `external_id` VARCHAR(200) - Generic order ID for other platforms
- **Sale Details:**
  - `sale_price` DECIMAL(10,2) NOT NULL
  - `buyer_premium` DECIMAL(10,2)
  - `seller_fee` DECIMAL(10,2)
  - `processing_fee` DECIMAL(10,2)
  - `net_proceeds` DECIMAL(10,2)
- **Profit Calculation:**
  - `original_buy_price` DECIMAL(10,2)
  - `gross_profit` DECIMAL(10,2)
  - `net_profit` DECIMAL(10,2)
  - `actual_margin` DECIMAL(5,2)
  - `roi` DECIMAL(5,2)
- **Status & Tracking:**
  - `order_status` VARCHAR(20) CHECK IN ('pending', 'authenticated', 'shipped', 'completed', 'cancelled')
  - `shipping_status` VARCHAR(20)
  - `tracking_number` VARCHAR(100)
- **Fees (Multi-Platform):**
  - `platform_fee` DECIMAL(10,2)
  - `shipping_cost` DECIMAL(10,2)
- **Buyer Destination:**
  - `buyer_destination_country` VARCHAR(100)
  - `buyer_destination_city` VARCHAR(200)
- **Notion Parity Fields:**
  - `sold_at` TIMESTAMP(TZ)
  - `gross_sale` DECIMAL(10,2) - Gross sale before fees
  - `net_proceeds` DECIMAL(10,2) - Net after platform fees
  - `gross_profit` DECIMAL(10,2) - Sale - Purchase
  - `net_profit` DECIMAL(10,2) - After all costs
  - `roi` DECIMAL(5,2) - Return on investment %
  - `payout_received` BOOLEAN DEFAULT false
  - `payout_date` TIMESTAMP(TZ)
  - `shelf_life_days` INTEGER - Days between purchase and sale
- **Timeline:**
  - `sold_at` TIMESTAMP(TZ) NOT NULL
  - `shipped_at` TIMESTAMP(TZ)
  - `completed_at` TIMESTAMP(TZ)
- Meta: `notes` TEXT
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_stockx_orders_status` ON `order_status`
- `idx_stockx_orders_listing` ON `listing_id`
- `idx_stockx_orders_sold_at` ON `sold_at`
- `ix_orders_external_id` ON `external_id`
- `idx_orders_sold_at` ON `sold_at`
- `idx_orders_payout_received` ON `payout_received`

**Relationships:**
- FK: `listing_id` → `platforms.stockx_listings.id`
- FK: `platform_id` → `core.platforms.id`

---

### 2.5 Pricing Schema Tables

#### `pricing.price_rules`
**Purpose:** Core pricing logic configurations

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `name` VARCHAR(100) NOT NULL
- `rule_type` VARCHAR(50) NOT NULL (cost_plus, market_based, competitive)
- `priority` INTEGER NOT NULL DEFAULT 100
- `active` BOOLEAN NOT NULL DEFAULT true
- **Scope:**
  - `brand_id` UUID FK → `core.brands.id`
  - `category_id` UUID FK → `core.categories.id`
  - `platform_id` UUID FK → `core.platforms.id`
- **Pricing Parameters:**
  - `base_markup_percent` DECIMAL(5,2)
  - `minimum_margin_percent` DECIMAL(5,2)
  - `maximum_discount_percent` DECIMAL(5,2)
  - `condition_multipliers` JSON
  - `seasonal_adjustments` JSON
- **Validity:**
  - `effective_from` TIMESTAMP(TZ) NOT NULL
  - `effective_until` TIMESTAMP(TZ)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_price_rules_brand_active` ON (`brand_id`, `active`)
- `idx_price_rules_effective_dates` ON (`effective_from`, `effective_until`)

**Relationships:**
- FK: `brand_id` → `core.brands.id`
- FK: `category_id` → `core.categories.id`
- FK: `platform_id` → `core.platforms.id`

---

#### `pricing.brand_multipliers`
**Purpose:** Brand-specific pricing adjustments

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `brand_id` UUID NOT NULL FK → `core.brands.id`
- `multiplier_type` VARCHAR(50) NOT NULL (premium, discount, seasonal)
- `multiplier_value` DECIMAL(4,3) NOT NULL
- `active` BOOLEAN NOT NULL DEFAULT true
- `effective_from` DATE NOT NULL
- `effective_until` DATE
- Timestamps: `created_at`, `updated_at`

**Relationships:**
- FK: `brand_id` → `core.brands.id`

---

#### `pricing.price_history`
**Purpose:** Historical price tracking (pricing context)

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `product_id` UUID NOT NULL FK → `products.products.id`
- `inventory_item_id` UUID FK → `products.inventory.id`
- `platform_id` UUID FK → `core.platforms.id`
- `price_date` DATE NOT NULL
- `price_type` VARCHAR(30) NOT NULL (listing, sale, market, competitor)
- `price_amount` DECIMAL(10,2) NOT NULL
- `currency` VARCHAR(3) NOT NULL DEFAULT 'EUR'
- `source` VARCHAR(50) NOT NULL (internal, stockx, goat, manual)
- `confidence_score` DECIMAL(3,2)
- `metadata` JSON
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_price_history_product_date` ON (`product_id`, `price_date`)
- `idx_price_history_date_type` ON (`price_date`, `price_type`)

**Relationships:**
- FK: `product_id` → `products.products.id`
- FK: `inventory_item_id` → `products.inventory.id`
- FK: `platform_id` → `core.platforms.id`

---

#### `pricing.market_prices`
**Purpose:** External market price data (pricing context)

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `product_id` UUID NOT NULL FK → `products.products.id`
- `platform_name` VARCHAR(50) NOT NULL
- `size_value` VARCHAR(20)
- `condition` VARCHAR(20) NOT NULL
- `price_date` DATE NOT NULL
- `lowest_ask` DECIMAL(10,2)
- `highest_bid` DECIMAL(10,2)
- `last_sale` DECIMAL(10,2)
- `average_price` DECIMAL(10,2)
- `sales_volume` INTEGER
- `premium_percentage` DECIMAL(5,2)
- `data_quality_score` DECIMAL(3,2)
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_market_prices_product_platform` ON (`product_id`, `platform_name`)
- `idx_market_prices_date` ON `price_date`

**Relationships:**
- FK: `product_id` → `products.products.id`

---

### 2.6 Analytics Schema Tables

#### `analytics.sales_forecasts`
**Purpose:** Predictive sales data

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `forecast_run_id` UUID NOT NULL
- **Scope:**
  - `product_id` UUID FK → `products.products.id`
  - `brand_id` UUID FK → `core.brands.id`
  - `category_id` UUID FK → `core.categories.id`
  - `platform_id` UUID FK → `core.platforms.id`
  - `forecast_level` VARCHAR(20) NOT NULL (product, brand, category, platform)
- **Forecast Data:**
  - `forecast_date` DATE NOT NULL
  - `forecast_horizon` VARCHAR(20) NOT NULL (daily, weekly, monthly)
  - `forecasted_units` DECIMAL(10,2) NOT NULL
  - `forecasted_revenue` DECIMAL(12,2) NOT NULL
  - `confidence_lower` DECIMAL(10,2)
  - `confidence_upper` DECIMAL(10,2)
- **Model Info:**
  - `model_name` VARCHAR(50) NOT NULL
  - `model_version` VARCHAR(20) NOT NULL
  - `feature_importance` JSON
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_sales_forecasts_run_date` ON (`forecast_run_id`, `forecast_date`)
- `idx_sales_forecasts_product_date` ON (`product_id`, `forecast_date`)
- `idx_sales_forecasts_brand_level` ON (`brand_id`, `forecast_level`)

**Relationships:**
- FK: `product_id` → `products.products.id`
- FK: `brand_id` → `core.brands.id`
- FK: `category_id` → `core.categories.id`
- FK: `platform_id` → `core.platforms.id`

---

#### `analytics.forecast_accuracy`
**Purpose:** Track prediction performance

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `forecast_run_id` UUID NOT NULL
- `model_name` VARCHAR(50) NOT NULL
- `forecast_level` VARCHAR(20) NOT NULL
- `forecast_horizon` VARCHAR(20) NOT NULL
- `accuracy_date` DATE NOT NULL
- **Metrics:**
  - `mape_score` DECIMAL(5,2) - Mean Absolute Percentage Error
  - `rmse_score` DECIMAL(10,2) - Root Mean Square Error
  - `mae_score` DECIMAL(10,2) - Mean Absolute Error
  - `r2_score` DECIMAL(5,4) - R-squared
  - `bias_score` DECIMAL(8,2)
- `records_evaluated` INTEGER NOT NULL
- `evaluation_period_days` INTEGER NOT NULL
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_forecast_accuracy_model_date` ON (`model_name`, `accuracy_date`)

---

#### `analytics.demand_patterns`
**Purpose:** Historical demand analysis

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- **Scope:**
  - `product_id` UUID FK → `products.products.id`
  - `brand_id` UUID FK → `core.brands.id`
  - `category_id` UUID FK → `core.categories.id`
  - `analysis_level` VARCHAR(20) NOT NULL
- **Pattern Data:**
  - `pattern_date` DATE NOT NULL
  - `period_type` VARCHAR(20) NOT NULL (daily, weekly, monthly, seasonal)
  - `demand_score` DECIMAL(8,4) NOT NULL
  - `velocity_rank` INTEGER
  - `seasonality_factor` DECIMAL(4,3)
  - `trend_direction` VARCHAR(20) (increasing, decreasing, stable)
  - `volatility_score` DECIMAL(5,4)
  - `pattern_metadata` JSON
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_demand_patterns_product_date` ON (`product_id`, `pattern_date`)
- `idx_demand_patterns_brand_period` ON (`brand_id`, `period_type`)

**Relationships:**
- FK: `product_id` → `products.products.id`
- FK: `brand_id` → `core.brands.id`
- FK: `category_id` → `core.categories.id`

---

#### `analytics.pricing_kpis`
**Purpose:** Key performance indicators

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `kpi_date` DATE NOT NULL
- **Scope:**
  - `product_id` UUID FK → `products.products.id`
  - `brand_id` UUID FK → `core.brands.id`
  - `category_id` UUID FK → `core.categories.id`
  - `platform_id` UUID FK → `core.platforms.id`
  - `aggregation_level` VARCHAR(20) NOT NULL
- **KPIs:**
  - `average_margin_percent` DECIMAL(5,2)
  - `average_markup_percent` DECIMAL(5,2)
  - `price_realization_percent` DECIMAL(5,2)
  - `competitive_index` DECIMAL(5,2)
  - `conversion_rate_percent` DECIMAL(5,2)
  - `revenue_impact_eur` DECIMAL(12,2)
  - `units_sold` INTEGER
  - `average_selling_price` DECIMAL(10,2)
  - `price_elasticity` DECIMAL(6,4)
- `created_at` TIMESTAMP DEFAULT now()

**Indexes:**
- `idx_pricing_kpis_date_level` ON (`kpi_date`, `aggregation_level`)
- `idx_pricing_kpis_brand_date` ON (`brand_id`, `kpi_date`)

**Relationships:**
- FK: `product_id` → `products.products.id`
- FK: `brand_id` → `core.brands.id`
- FK: `category_id` → `core.categories.id`
- FK: `platform_id` → `core.platforms.id`

---

#### `analytics.marketplace_data`
**Purpose:** Marketplace listing data and market intelligence

**Columns:**
- `id` UUID PRIMARY KEY
- `inventory_item_id` UUID NOT NULL FK → `products.inventory.id`
- `platform_id` UUID NOT NULL FK → `core.platforms.id`
- `marketplace_listing_id` VARCHAR(255) - External listing ID
- **Pricing:**
  - `ask_price` DECIMAL(10,2) - Current ask price
  - `bid_price` DECIMAL(10,2) - Current bid price
  - `market_lowest_ask` DECIMAL(10,2)
  - `market_highest_bid` DECIMAL(10,2)
  - `last_sale_price` DECIMAL(10,2)
- **Market Intelligence:**
  - `sales_frequency` INTEGER - Sales in last 30 days
  - `volatility` DECIMAL(5,4) - Price volatility (0.0-1.0)
  - `fees_percentage` DECIMAL(5,4) - Platform fees (0.08 = 8%)
- `platform_specific` JSONB - Platform-specific metadata
- Timestamps: `updated_at`, `created_at`

**Constraints:**
- UNIQUE (`inventory_item_id`, `platform_id`)
- CHECK: `volatility >= 0 AND volatility <= 1`
- CHECK: `fees_percentage >= 0 AND fees_percentage <= 1`

**Indexes:**
- `idx_marketplace_data_platform` ON `platform_id`
- `idx_marketplace_data_item` ON `inventory_item_id`
- `idx_marketplace_data_updated` ON `updated_at`
- `idx_marketplace_data_ask_price` ON `ask_price` WHERE `ask_price IS NOT NULL`

**Relationships:**
- FK: `inventory_item_id` → `products.inventory.id`
- FK: `platform_id` → `core.platforms.id`

---

### 2.7 Auth Schema Tables

#### `auth.users`
**Purpose:** User accounts with role-based access

**Columns:**
- `id` UUID PRIMARY KEY
- `email` VARCHAR(255) UNIQUE NOT NULL
- `username` VARCHAR(100) UNIQUE NOT NULL
- `hashed_password` VARCHAR(255) NOT NULL
- `role` ENUM(user_role) NOT NULL DEFAULT 'user' (admin, user, readonly)
- `is_active` BOOLEAN NOT NULL DEFAULT true
- `last_login` TIMESTAMP(TZ)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_users_email` UNIQUE ON `email`
- `idx_users_username` UNIQUE ON `username`
- `idx_users_role` ON `role`
- `idx_users_is_active` ON `is_active`

**Default Data:**
- Admin user: `admin@soleflip.com` / `admin` (password: `admin123`)

---

### 2.8 Platforms Schema Tables

#### `platforms.stockx_listings`
**Purpose:** StockX active listings

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `product_id` UUID NOT NULL FK → `products.products.id`
- `stockx_listing_id` VARCHAR(100) UNIQUE NOT NULL
- `stockx_product_id` VARCHAR(100) NOT NULL
- `variant_id` VARCHAR(100)
- **Listing Details:**
  - `ask_price` DECIMAL(10,2) NOT NULL
  - `original_ask_price` DECIMAL(10,2)
  - `buy_price` DECIMAL(10,2)
  - `expected_profit` DECIMAL(10,2)
  - `expected_margin` DECIMAL(5,2)
- **Status:**
  - `status` VARCHAR(20) NOT NULL DEFAULT 'active' CHECK IN ('active', 'inactive', 'sold', 'expired', 'cancelled')
  - `is_active` BOOLEAN NOT NULL DEFAULT true
  - `expires_at` TIMESTAMP(TZ)
- **Market Data:**
  - `current_lowest_ask` DECIMAL(10,2)
  - `current_highest_bid` DECIMAL(10,2)
  - `last_price_update` TIMESTAMP(TZ)
- **Source Tracking:**
  - `source_opportunity_id` UUID
  - `created_from` VARCHAR(50) DEFAULT 'manual'
- Timestamps: `created_at`, `updated_at`, `listed_at`, `delisted_at`

**Indexes:**
- `idx_stockx_listings_status` ON `status`
- `idx_stockx_listings_active` ON `is_active`
- `idx_stockx_listings_product` ON `product_id`
- `idx_stockx_listings_stockx_id` ON `stockx_listing_id`

**Relationships:**
- FK: `product_id` → `products.products.id`
- Referenced by: `transactions.orders`, `platforms.pricing_history`

---

#### `platforms.stockx_orders`
**Purpose:** StockX order details (legacy, superseded by transactions.orders)

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `listing_id` UUID NOT NULL FK → `platforms.stockx_listings.id`
- `stockx_order_number` VARCHAR(100) UNIQUE NOT NULL
- **Sale Details:**
  - `sale_price` DECIMAL(10,2) NOT NULL
  - `buyer_premium` DECIMAL(10,2)
  - `seller_fee` DECIMAL(10,2)
  - `processing_fee` DECIMAL(10,2)
  - `net_proceeds` DECIMAL(10,2)
- **Profit Calculation:**
  - `original_buy_price` DECIMAL(10,2)
  - `gross_profit` DECIMAL(10,2)
  - `net_profit` DECIMAL(10,2)
  - `actual_margin` DECIMAL(5,2)
  - `roi` DECIMAL(5,2)
- **Status & Tracking:**
  - `order_status` VARCHAR(20) CHECK IN ('pending', 'authenticated', 'shipped', 'completed', 'cancelled')
  - `shipping_status` VARCHAR(20)
  - `tracking_number` VARCHAR(100)
- **Timeline:**
  - `sold_at` TIMESTAMP(TZ) NOT NULL
  - `shipped_at` TIMESTAMP(TZ)
  - `completed_at` TIMESTAMP(TZ)
- Timestamps: `created_at`, `updated_at`

**Indexes:**
- `idx_stockx_orders_status` ON `order_status`
- `idx_stockx_orders_listing` ON `listing_id`
- `idx_stockx_orders_sold_at` ON `sold_at`

**Relationships:**
- FK: `listing_id` → `platforms.stockx_listings.id`

---

#### `platforms.pricing_history`
**Purpose:** StockX listing price changes

**Columns:**
- `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
- `listing_id` UUID NOT NULL FK → `platforms.stockx_listings.id`
- `old_price` DECIMAL(10,2)
- `new_price` DECIMAL(10,2) NOT NULL
- `change_reason` VARCHAR(100)
- `market_lowest_ask` DECIMAL(10,2)
- `market_highest_bid` DECIMAL(10,2)
- `created_at` TIMESTAMP DEFAULT NOW()

**Indexes:**
- `idx_pricing_history_listing` ON `listing_id`
- `idx_pricing_history_created` ON `created_at`

**Relationships:**
- FK: `listing_id` → `platforms.stockx_listings.id`

---

### 2.9 Public Schema Tables

#### `system_config`
**Purpose:** Encrypted system configuration

**Columns:**
- `key` VARCHAR(100) PRIMARY KEY
- `value_encrypted` TEXT NOT NULL
- `description` TEXT
- Timestamps: `created_at`, `updated_at`

---

#### `system_logs`
**Purpose:** Application logs

**Columns:**
- `id` UUID PRIMARY KEY
- `level` VARCHAR(20) NOT NULL
- `component` VARCHAR(50) NOT NULL
- `message` TEXT NOT NULL
- `details` JSONB
- `source_table` VARCHAR(100)
- `source_id` UUID
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## 3. Database Enums

### 3.1 Integration Schema Enums

**`integration.source_type_enum`**
- Values: `stockx`, `awin`, `ebay`, `goat`, `klekt`, `restocks`, `stockxapi`
- Used in: `integration.price_sources.source_type`

**`integration.price_type_enum`**
- Values: `resale`, `retail`, `auction`, `wholesale`
- Used in: `integration.price_sources.price_type`

**`integration.condition_enum`**
- Values: `new`, `like_new`, `used_excellent`, `used_good`, `used_fair`, `deadstock`
- Used in: `integration.price_sources.condition`

### 3.2 Products Schema Enums

**`inventory_status` (no schema prefix)**
- Values: `incoming`, `available`, `consigned`, `need_shipping`, `packed`, `outgoing`, `sale_completed`, `cancelled`
- Used in: `products.inventory.detailed_status`

**`sales_platform` (no schema prefix)**
- Values: `StockX`, `Alias`, `eBay`, `Kleinanzeigen`, `Laced`, `WTN`, `Return`
- Created but not yet used in schema

### 3.3 Auth Schema Enums

**`auth.user_role`**
- Values: `admin`, `user`, `readonly`
- Used in: `auth.users.role`

---

## 4. Foreign Key Relationships

### 4.1 Relationship Diagram

```
core.brands
├─> products.products.brand_id
├─> core.brand_patterns.brand_id
├─> pricing.price_rules.brand_id
├─> pricing.brand_multipliers.brand_id
└─> analytics.* (sales_forecasts, demand_patterns, pricing_kpis)

core.categories
├─> products.products.category_id
├─> sizes.category_id
├─> pricing.price_rules.category_id
└─> analytics.* (sales_forecasts, demand_patterns, pricing_kpis)

core.platforms
├─> transactions.transactions.platform_id
├─> transactions.orders.platform_id
├─> analytics.marketplace_data.platform_id
├─> pricing.price_rules.platform_id
└─> analytics.* (sales_forecasts, pricing_kpis)

core.suppliers
├─> products.inventory.supplier_id
├─> integration.price_sources.supplier_id
├─> core.supplier_accounts.supplier_id (CASCADE)
├─> core.account_purchase_history.supplier_id (CASCADE)
├─> core.supplier_performance.supplier_id
└─> core.supplier_history.supplier_id (CASCADE)

products.products
├─> products.inventory.product_id
├─> pricing.price_history.product_id
├─> pricing.market_prices.product_id
├─> integration.market_prices.product_id
├─> integration.price_sources.product_id (CASCADE)
├─> core.account_purchase_history.product_id (SET NULL)
├─> platforms.stockx_listings.product_id
└─> analytics.* (sales_forecasts, demand_patterns, pricing_kpis)

products.inventory
├─> transactions.transactions.inventory_id
├─> transactions.orders.inventory_id (indirect via listing)
├─> analytics.marketplace_data.inventory_item_id
└─> pricing.price_history.inventory_item_id

sizes
├─> products.inventory.size_id
└─> integration.price_sources.size_id (SET NULL)

integration.import_batches
└─> integration.import_records.batch_id

integration.awin_products
└─> integration.awin_price_history.awin_product_id (CASCADE)

integration.price_sources (NEW)
└─> integration.price_history.price_source_id (CASCADE)

platforms.stockx_listings
├─> transactions.orders.listing_id
├─> platforms.stockx_orders.listing_id
└─> platforms.pricing_history.listing_id

core.supplier_accounts
└─> core.account_purchase_history.account_id (CASCADE)
```

### 4.2 Cascade Rules Summary

**CASCADE Deletes:**
- `core.suppliers` → `core.supplier_accounts`, `core.account_purchase_history`, `core.supplier_history`
- `core.supplier_accounts` → `core.account_purchase_history`
- `integration.awin_products` → `integration.awin_price_history`
- `integration.price_sources` → `integration.price_history`
- `products.products` → `integration.price_sources`

**SET NULL:**
- `products.products` → `core.account_purchase_history.product_id`
- `core.suppliers` → `integration.price_sources.supplier_id`
- `sizes` → `integration.price_sources.size_id`

---

## 5. Database Views

### 5.1 Analytics Views

**`analytics.brand_trend_analysis`**
- **Purpose:** Brand sales trends over time
- **Source:** `transactions`, `inventory`, `products`, `brands`
- **Columns:** `brand`, `month`, `transaction_count`, `total_revenue`, `avg_transaction_value`
- **Notes:** Recreated without buyer_id dependency in cleanup migration

**`analytics.brand_loyalty_analysis`**
- **Purpose:** Brand customer loyalty metrics
- **Source:** `transactions`, `inventory`, `products`, `brands`
- **Columns:** `brand`, `active_months`, `total_transactions`, `total_spent`, `avg_order_value`
- **Notes:** Recreated without buyer_id dependency in cleanup migration

### 5.2 Integration Views (NEW)

**`integration.latest_prices`**
- **Purpose:** Latest prices per product and source
- **Source:** `price_sources`, `products`, `brands`, `suppliers`
- **Columns:** All price_sources columns + `product_name`, `product_sku`, `product_ean`, `brand_name`, `supplier_name`
- **Filter:** `in_stock = true`, DISTINCT ON (`product_id`, `source_type`), ORDER BY `last_updated DESC`

**`integration.profit_opportunities_v2`** ⭐
- **Purpose:** Identify profitable arbitrage opportunities (retail vs resale)
- **Source:** `products`, `brands`, `price_sources`, `sizes`
- **Key Columns:**
  - Product: `product_id`, `product_name`, `sku`, `ean`, `brand_name`
  - Retail: `retail_source`, `retail_source_name`, `retail_price_cents`, `retail_price_eur`, `retail_supplier_id`, `retail_affiliate_link`, `retail_stock_quantity`
  - Resale: `resale_source`, `resale_source_name`, `resale_price_cents`, `resale_price_eur`
  - Sizes: `retail_size_value`, `resale_size_value`, `standardized_size`
  - Profit: `profit_cents`, `profit_eur`, `profit_percentage`, `opportunity_score`
- **Logic:**
  - Joins retail prices (`price_type = 'retail'`) with resale prices (`price_type = 'resale'`)
  - Matches via `standardized_size` OR both NULL (generic products)
  - Filters: `profit > 0` AND `in_stock = true`
  - Sorts by `profit_eur DESC`

---

## 6. Database Triggers

### 6.1 Inventory Triggers

**`trigger_calculate_inventory_analytics`**
- **Table:** `products.inventory`
- **Timing:** BEFORE INSERT OR UPDATE
- **Function:** `calculate_inventory_analytics()`
- **Actions:**
  - Calculates `shelf_life_days` from `purchase_date`
  - Calculates `roi_percentage` (basic calculation)
  - Generates `sale_overview` text (REMOVED in later migration)

### 6.2 Price Change Triggers

**`awin_price_change_trigger`**
- **Table:** `integration.awin_products`
- **Timing:** AFTER UPDATE
- **Function:** `integration.track_awin_price_changes()`
- **Actions:**
  - Logs price changes to `integration.awin_price_history`
  - Triggered when `retail_price_cents` OR `in_stock` changes

**`price_change_trigger`** ⭐ **NEW**
- **Table:** `integration.price_sources`
- **Timing:** AFTER UPDATE
- **Function:** `integration.track_price_changes()`
- **Actions:**
  - Logs price changes to `integration.price_history`
  - Triggered when `price_cents` OR `in_stock` changes

---

## 7. Indexes Summary

### 7.1 Performance Indexes

**Core Schema:**
- Suppliers: `instagram_handle`, `founded_year`
- Supplier Accounts: `supplier_id`, `email`, `status`, `last_used_at`
- Supplier History: (`supplier_id`, `event_date`), `event_type`

**Products Schema:**
- Products: `sku`, `brand_id`, `category_id`, `stockx_product_id`, `last_enriched_at`
- Inventory: `status`, `product_id`, `created_at`, (`status`, `created_at`), `shelf_life_days`, `roi_percentage`, `location`, `delivery_date`

**Integration Schema:**
- Import Records: `status`
- Market Prices (legacy): `product_id`, `source`, `supplier_name`, `price`, `last_updated`, (`product_id`, `price`, `last_updated`)
- Awin Products: `ean`, `merchant_id`, `brand_name`, `matched_product_id`, `in_stock`, `last_updated`, `stockx_product_id`, `profit_cents`, `enrichment_status`
- Awin Price History: `awin_product_id`, `recorded_at`
- Awin Enrichment Jobs: `status`, `created_at`
- **Price Sources (NEW):** 14 indexes including partial indexes for profit queries

**Transactions Schema:**
- Transactions: `transaction_date`, `inventory_id`, (`transaction_date`, `status`)
- Orders: `order_status`, `listing_id`, `sold_at`, `external_id`, `payout_received`

**Pricing Schema:**
- Price Rules: (`brand_id`, `active`), (`effective_from`, `effective_until`)
- Price History: (`product_id`, `price_date`), (`price_date`, `price_type`)
- Market Prices: (`product_id`, `platform_name`), `price_date`

**Analytics Schema:**
- Sales Forecasts: (`forecast_run_id`, `forecast_date`), (`product_id`, `forecast_date`), (`brand_id`, `forecast_level`)
- Forecast Accuracy: (`model_name`, `accuracy_date`)
- Demand Patterns: (`product_id`, `pattern_date`), (`brand_id`, `period_type`)
- Pricing KPIs: (`kpi_date`, `aggregation_level`), (`brand_id`, `kpi_date`)
- Marketplace Data: `platform_id`, `inventory_item_id`, `updated_at`, `ask_price` (partial)

**Auth Schema:**
- Users: `email` (unique), `username` (unique), `role`, `is_active`

**Platforms Schema:**
- StockX Listings: `status`, `is_active`, `product_id`, `stockx_listing_id`
- StockX Orders: `order_status`, `listing_id`, `sold_at`
- Pricing History: `listing_id`, `created_at`

### 7.2 Unique Indexes

- `products.products.sku`
- `core.brands.slug`
- `core.categories.slug`
- `core.platforms.slug`
- `core.brand_patterns.pattern`
- `core.supplier_accounts` (`supplier_id`, `email`)
- `integration.awin_products.awin_product_id`
- `platforms.stockx_listings.stockx_listing_id`
- `platforms.stockx_orders.stockx_order_number`
- `auth.users.email`
- `auth.users.username`
- **integration.price_sources:** Partial unique indexes (with/without size)

---

## 8. Design Decisions & Patterns

### 8.1 Schema Organization

**Multi-Schema Architecture:**
- **Domain Separation:** Each domain (core, products, integration, transactions, etc.) has its own schema
- **Benefits:** Clear ownership, easier permissions management, logical grouping
- **Pattern:** Follows Domain-Driven Design (DDD) principles

### 8.2 Data Redundancy Elimination

**Price Sources Unification (v2.2.8):**
- **Problem:** Multiple tables storing similar price data (`integration.market_prices`, `pricing.market_prices`, `integration.awin_products`)
- **Solution:** Created `integration.price_sources` as unified source
- **Benefits:**
  - Single source of truth
  - Eliminates duplication
  - Easier to add new sources
  - Consistent price tracking via `integration.price_history`

### 8.3 Multi-Platform Support

**Orders Table Evolution:**
- **From:** StockX-specific `platforms.stockx_orders`
- **To:** Multi-platform `transactions.orders`
- **Changes:**
  - Added `platform_id` FK
  - Made `stockx_order_number` nullable
  - Added generic `external_id`
  - Added platform-agnostic fee fields

### 8.4 PCI Compliance

**Supplier Accounts Security:**
- **Migration:** `pci_compliance_payment_fields`
- **Removed:** `cc_number_encrypted`, `cvv_encrypted`
- **Added:** Tokenized payment fields (`payment_provider`, `payment_method_token`, `payment_method_last4`, `payment_method_brand`)
- **Downgrade:** Disabled for security reasons

### 8.5 Notion Feature Parity

**Business Intelligence Fields:**
- **Migration:** `business_intelligence_fields`
- **Purpose:** Match Notion database capabilities
- **Added to Inventory:**
  - `shelf_life_days` - Days in inventory
  - `profit_per_shelf_day` - PAS (Profit per Active day) metric
  - `roi_percentage` - Return on Investment
  - Multi-platform listing flags
  - Advanced status enum
- **Added to Orders:**
  - Complete financial tracking (gross_sale, net_proceeds, profit calculations)
  - Payout tracking
  - Shelf life days (purchase to sale)

### 8.6 Size Standardization

**Size Matching Strategy:**
- **Problem:** Different regions use different size formats (US, EU, UK)
- **Solution:** `sizes.standardized_value` (DECIMAL)
- **Example:** US 9 = EU 42.5 = UK 8 = 42.5 (standardized)
- **Usage:** Enables cross-source price matching in `profit_opportunities_v2` view

### 8.7 Price Tracking Strategy

**Historical Price Tracking:**
- **Method:** Trigger-based automatic logging
- **Tables:**
  - `integration.awin_price_history` (Awin-specific)
  - `integration.price_history` (unified, NEW)
- **Triggers:**
  - Log on price change OR stock status change
  - Captures: `price_cents`, `in_stock`, `stock_quantity`, `recorded_at`

### 8.8 Cleanup Migrations

**Schema Cleanup Journey:**
- **Migration:** `safe_partial_cleanup` → `comprehensive_view_aware_cleanup` → `minimal_safe_cleanup`
- **Problem:** Legacy fields with view dependencies
- **Solution:** Drop dependent views → Remove fields → Recreate views
- **Removed:** `buyer_id` from transactions, backup tables, unused indexes

### 8.9 Encryption Strategy

**Sensitive Data Protection:**
- **Fields:** `api_key_encrypted`, `password_hash`, `value_encrypted`
- **Method:** Fernet encryption (symmetric)
- **Key:** `FIELD_ENCRYPTION_KEY` environment variable
- **PCI Compliance:** Credit cards removed entirely (tokenization instead)

---

## 9. Migration Issues & Inconsistencies

### 9.1 Schema Naming Conflicts

**Issue:** `sales` vs `selling` vs `transactions`
- **History:**
  1. Initial: `sales` schema (transactions table)
  2. StockX: `selling` schema (stockx_listings, stockx_orders)
  3. Rename: `sales` → `transactions`, `selling` → `platforms`
- **Current State:** `transactions` schema for orders, `platforms` schema for platform-specific tables
- **Risk:** Code may reference old schema names

### 9.2 Multiple Cleanup Migrations

**Issue:** Three separate cleanup migrations attempted
- `052f62a0fc10_safe_partial_cleanup`
- `2025_08_30_0900_comprehensive_view_aware_cleanup`
- `2025_08_30_0915_minimal_safe_cleanup`
- **Problem:** Unclear which one is actually applied
- **Recommendation:** Review alembic_version table to confirm

### 9.3 Merge Migration

**Issue:** `930405202c44_merge_multiple_migration_heads`
- **Purpose:** Resolve multiple migration heads
- **Content:** Empty upgrade/downgrade
- **Risk:** May cause confusion in migration history

### 9.4 Price Data Duplication

**Current State:**
- `pricing.market_prices` - Still exists
- `integration.market_prices` - Legacy table, still exists
- `integration.price_sources` - NEW unified table

**Recommendation:**
- Migrate data from old tables to `price_sources`
- Drop old tables
- Update code to use new unified architecture

### 9.5 Size Table Schema

**Issue:** `sizes` table has no schema prefix
- **Location:** Public schema (default)
- **Expected:** Should be in `products` schema for consistency
- **Impact:** FK references use bare table name (`sizes.id`)

### 9.6 Enum Schema Inconsistency

**Issue:** Some enums have schema prefix, some don't
- **With Schema:** `integration.source_type_enum`, `integration.price_type_enum`, `integration.condition_enum`
- **Without Schema:** `inventory_status`, `sales_platform`, `auth.user_role`
- **Recommendation:** Standardize enum schema placement

### 9.7 Trigger Function Dependencies

**Issue:** Triggers reference functions that may not exist if migrations run out of order
- `calculate_inventory_analytics()` - No schema prefix
- `integration.track_awin_price_changes()`
- `integration.track_price_changes()`
- **Recommendation:** Add `CREATE OR REPLACE` and `IF EXISTS` checks

### 9.8 Style Code Length Evolution

**Issue:** `style_code` field changed size mid-lifecycle
- **Initial:** VARCHAR(50) in `add_product_enrichment_fields`
- **Update:** VARCHAR(200) in `increase_style_code_length`
- **Reason:** Multiple style codes concatenated
- **Impact:** Data may have been truncated initially

---

## 10. Consolidated Migration Strategy

### 10.1 Recommended Consolidation Order

1. **Initial Schema** (`7689c86d1945_initial_schema.py`)
2. **External IDs** (`1d7ca9ca7284_add_external_ids_to_inventory_item.py`)
3. **Pricing & Analytics** (`9233d7fa1f2a_create_pricing_and_analytics_schemas.py`)
4. **Cleanup** (Choose ONE: minimal_safe_cleanup recommended)
5. **Performance Indexes** (`2025_08_30_1000_add_performance_indexes.py`)
6. **Auth Schema** (`2025_08_30_1030_create_auth_schema.py`)
7. **Merge** (`930405202c44_merge_multiple_migration_heads.py`)
8. **Inventory Index** (`260ad1392824_add_inventory_created_at_index.py`)
9. **Market Prices (Legacy)** (`a82e22d786aa_create_market_prices_table.py`)
10. **Selling Schema** (`a1b2c3d4e5f6_create_selling_schema.py`)
11. **Supplier Accounts** (`2025_09_19_1300_create_supplier_accounts.py`)
12. **PCI Compliance** (`pci_compliance_payment_fields`)
13. **Business Intelligence** (`business_intelligence_fields`)
14. **Schema Rename** (`319a23ef9c05_rename_sales_selling_schemas.py`)
15. **Marketplace Data** (`887763befe74_add_marketplace_data_table.py`)
16. **Notion Fields** (`1fc1f0c9b64d_add_notion_sale_fields.py`)
17. **Multi-Platform Orders** (`84bc4d8b03ef_make_orders_table_multi_platform.py`)
18. **Remove Redundant** (`22679e4c7a0b_remove_redundant_sale_overview.py`)
19. **Product Enrichment** (`e6afd519c0a5_add_product_enrichment_fields.py`)
20. **Style Code Length** (`1eecf0cb7df3_increase_style_code_length.py`)
21. **Supplier History** (`3ef19f94d0a5_add_supplier_history_table.py`)
22. **Awin Products** (`6eef30096de3_add_awin_product_feed_tables.py`)
23. **Awin Enrichment** (`a7b8c9d0e1f2_add_awin_stockx_enrichment_tracking.py`)
24. **Price Sources** (`b2c8f3a1d9e4_create_price_sources_tables.py`) ⭐

### 10.2 Consolidation Principles

**Combine:**
- Initial schema + external IDs + pricing/analytics (base schema)
- All performance indexes (single migration)
- Supplier accounts + PCI compliance + business intelligence (supplier enhancements)
- Awin products + enrichment (Awin integration)

**Keep Separate:**
- Auth schema (optional module)
- Market prices (deprecated, consider removing)
- Schema renames (operational change)
- Price sources (major architectural change)

**Remove:**
- Multiple cleanup attempts (consolidate into one)
- Merge migration (not needed with linear history)

---

## 11. Summary Statistics

**Schemas:** 7 (core, products, integration, transactions, pricing, analytics, auth)
**Tables:** 35+
**Views:** 4 (2 analytics + 2 integration)
**Enums:** 6 (source_type, price_type, condition, inventory_status, sales_platform, user_role)
**Triggers:** 3 (inventory analytics, Awin price tracking, unified price tracking)
**Indexes:** 100+ (including partial and composite indexes)
**Foreign Keys:** 50+ relationships

---

## 12. Next Steps for Consolidated Migration

### 12.1 Pre-Consolidation Tasks

1. **Backup Current Database**
   ```bash
   pg_dump soleflip > backup_$(date +%Y%m%d).sql
   ```

2. **Export Current Schema**
   ```bash
   pg_dump --schema-only soleflip > current_schema.sql
   ```

3. **Document Current Data Volume**
   ```sql
   SELECT schemaname, tablename,
          pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
   FROM pg_tables
   WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

### 12.2 Consolidation Checklist

- [ ] Create single initial schema migration with ALL base tables
- [ ] Combine all index creation into logical groups
- [ ] Consolidate cleanup operations (remove duplicates)
- [ ] Merge Awin-related migrations
- [ ] Test consolidated migrations on empty database
- [ ] Test data migration from current schema
- [ ] Update models to match consolidated schema
- [ ] Update documentation

### 12.3 Code Review Required

**Models to Review:**
- `domains/products/models/product.py`
- `domains/products/models/inventory.py`
- `domains/integration/models/` (all)
- `domains/orders/models/order.py`
- `shared/database/models.py`

**References to Old Schema Names:**
- Search codebase for `sales.` (should be `transactions.`)
- Search codebase for `selling.` (should be `platforms.`)
- Search codebase for direct table references without schema

---

## Appendix A: Migration File List

1. `2025_08_14_0539_7689c86d1945_initial_schema.py`
2. `2025_08_14_1748_1d7ca9ca7284_add_external_ids_to_inventory_item.py`
3. `2025_08_27_1353_9233d7fa1f2a_create_pricing_and_analytics_schemas_.py`
4. `2025_08_30_0849_052f62a0fc10_safe_partial_cleanup_remove_independent_.py`
5. `2025_08_30_0900_comprehensive_view_aware_cleanup.py`
6. `2025_08_30_0915_minimal_safe_cleanup.py`
7. `2025_08_30_1000_add_performance_indexes.py`
8. `2025_08_30_1030_create_auth_schema.py`
9. `2025_08_31_1016_930405202c44_merge_multiple_migration_heads.py`
10. `2025_09_18_0622_260ad1392824_add_inventory_created_at_index.py`
11. `2025_09_18_0807_a82e22d786aa_create_market_prices_table_for_.py`
12. `2025_09_19_1200_create_selling_schema.py`
13. `2025_09_19_1300_create_supplier_accounts.py`
14. `2025_09_20_1500_pci_compliance_payment_fields.py`
15. `2025_09_27_1400_add_business_intelligence_fields.py`
16. `2025_09_27_1820_319a23ef9c05_rename_sales_selling_schemas_for_clarity.py`
17. `2025_09_29_1350_887763befe74_add_marketplace_data_table.py`
18. `2025_09_30_1328_1fc1f0c9b64d_add_notion_sale_fields.py`
19. `2025_10_01_0730_84bc4d8b03ef_make_orders_table_multi_platform_.py`
20. `2025_10_01_0816_22679e4c7a0b_remove_redundant_sale_overview_from_.py`
21. `2025_10_10_1911_e6afd519c0a5_add_product_enrichment_fields_simplified.py`
22. `2025_10_10_2002_1eecf0cb7df3_increase_style_code_length.py`
23. `2025_10_11_0835_3ef19f94d0a5_add_supplier_history_table.py`
24. `2025_10_11_1921_6eef30096de3_add_awin_product_feed_tables.py`
25. `2025_10_12_0940_add_awin_stockx_enrichment_tracking.py`
26. `2025_10_12_1400_b2c8f3a1d9e4_create_price_sources_tables.py`

---

## Appendix B: Key Design Patterns

### B.1 UUID as Primary Keys
- All tables use UUID for primary keys
- Generated via `gen_random_uuid()` PostgreSQL function
- Benefits: Distributed ID generation, no collisions, better security

### B.2 Timestamp Tracking
- Standard pattern: `created_at`, `updated_at`
- All timestamps use `TIMESTAMP(timezone=True)`
- Default: `server_default=sa.text('NOW()')` or `CURRENT_TIMESTAMP`

### B.3 Soft Deletes
- No explicit soft delete pattern observed
- Consider adding `deleted_at` for important entities

### B.4 Audit Trail
- `system_logs` table for application-level logging
- Trigger-based price history tracking
- No comprehensive audit trail for all tables

### B.5 Metadata Storage
- JSONB columns for flexible data: `metadata`, `enrichment_data`, `platform_specific`, `raw_data`, `tags`
- Benefits: Flexibility without schema changes, efficient querying with GIN indexes

---

## Appendix C: Recommended Improvements

### C.1 Missing Features

1. **Audit Trail**
   - Add `created_by`, `updated_by` UUID FK to `auth.users`
   - Add versioning for critical tables (products, inventory)

2. **Soft Deletes**
   - Add `deleted_at` TIMESTAMP to important entities
   - Add `is_deleted` BOOLEAN for easier querying

3. **Full-Text Search**
   - Add GIN indexes on text columns
   - Add `tsvector` columns for product search

4. **Materialized Views**
   - Consider materializing `profit_opportunities_v2` for performance
   - Refresh strategy: ON COMMIT or scheduled

5. **Partitioning**
   - Partition `price_history` by date (monthly/yearly)
   - Partition `system_logs` by date
   - Partition `transactions` by date

### C.2 Performance Optimization

1. **Missing Indexes**
   - `products.products.ean` (frequent lookups)
   - `products.inventory` composite index on (`product_id`, `size_id`, `status`)
   - `transactions.orders` composite index on (`platform_id`, `sold_at`)

2. **Query Optimization**
   - Review N+1 query patterns in ORM code
   - Add `select_related` / `joinedload` hints
   - Consider `EXPLAIN ANALYZE` for slow queries

3. **Connection Pooling**
   - Current: Async SQLAlchemy with pooling
   - Recommendation: Monitor pool exhaustion

### C.3 Data Integrity

1. **Missing Check Constraints**
   - `inventory.quantity >= 0`
   - `products.retail_price >= 0`
   - `orders.sale_price > 0`

2. **Missing NOT NULL Constraints**
   - Many optional fields should be required
   - Review business logic requirements

3. **Referential Integrity**
   - All FKs defined correctly
   - Consider adding CHECK constraints for status enums

---

## Appendix D: Glossary

**PAS** - Profit per Active day (Shelf day)
**ROI** - Return on Investment
**EAN** - European Article Number (barcode)
**GTIN** - Global Trade Item Number
**MPN** - Manufacturer Part Number
**SKU** - Stock Keeping Unit
**Ask Price** - Seller's asking price
**Bid Price** - Buyer's offered price
**StockX** - Resale marketplace for sneakers
**Awin** - Affiliate marketing network
**PCI DSS** - Payment Card Industry Data Security Standard
**DDD** - Domain-Driven Design
**JSONB** - PostgreSQL JSON Binary format
**UUID** - Universally Unique Identifier
**FK** - Foreign Key
**GIN** - Generalized Inverted Index (PostgreSQL)
