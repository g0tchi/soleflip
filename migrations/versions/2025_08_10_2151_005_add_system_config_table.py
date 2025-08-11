"""Add system_config table

Revision ID: 005_config_table
Revises: 2025_08_06_1200_004_add_german_suppliers
Create Date: 2025-08-10 21:51:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_config_table'
down_revision = '2025_08_06_1200_004_add_german_suppliers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    schema_name = 'core' if is_postgres else None

    op.create_table('system_config',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value_encrypted', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key'),
        schema=schema_name
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    schema_name = 'core' if is_postgres else None
    op.drop_table('system_config', schema=schema_name)
