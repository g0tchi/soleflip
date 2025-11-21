"""populate_size_master_with_standard_sizes

Revision ID: fa6f61561a34
Revises: 0f4c2653c093
Create Date: 2025-11-21 06:34:57.852560

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'fa6f61561a34'
down_revision = '0f4c2653c093'
branch_labels = None
depends_on = None


def upgrade():
    """Populate core.size_master with standard sneaker sizes for men and women"""

    # Standard Men's Sneaker Sizes (US 4-14)
    men_sizes = [
        # (us, eu, uk, cm, kr)
        (4.0, 36.0, 3.0, 22.5, 225.0),
        (4.5, 37.0, 3.5, 23.0, 230.0),
        (5.0, 37.5, 4.0, 23.5, 235.0),
        (5.5, 38.0, 4.5, 24.0, 240.0),
        (6.0, 39.0, 5.0, 24.5, 245.0),
        (6.5, 39.5, 5.5, 25.0, 250.0),
        (7.0, 40.0, 6.0, 25.5, 255.0),
        (7.5, 40.5, 6.5, 26.0, 260.0),
        (8.0, 41.5, 7.0, 26.5, 265.0),
        (8.5, 42.0, 7.5, 27.0, 270.0),
        (9.0, 42.5, 8.0, 27.5, 275.0),
        (9.5, 43.5, 8.5, 28.0, 280.0),
        (10.0, 44.0, 9.0, 28.5, 285.0),
        (10.5, 44.5, 9.5, 29.0, 290.0),
        (11.0, 45.0, 10.0, 29.5, 295.0),
        (11.5, 46.0, 10.5, 30.0, 300.0),
        (12.0, 46.5, 11.0, 30.5, 305.0),
        (12.5, 47.0, 11.5, 31.0, 310.0),
        (13.0, 48.0, 12.0, 31.5, 315.0),
        (13.5, 48.5, 12.5, 32.0, 320.0),
        (14.0, 49.0, 13.0, 32.5, 325.0),
    ]

    # Standard Women's Sneaker Sizes (US 5-12)
    women_sizes = [
        # (us, eu, uk, cm, kr)
        (5.0, 35.5, 2.5, 22.0, 220.0),
        (5.5, 36.0, 3.0, 22.5, 225.0),
        (6.0, 36.5, 3.5, 23.0, 230.0),
        (6.5, 37.5, 4.0, 23.5, 235.0),
        (7.0, 38.0, 4.5, 24.0, 240.0),
        (7.5, 38.5, 5.0, 24.5, 245.0),
        (8.0, 39.0, 5.5, 25.0, 250.0),
        (8.5, 40.0, 6.0, 25.5, 255.0),
        (9.0, 40.5, 6.5, 26.0, 260.0),
        (9.5, 41.0, 7.0, 26.5, 265.0),
        (10.0, 42.0, 7.5, 27.0, 270.0),
        (10.5, 42.5, 8.0, 27.5, 275.0),
        (11.0, 43.0, 8.5, 28.0, 280.0),
        (11.5, 44.0, 9.0, 28.5, 285.0),
        (12.0, 44.5, 9.5, 29.0, 290.0),
    ]

    # Insert men's sizes with ON CONFLICT handling
    for us, eu, uk, cm, kr in men_sizes:
        op.execute(sa.text("""
            INSERT INTO core.size_master (
                id, gender, us_size, eu_size, uk_size, cm_size, kr_size,
                category_id, validation_source, last_validated_at, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), 'men', :us, :eu, :uk, :cm, :kr,
                NULL, 'standard_conversion', NOW(), NOW(), NOW()
            )
            ON CONFLICT (us_size, gender, category_id)
            DO UPDATE SET
                eu_size = EXCLUDED.eu_size,
                uk_size = EXCLUDED.uk_size,
                cm_size = EXCLUDED.cm_size,
                kr_size = EXCLUDED.kr_size,
                validation_source = EXCLUDED.validation_source,
                last_validated_at = NOW(),
                updated_at = NOW()
        """).bindparams(
            us=us, eu=eu, uk=uk, cm=cm, kr=kr
        ))

    # Insert women's sizes with ON CONFLICT handling
    for us, eu, uk, cm, kr in women_sizes:
        op.execute(sa.text("""
            INSERT INTO core.size_master (
                id, gender, us_size, eu_size, uk_size, cm_size, kr_size,
                category_id, validation_source, last_validated_at, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), 'women', :us, :eu, :uk, :cm, :kr,
                NULL, 'standard_conversion', NOW(), NOW(), NOW()
            )
            ON CONFLICT (us_size, gender, category_id)
            DO UPDATE SET
                eu_size = EXCLUDED.eu_size,
                uk_size = EXCLUDED.uk_size,
                cm_size = EXCLUDED.cm_size,
                kr_size = EXCLUDED.kr_size,
                validation_source = EXCLUDED.validation_source,
                last_validated_at = NOW(),
                updated_at = NOW()
        """).bindparams(
            us=us, eu=eu, uk=uk, cm=cm, kr=kr
        ))


def downgrade():
    """Remove standard size entries added by this migration"""
    op.execute("""
        DELETE FROM core.size_master
        WHERE validation_source = 'standard_conversion'
        AND category_id IS NULL
    """)
