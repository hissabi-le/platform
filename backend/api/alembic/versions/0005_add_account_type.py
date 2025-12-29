"""Add account_type column to transactions table

Revision ID: 0005_add_account_type
Revises: 0004_add_journal_and_settings
Create Date: 2025-12-16

This migration adds a deterministic account_type column to the transactions table,
replacing the fragile string-matching approach used in analytics.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_add_account_type'
down_revision = '0004_add_journal_and_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account_type column with a default value for existing rows
    # Using String instead of PostgreSQL ENUM for SQLite compatibility in development
    op.add_column(
        'transactions',
        sa.Column(
            'account_type',
            sa.String(20),
            nullable=True,
            comment='Account classification: ASSET, LIABILITY, EQUITY, REVENUE, COGS, EXPENSE'
        )
    )
    
    # Backfill existing rows using heuristic classification
    # This query uses the same logic that was in _classify_pnl_bucket
    op.execute("""
        UPDATE transactions SET account_type = 
            CASE 
                WHEN LOWER(category) LIKE '%revenue%' 
                     OR LOWER(category) LIKE '%sales%' 
                     OR LOWER(category) LIKE '%income%'
                     OR LOWER(account_code) LIKE '%revenue%'
                     OR LOWER(account_code) LIKE '%sales%'
                THEN 'REVENUE'
                WHEN LOWER(category) LIKE '%cogs%' 
                     OR LOWER(category) LIKE '%cost of goods%'
                     OR LOWER(account_code) LIKE '%cogs%'
                THEN 'COGS'
                WHEN LOWER(category) LIKE '%cash%'
                     OR LOWER(category) LIKE '%bank%'
                     OR LOWER(category) LIKE '%receivable%'
                     OR LOWER(category) LIKE '%inventory%'
                     OR LOWER(category) LIKE '%asset%'
                     OR LOWER(category) LIKE '%prepaid%'
                THEN 'ASSET'
                WHEN LOWER(category) LIKE '%payable%'
                     OR LOWER(category) LIKE '%loan%'
                     OR LOWER(category) LIKE '%debt%'
                     OR LOWER(category) LIKE '%accrued%'
                THEN 'LIABILITY'
                WHEN LOWER(category) LIKE '%equity%'
                     OR LOWER(category) LIKE '%capital%'
                     OR LOWER(category) LIKE '%retained%'
                THEN 'EQUITY'
                WHEN amount > 0 THEN 'REVENUE'
                ELSE 'EXPENSE'
            END
        WHERE account_type IS NULL
    """)
    
    # Make the column non-nullable after backfill
    op.alter_column(
        'transactions',
        'account_type',
        nullable=False,
        server_default='EXPENSE'
    )
    
    # Add index for faster queries by account_type
    op.create_index(
        'ix_transactions_account_type',
        'transactions',
        ['account_type']
    )
    
    # Composite index for analytics queries
    op.create_index(
        'ix_transactions_org_type_date',
        'transactions',
        ['org_id', 'account_type', 'txn_date']
    )


def downgrade() -> None:
    op.drop_index('ix_transactions_org_type_date', table_name='transactions')
    op.drop_index('ix_transactions_account_type', table_name='transactions')
    op.drop_column('transactions', 'account_type')
