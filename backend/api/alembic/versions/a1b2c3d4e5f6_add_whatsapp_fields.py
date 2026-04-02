"""add whatsapp fields to users

Revision ID: a1b2c3d4e5f6
Revises: 'f3c80a86135d'
Create Date: 2026-04-02 07:26:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f3c80a86135d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('whatsapp_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('whatsapp_opt_in', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_unique_constraint('uq_users_phone', 'users', ['phone_number'])


def downgrade():
    op.drop_constraint('uq_users_phone', 'users', type_='unique')
    op.drop_column('users', 'whatsapp_opt_in')
    op.drop_column('users', 'whatsapp_verified')
    op.drop_column('users', 'phone_number')
