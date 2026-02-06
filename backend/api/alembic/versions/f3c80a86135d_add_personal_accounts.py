"""add personal accounts

Revision ID: f3c80a86135d
Revises: 'eeb155d82577'
Create Date: 2026-02-06 03:57:11.171018
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3c80a86135d'
down_revision = 'eeb155d82577'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'personal_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('balance', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='checking'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('personal_accounts')
