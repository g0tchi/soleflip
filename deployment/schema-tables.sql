-- ============================================================================
-- Soleflip Database Schema - PostgreSQL Version
-- Converted from Gibson AI MySQL Schema
-- Total: 54 Tables across 14 Modules
-- ============================================================================

-- ============================================================================
-- ENUM TYPES (PostgreSQL requires explicit type definitions)
-- ============================================================================

CREATE TYPE gender_type AS ENUM ('infant', 'men', 'toddler', 'unisex', 'women', 'youth');
CREATE TYPE size_standard_type AS ENUM ('cm', 'eu', 'jp', 'uk', 'us');
CREATE TYPE condition_type AS ENUM ('new', 'refurbished', 'used');
CREATE TYPE batch_status_type AS ENUM ('completed', 'failed', 'pending', 'processing');
CREATE TYPE record_status_type AS ENUM ('failed', 'pending', 'processed');
CREATE TYPE source_type AS ENUM ('api', 'csv');
CREATE TYPE width_type AS ENUM ('2e', '4e', 'b', 'd', 'ee', 'eee');

-- ============================================================================
-- CATALOG MODULE (3 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS catalog.product_category_mapping (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (product_id, category_id)
);
CREATE INDEX idx_catalog_product_category_mapping_category ON catalog.product_category_mapping(category_id);
COMMENT ON TABLE catalog.product_category_mapping IS 'Maps products to multiple categories';

CREATE TABLE IF NOT EXISTS catalog.product_platform_availability (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    platform_id BIGINT NOT NULL,
    available_from TIMESTAMPTZ NOT NULL,
    available_to TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (product_id, platform_id)
);
CREATE INDEX idx_catalog_product_platform_platform ON catalog.product_platform_availability(platform_id);
COMMENT ON TABLE catalog.product_platform_availability IS 'Tracks product availability across platforms';

CREATE TABLE IF NOT EXISTS catalog.product_variant (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    size_id BIGINT NOT NULL,
    color VARCHAR(50),
    condition condition_type DEFAULT 'new',
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_catalog_product_variant_product ON catalog.product_variant(product_id);
CREATE INDEX idx_catalog_product_variant_size ON catalog.product_variant(size_id);
COMMENT ON TABLE catalog.product_variant IS 'Product variant details like size, color, and condition';

-- ============================================================================
-- COMPLIANCE MODULE (3 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS compliance.business_rule (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    rule_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    conditions JSONB,
    actions JSONB,
    active BOOLEAN NOT NULL DEFAULT true,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE compliance.business_rule IS 'Business rules with conditions and actions';

CREATE TABLE IF NOT EXISTS compliance.data_retention_policy (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    entity_name VARCHAR(255) NOT NULL UNIQUE,
    retention_period_days INT NOT NULL,
    effective_date DATE NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE compliance.data_retention_policy IS 'Data retention policies for entities';

CREATE TABLE IF NOT EXISTS compliance.user_permission (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    user_identifier UUID NOT NULL,
    permission_key VARCHAR(255) NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (user_identifier, permission_key)
);
COMMENT ON TABLE compliance.user_permission IS 'User permissions mapping';

-- ============================================================================
-- CORE MODULE (8 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS core.brand (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(255) NOT NULL UNIQUE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE core.brand IS 'Brand catalog';

CREATE TABLE IF NOT EXISTS core.category (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    parent_id BIGINT,
    path VARCHAR(1024) NOT NULL DEFAULT '/',
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    FOREIGN KEY (parent_id) REFERENCES core.category(id)
);
CREATE INDEX idx_core_category_parent ON core.category(parent_id);
COMMENT ON TABLE core.category IS 'Hierarchical product categories';

CREATE TABLE IF NOT EXISTS core.size_conversion (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    gender gender_type NOT NULL,
    from_standard size_standard_type NOT NULL,
    from_size DECIMAL(4, 1) NOT NULL,
    to_standard size_standard_type NOT NULL,
    to_size DECIMAL(4, 1) NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (gender, from_standard, from_size, to_standard, to_size)
);
COMMENT ON TABLE core.size_conversion IS 'Size conversion table between different standards';

CREATE TABLE IF NOT EXISTS core.size_master (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    gender gender_type NOT NULL,
    size_decimal DECIMAL(4, 1) NOT NULL,
    us_size DECIMAL(4, 1) NOT NULL,
    eu_size DECIMAL(4, 1) NOT NULL,
    uk_size DECIMAL(4, 1) NOT NULL,
    cm_size DECIMAL(4, 1) NOT NULL,
    jp_size DECIMAL(4, 1) NOT NULL,
    length_cm DECIMAL(5, 2),
    length_in DECIMAL(5, 2),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (gender, size_decimal)
);
COMMENT ON TABLE core.size_master IS 'Master size table with all size standards';

CREATE TABLE IF NOT EXISTS core.supplier (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    contact_info TEXT,
    rating DECIMAL(3, 2),
    performance_metrics JSONB,
    vat_rate DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    return_policy TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE core.supplier IS 'Supplier information and metrics';

CREATE TABLE IF NOT EXISTS core.system_batch_operation (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    operation_id VARCHAR(255) NOT NULL UNIQUE,
    operation_type VARCHAR(255) NOT NULL,
    total_records INT,
    processed_records INT,
    failed_records INT,
    status batch_status_type DEFAULT 'pending',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE core.system_batch_operation IS 'Batch operation tracking';

CREATE TABLE IF NOT EXISTS core.system_config (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT,
    is_encrypted BOOLEAN NOT NULL DEFAULT false,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE core.system_config IS 'System configuration key-value store';

CREATE TABLE IF NOT EXISTS core.system_event_sourcing (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    event_id VARCHAR(255) NOT NULL UNIQUE,
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id BIGINT,
    event_type VARCHAR(255) NOT NULL,
    event_data JSONB,
    event_version INT NOT NULL DEFAULT 1,
    occurred_at TIMESTAMPTZ NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE core.system_event_sourcing IS 'Event sourcing for system events';

-- ============================================================================
-- INTEGRATION MODULE (3 tables)
-- ============================================================================

CREATE TABLE IF NOT EXISTS integration.event_store (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    event_id VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(255) NOT NULL,
    aggregate_id BIGINT,
    event_data JSONB,
    correlation_id VARCHAR(255),
    causation_id VARCHAR(255),
    event_timestamp TIMESTAMPTZ NOT NULL,
    version INT DEFAULT 1,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE integration.event_store IS 'Event store for integration events';

CREATE TABLE IF NOT EXISTS integration.import_batch (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    source_type source_type NOT NULL,
    source_file VARCHAR(255),
    record_count INT,
    status batch_status_type DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE integration.import_batch IS 'Import batch tracking';

CREATE TABLE IF NOT EXISTS integration.import_record (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    batch_id BIGINT NOT NULL,
    source_data JSONB,
    processed_data JSONB,
    validation_errors JSONB,
    status record_status_type DEFAULT 'pending',
    error_message TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    FOREIGN KEY (batch_id) REFERENCES integration.import_batch(id)
);
CREATE INDEX idx_integration_import_record_batch ON integration.import_record(batch_id);
COMMENT ON TABLE integration.import_record IS 'Individual import records';

-- ============================================================================
-- OPERATIONS MODULE (1 table)
-- ============================================================================

CREATE TABLE IF NOT EXISTS operations.supplier_platform_integration (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    supplier_id BIGINT NOT NULL,
    platform_id BIGINT NOT NULL,
    integration_details JSONB,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ,
    UNIQUE (supplier_id, platform_id)
);
CREATE INDEX idx_operations_supplier_platform_platform ON operations.supplier_platform_integration(platform_id);
COMMENT ON TABLE operations.supplier_platform_integration IS 'Supplier-platform integration mapping';

-- ============================================================================
-- PLATFORM MODULE (1 table)
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform.marketplace (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(255) NOT NULL UNIQUE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
COMMENT ON TABLE platform.marketplace IS 'Marketplace platforms (StockX, eBay, GOAT, etc.)';

-- ============================================================================
-- PRODUCT MODULE (3 tables + main product table)
-- ============================================================================

CREATE TABLE IF NOT EXISTS product.product (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    sku VARCHAR(100) NOT NULL UNIQUE,
    brand_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    retail_price DECIMAL(10, 2),
    avg_resale_price DECIMAL(10, 2),
    release_date DATE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_product_brand ON product.product(brand_id);
CREATE INDEX idx_product_product_category ON product.product(category_id);
COMMENT ON TABLE product.product IS 'Main product catalog';

CREATE TABLE IF NOT EXISTS product.size_availability_range (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    min_size DECIMAL(4, 1) NOT NULL,
    max_size DECIMAL(4, 1) NOT NULL,
    discontinued_sizes JSONB,
    half_sizes_available BOOLEAN NOT NULL DEFAULT true,
    size_popularity_score DECIMAL(5, 2),
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_size_availability_product ON product.size_availability_range(product_id);
COMMENT ON TABLE product.size_availability_range IS 'Size availability and popularity for products';

CREATE TABLE IF NOT EXISTS product.size_profile (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version INT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMPTZ,
    product_id BIGINT NOT NULL,
    standard_size_id BIGINT NOT NULL,
    adjustment DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    width width_type NOT NULL,
    fit_notes TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_updated TIMESTAMPTZ
);
CREATE INDEX idx_product_size_profile_product ON product.size_profile(product_id);
CREATE INDEX idx_product_size_profile_size ON product.size_profile(standard_size_id);
COMMENT ON TABLE product.size_profile IS 'Product size fit profiles and adjustments';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS
-- Foreign keys are added after all tables are created to avoid dependency issues
-- ============================================================================

-- Catalog module foreign keys
ALTER TABLE catalog.product_category_mapping
    ADD CONSTRAINT fk_catalog_product_category_product
    FOREIGN KEY (product_id) REFERENCES product.product(id);

ALTER TABLE catalog.product_category_mapping
    ADD CONSTRAINT fk_catalog_product_category_category
    FOREIGN KEY (category_id) REFERENCES core.category(id);

ALTER TABLE catalog.product_platform_availability
    ADD CONSTRAINT fk_catalog_product_platform_product
    FOREIGN KEY (product_id) REFERENCES product.product(id);

ALTER TABLE catalog.product_platform_availability
    ADD CONSTRAINT fk_catalog_product_platform_platform
    FOREIGN KEY (platform_id) REFERENCES platform.marketplace(id);

ALTER TABLE catalog.product_variant
    ADD CONSTRAINT fk_catalog_product_variant_product
    FOREIGN KEY (product_id) REFERENCES product.product(id);

ALTER TABLE catalog.product_variant
    ADD CONSTRAINT fk_catalog_product_variant_size
    FOREIGN KEY (size_id) REFERENCES core.size_master(id);

-- Operations module foreign keys
ALTER TABLE operations.supplier_platform_integration
    ADD CONSTRAINT fk_operations_supplier_platform_supplier
    FOREIGN KEY (supplier_id) REFERENCES core.supplier(id);

ALTER TABLE operations.supplier_platform_integration
    ADD CONSTRAINT fk_operations_supplier_platform_platform
    FOREIGN KEY (platform_id) REFERENCES platform.marketplace(id);

-- Product module foreign keys
ALTER TABLE product.product
    ADD CONSTRAINT fk_product_product_brand
    FOREIGN KEY (brand_id) REFERENCES core.brand(id);

ALTER TABLE product.product
    ADD CONSTRAINT fk_product_product_category
    FOREIGN KEY (category_id) REFERENCES core.category(id);

ALTER TABLE product.size_availability_range
    ADD CONSTRAINT fk_product_size_availability_product
    FOREIGN KEY (product_id) REFERENCES product.product(id);

ALTER TABLE product.size_profile
    ADD CONSTRAINT fk_product_size_profile_product
    FOREIGN KEY (product_id) REFERENCES product.product(id);

ALTER TABLE product.size_profile
    ADD CONSTRAINT fk_product_size_profile_size
    FOREIGN KEY (standard_size_id) REFERENCES core.size_master(id);

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATE OF date_updated
-- PostgreSQL doesn't support ON UPDATE CURRENT_TIMESTAMP, so we use triggers
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_updated = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with date_updated column
CREATE TRIGGER trg_catalog_product_category_mapping_updated
    BEFORE UPDATE ON catalog.product_category_mapping
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_catalog_product_platform_availability_updated
    BEFORE UPDATE ON catalog.product_platform_availability
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_catalog_product_variant_updated
    BEFORE UPDATE ON catalog.product_variant
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_compliance_business_rule_updated
    BEFORE UPDATE ON compliance.business_rule
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_compliance_data_retention_policy_updated
    BEFORE UPDATE ON compliance.data_retention_policy
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_compliance_user_permission_updated
    BEFORE UPDATE ON compliance.user_permission
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_brand_updated
    BEFORE UPDATE ON core.brand
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_category_updated
    BEFORE UPDATE ON core.category
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_size_conversion_updated
    BEFORE UPDATE ON core.size_conversion
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_size_master_updated
    BEFORE UPDATE ON core.size_master
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_supplier_updated
    BEFORE UPDATE ON core.supplier
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_system_batch_operation_updated
    BEFORE UPDATE ON core.system_batch_operation
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_system_config_updated
    BEFORE UPDATE ON core.system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_core_system_event_sourcing_updated
    BEFORE UPDATE ON core.system_event_sourcing
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_integration_event_store_updated
    BEFORE UPDATE ON integration.event_store
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_integration_import_batch_updated
    BEFORE UPDATE ON integration.import_batch
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_integration_import_record_updated
    BEFORE UPDATE ON integration.import_record
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_operations_supplier_platform_integration_updated
    BEFORE UPDATE ON operations.supplier_platform_integration
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_platform_marketplace_updated
    BEFORE UPDATE ON platform.marketplace
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_product_updated
    BEFORE UPDATE ON product.product
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_size_availability_range_updated
    BEFORE UPDATE ON product.size_availability_range
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

CREATE TRIGGER trg_product_size_profile_updated
    BEFORE UPDATE ON product.size_profile
    FOR EACH ROW EXECUTE FUNCTION update_updated_timestamp();

-- ============================================================================
-- INDEXES FOR COMMON QUERIES
-- ============================================================================

-- UUID indexes for fast lookups
CREATE INDEX idx_catalog_product_category_uuid ON catalog.product_category_mapping(uuid);
CREATE INDEX idx_core_brand_uuid ON core.brand(uuid);
CREATE INDEX idx_core_category_uuid ON core.category(uuid);
CREATE INDEX idx_product_product_uuid ON product.product(uuid);

-- Soft delete indexes (for queries filtering out deleted records)
CREATE INDEX idx_core_brand_deleted ON core.brand(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_core_category_deleted ON core.category(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_product_product_deleted ON product.product(deleted_at) WHERE deleted_at IS NULL;

-- Tenant isolation indexes
CREATE INDEX idx_core_brand_tenant ON core.brand(tenant_id);
CREATE INDEX idx_core_category_tenant ON core.category(tenant_id);
CREATE INDEX idx_product_product_tenant ON product.product(tenant_id);

-- ============================================================================
-- SUMMARY
-- ============================================================================
-- Total Tables Created: 23 (out of 54 from Gibson - this is Phase 1)
--
-- Modules Completed:
-- ✅ catalog (3 tables)
-- ✅ compliance (3 tables)
-- ✅ core (8 tables)
-- ✅ integration (3 tables)
-- ✅ operations (1 table)
-- ✅ platform (1 table)
-- ✅ product (4 tables)
--
-- Remaining Modules (31 tables):
-- ⏳ analytics (9 tables)
-- ⏳ financial (3 tables)
-- ⏳ logging (3 tables)
-- ⏳ pricing (7 tables)
-- ⏳ realtime (1 table)
-- ⏳ supplier (3 tables)
-- ⏳ transaction (4 tables)
--
-- Next: Run this script, test, then add remaining modules
-- ============================================================================
