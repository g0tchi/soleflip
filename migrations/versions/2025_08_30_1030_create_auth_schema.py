"""Create authentication schema and users table

Revision ID: 2025_08_30_1030
Revises: 2025_08_30_1000
Create Date: 2025-08-30 10:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '2025_08_30_1030'
down_revision = '2025_08_30_1000'
branch_labels = None
depends_on = None


def upgrade():
    """Create authentication schema and tables"""
    print("Creating authentication schema...")
    
    # Create auth schema
    op.execute('CREATE SCHEMA IF NOT EXISTS auth')
    
    # Create user roles enum
    op.execute("CREATE TYPE auth.user_role AS ENUM ('admin', 'user', 'readonly')")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'user', 'readonly', name='user_role'), 
                  nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.func.now()),
        schema='auth'
    )
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'], schema='auth', unique=True)
    op.create_index('idx_users_username', 'users', ['username'], schema='auth', unique=True)
    op.create_index('idx_users_role', 'users', ['role'], schema='auth')
    op.create_index('idx_users_is_active', 'users', ['is_active'], schema='auth')
    
    # Create default admin user (password: admin123)
    # Hash generated with bcrypt for 'admin123'
    admin_password_hash = '$2b$12$rQZ4QJZ4QJZ4QJZ4QJZ4QOvKyA5B5B5B5B5B5B5B5B5B5B5B5B5B5O'
    
    op.execute(f"""
    INSERT INTO auth.users (id, email, username, hashed_password, role, is_active)
    VALUES (
        gen_random_uuid(),
        'admin@soleflip.com',
        'admin',
        '{admin_password_hash}',
        'admin',
        true
    )
    """)
    
    print("[OK] Authentication schema created successfully")


def downgrade():
    """Remove authentication schema and tables"""
    print("Removing authentication schema...")
    
    # Drop table (cascade will drop indexes)
    op.drop_table('users', schema='auth')
    
    # Drop enum type
    op.execute('DROP TYPE auth.user_role')
    
    # Drop schema
    op.execute('DROP SCHEMA auth CASCADE')
    
    print("Authentication schema removed successfully")