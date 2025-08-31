"""Merge multiple migration heads

Revision ID: 930405202c44
Revises: ('052f62a0fc10', '2025_08_30_0900', '2025_08_30_1030')
Create Date: 2025-08-31 10:16:22.933975

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '930405202c44'
down_revision = ('052f62a0fc10', '2025_08_30_0900', '2025_08_30_1030')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
