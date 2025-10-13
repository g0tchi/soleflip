"""increase_style_code_length

Revision ID: 1eecf0cb7df3
Revises: e6afd519c0a5
Create Date: 2025-10-10 20:02:41.307230

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1eecf0cb7df3'
down_revision = 'e6afd519c0a5'
branch_labels = None
depends_on = None


def upgrade():
    # Increase style_code length from VARCHAR(50) to VARCHAR(200)
    # Some products have multiple style codes concatenated which exceed 50 characters
    op.alter_column(
        'products',
        'style_code',
        type_=sa.String(length=200),
        existing_type=sa.String(length=50),
        schema='products'
    )


def downgrade():
    # Revert back to VARCHAR(50)
    op.alter_column(
        'products',
        'style_code',
        type_=sa.String(length=50),
        existing_type=sa.String(length=200),
        schema='products'
    )
