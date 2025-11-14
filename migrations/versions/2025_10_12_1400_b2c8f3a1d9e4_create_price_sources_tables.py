"""create_price_sources_tables

Revision ID: b2c8f3a1d9e4
Revises: a7b8c9d0e1f2
Create Date: 2025-10-12 14:00:00.000000

Creates unified price sources architecture to eliminate product data redundancy
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c8f3a1d9e4'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # 1. CREATE ENUMS
    # ========================================================================

    # Source type enum
    source_type_enum = postgresql.ENUM(
        'stockx', 'awin', 'ebay', 'goat', 'klekt', 'restocks', 'stockxapi',
        name='source_type_enum',
        schema='integration'
    )
    source_type_enum.create(op.get_bind(), checkfirst=True)

    # Price type enum
    price_type_enum = postgresql.ENUM(
        'resale', 'retail', 'auction', 'wholesale',
        name='price_type_enum',
        schema='integration'
    )
    price_type_enum.create(op.get_bind(), checkfirst=True)

    # Condition enum
    condition_enum = postgresql.ENUM(
        'new', 'like_new', 'used_excellent', 'used_good', 'used_fair', 'deadstock',
        name='condition_enum',
        schema='integration'
    )
    condition_enum.create(op.get_bind(), checkfirst=True)

    # ========================================================================
    # 2. CREATE PRICE_SOURCES TABLE
    # ========================================================================

    op.create_table(
        'price_sources',

        # Primary key
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),

        # Product relationship
        sa.Column('product_id', sa.UUID(), nullable=False),

        # Size relationship (for size-specific pricing)
        sa.Column('size_id', sa.UUID(), nullable=True),

        # Source identification
        sa.Column('source_type', source_type_enum, nullable=False),
        sa.Column('source_product_id', sa.String(100), nullable=False),
        sa.Column('source_name', sa.String(200), nullable=True),  # e.g., "size?Official DE", "StockX"

        # Price information
        sa.Column('price_type', price_type_enum, nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), server_default='EUR', nullable=False),

        # Stock information
        sa.Column('stock_quantity', sa.Integer(), nullable=True),
        sa.Column('in_stock', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('condition', condition_enum, server_default='new', nullable=True),

        # URLs and links
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('affiliate_link', sa.Text(), nullable=True),

        # Supplier relationship (for retail sources)
        sa.Column('supplier_id', sa.UUID(), nullable=True),

        # Additional metadata (flexible JSONB for source-specific data)
        sa.Column('metadata', sa.JSON(), nullable=True),

        # Timestamps
        sa.Column('last_updated', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['product_id'],
            ['products.products.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['supplier_id'],
            ['core.suppliers.id'],
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['size_id'],
            ['sizes.id'],  # Correct table reference
            ondelete='SET NULL'
        ),

        schema='integration'
    )

    # Unique constraints using partial indexes (handles NULL properly)
    # With size: product + source + source_id + size must be unique
    op.create_index(
        'uq_price_source_with_size',
        'price_sources',
        ['product_id', 'source_type', 'source_product_id', 'size_id'],
        schema='integration',
        unique=True,
        postgresql_where=sa.text('size_id IS NOT NULL')
    )

    # Without size: product + source + source_id must be unique
    op.create_index(
        'uq_price_source_without_size',
        'price_sources',
        ['product_id', 'source_type', 'source_product_id'],
        schema='integration',
        unique=True,
        postgresql_where=sa.text('size_id IS NULL')
    )

    # ========================================================================
    # 3. CREATE INDEXES FOR PERFORMANCE
    # ========================================================================

    # Core lookup indexes
    op.create_index('idx_price_sources_product_id', 'price_sources', ['product_id'], schema='integration')
    op.create_index('idx_price_sources_source_type', 'price_sources', ['source_type'], schema='integration')
    op.create_index('idx_price_sources_price_type', 'price_sources', ['price_type'], schema='integration')

    # Composite indexes for common queries
    op.create_index(
        'idx_price_sources_product_source',
        'price_sources',
        ['product_id', 'source_type'],
        schema='integration'
    )
    op.create_index(
        'idx_price_sources_source_price_type',
        'price_sources',
        ['source_type', 'price_type'],
        schema='integration'
    )

    # Stock and availability
    op.create_index('idx_price_sources_in_stock', 'price_sources', ['in_stock'], schema='integration')
    op.create_index('idx_price_sources_supplier', 'price_sources', ['supplier_id'], schema='integration')
    op.create_index('idx_price_sources_size', 'price_sources', ['size_id'], schema='integration')

    # Timestamps for stale data detection
    op.create_index('idx_price_sources_last_updated', 'price_sources', ['last_updated'], schema='integration')

    # Price range queries
    op.create_index('idx_price_sources_price_cents', 'price_sources', ['price_cents'], schema='integration')

    # ========================================================================
    # PERFORMANCE: Optimized indexes for profit opportunities query
    # ========================================================================

    # Composite index for profit query (retail prices)
    op.create_index(
        'idx_price_sources_retail_active',
        'price_sources',
        ['product_id', 'size_id', 'price_cents'],
        schema='integration',
        postgresql_where=sa.text("price_type = 'retail' AND in_stock = true")
    )

    # Composite index for profit query (resale prices)
    op.create_index(
        'idx_price_sources_resale_active',
        'price_sources',
        ['product_id', 'size_id', 'price_cents'],
        schema='integration',
        postgresql_where=sa.text("price_type = 'resale' AND in_stock = true")
    )

    # ========================================================================
    # 4. CREATE PRICE_HISTORY TABLE
    # ========================================================================

    op.create_table(
        'price_history',

        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('price_source_id', sa.UUID(), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('in_stock', sa.Boolean(), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['price_source_id'],
            ['integration.price_sources.id'],
            ondelete='CASCADE'
        ),

        schema='integration'
    )

    # Indexes for historical queries
    op.create_index('idx_price_history_source', 'price_history', ['price_source_id'], schema='integration')
    op.create_index('idx_price_history_recorded', 'price_history', ['recorded_at'], schema='integration')
    op.create_index(
        'idx_price_history_source_date',
        'price_history',
        ['price_source_id', 'recorded_at'],
        schema='integration'
    )

    # ========================================================================
    # 5. CREATE TRIGGER FOR AUTOMATIC PRICE HISTORY
    # ========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION integration.track_price_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only log if price or stock status changed
            IF OLD.price_cents IS DISTINCT FROM NEW.price_cents
               OR OLD.in_stock IS DISTINCT FROM NEW.in_stock THEN
                INSERT INTO integration.price_history
                    (price_source_id, price_cents, in_stock, stock_quantity, recorded_at)
                VALUES
                    (NEW.id, NEW.price_cents, NEW.in_stock, NEW.stock_quantity, NOW());
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER price_change_trigger
        AFTER UPDATE ON integration.price_sources
        FOR EACH ROW
        EXECUTE FUNCTION integration.track_price_changes();
    """)

    # ========================================================================
    # 6. ADD HELPER VIEWS FOR COMMON QUERIES
    # ========================================================================

    # View: Latest prices per product and source
    op.execute("""
        CREATE OR REPLACE VIEW integration.latest_prices AS
        SELECT DISTINCT ON (product_id, source_type)
            ps.*,
            p.name as product_name,
            p.sku as product_sku,
            p.ean as product_ean,
            b.name as brand_name,
            s.name as supplier_name
        FROM integration.price_sources ps
        JOIN products.products p ON ps.product_id = p.id
        LEFT JOIN core.brands b ON p.brand_id = b.id
        LEFT JOIN core.suppliers s ON ps.supplier_id = s.id
        WHERE ps.in_stock = true
        ORDER BY product_id, source_type, last_updated DESC;
    """)

    # View: Profit opportunities (retail vs resale)
    op.execute("""
        CREATE OR REPLACE VIEW integration.profit_opportunities_v2 AS
        SELECT
            p.id as product_id,
            p.name as product_name,
            p.sku as product_sku,
            p.ean as product_ean,
            b.name as brand_name,

            -- Size information (retail)
            s_retail.value as retail_size_value,
            s_retail.region as retail_size_region,

            -- Size information (resale)
            s_resale.value as resale_size_value,
            s_resale.region as resale_size_region,

            -- Standardized size (for matching)
            s_retail.standardized_value as standardized_size,

            -- Retail price (from Awin, eBay, etc.)
            ps_retail.id as retail_price_source_id,
            ps_retail.source_type as retail_source,
            ps_retail.source_name as retail_source_name,
            ps_retail.price_cents as retail_price_cents,
            ps_retail.price_cents / 100.0 as retail_price_eur,
            ps_retail.supplier_id as retail_supplier_id,
            ps_retail.affiliate_link as retail_affiliate_link,
            ps_retail.stock_quantity as retail_stock_quantity,

            -- Resale price (from StockX, GOAT, etc.)
            ps_resale.id as resale_price_source_id,
            ps_resale.source_type as resale_source,
            ps_resale.source_name as resale_source_name,
            ps_resale.price_cents as resale_price_cents,
            ps_resale.price_cents / 100.0 as resale_price_eur,

            -- Profit calculation
            (ps_resale.price_cents - ps_retail.price_cents) as profit_cents,
            (ps_resale.price_cents - ps_retail.price_cents) / 100.0 as profit_eur,
            ROUND(
                ((ps_resale.price_cents - ps_retail.price_cents)::numeric
                / NULLIF(ps_retail.price_cents, 0)::numeric * 100),
                1
            ) as profit_percentage,

            -- Combined opportunity score (profit × ROI)
            ROUND(
                (ps_resale.price_cents - ps_retail.price_cents)::numeric / 100.0 *
                ((ps_resale.price_cents - ps_retail.price_cents)::numeric / NULLIF(ps_retail.price_cents, 0)::numeric),
                2
            ) as opportunity_score

        FROM products.products p
        JOIN core.brands b ON p.brand_id = b.id

        -- Retail prices
        JOIN integration.price_sources ps_retail
            ON ps_retail.product_id = p.id
            AND ps_retail.price_type = 'retail'
            AND ps_retail.in_stock = true

        -- Retail sizes (optional)
        LEFT JOIN sizes s_retail ON ps_retail.size_id = s_retail.id

        -- Resale prices
        JOIN integration.price_sources ps_resale
            ON ps_resale.product_id = p.id
            AND ps_resale.price_type = 'resale'
            AND ps_resale.in_stock = true

        -- Resale sizes (optional)
        LEFT JOIN sizes s_resale ON ps_resale.size_id = s_resale.id

        WHERE ps_resale.price_cents > ps_retail.price_cents  -- Only profitable opportunities
          AND (
              -- Match via standardized_value (e.g., EU 38 = US 5.5)
              s_retail.standardized_value = s_resale.standardized_value
              -- OR both have no size (generic products)
              OR (ps_retail.size_id IS NULL AND ps_resale.size_id IS NULL)
          )
        ORDER BY profit_eur DESC;
    """)

    # ========================================================================
    # 7. ADD COLUMN COMMENTS FOR DOCUMENTATION
    # ========================================================================

    op.execute("""
        COMMENT ON TABLE integration.price_sources IS
        'Unified price sources from multiple providers (StockX, Awin, eBay, etc.)';
    """)

    op.execute("""
        COMMENT ON COLUMN integration.price_sources.source_type IS
        'Type of price source: stockx, awin, ebay, goat, klekt';
    """)

    op.execute("""
        COMMENT ON COLUMN integration.price_sources.price_type IS
        'Type of price: resale (secondary market), retail (primary market), auction, wholesale';
    """)

    op.execute("""
        COMMENT ON COLUMN integration.price_sources.metadata IS
        'Flexible JSONB field for source-specific data (e.g., StockX variant details, Awin merchant info)';
    """)

    op.execute("""
        COMMENT ON COLUMN integration.price_sources.size_id IS
        'Optional FK to sizes table for size-specific pricing (e.g., StockX has different prices per size)';
    """)

    # ========================================================================
    # 8. DATA VALIDATION CONSTRAINTS
    # ========================================================================

    # Price must be positive
    op.execute("""
        ALTER TABLE integration.price_sources
        ADD CONSTRAINT chk_price_positive CHECK (price_cents >= 0);
    """)

    # Stock quantity must be positive if specified
    op.execute("""
        ALTER TABLE integration.price_sources
        ADD CONSTRAINT chk_stock_positive
        CHECK (stock_quantity IS NULL OR stock_quantity >= 0);
    """)

    # Currency must be valid (3 uppercase letters)
    op.execute("""
        ALTER TABLE integration.price_sources
        ADD CONSTRAINT chk_currency_valid CHECK (currency ~ '^[A-Z]{3}$');
    """)

    # last_updated must be in the past
    op.execute("""
        ALTER TABLE integration.price_sources
        ADD CONSTRAINT chk_last_updated_past
        CHECK (last_updated IS NULL OR last_updated <= NOW());
    """)


def downgrade():
    # Drop views
    op.execute("DROP VIEW IF EXISTS integration.profit_opportunities_v2")
    op.execute("DROP VIEW IF EXISTS integration.latest_prices")

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS price_change_trigger ON integration.price_sources")
    op.execute("DROP FUNCTION IF EXISTS integration.track_price_changes()")

    # Drop tables
    op.drop_table('price_history', schema='integration')
    op.drop_table('price_sources', schema='integration')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS integration.condition_enum")
    op.execute("DROP TYPE IF EXISTS integration.price_type_enum")
    op.execute("DROP TYPE IF EXISTS integration.source_type_enum")
