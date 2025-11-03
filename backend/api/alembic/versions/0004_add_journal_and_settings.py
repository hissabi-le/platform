"""introduce organisation settings and journal tables"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_journal_and_settings"
down_revision = "0003_align_models_after_sprint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organisation_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_initial_investment", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("starting_cash_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("current_assets_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("default_currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("default_locale", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("org_id", name="uq_org_settings_org"),
        sa.CheckConstraint("total_initial_investment >= 0", name="ck_settings_initial_investment_nonnegative"),
        sa.CheckConstraint("starting_cash_balance >= 0", name="ck_settings_starting_cash_nonnegative"),
        sa.CheckConstraint("current_assets_value >= 0", name="ck_settings_assets_nonnegative"),
    )

    parse_status_check = (
        "parse_status IN ('pending','parsed','needs_review','error')"
    )
    entry_type_check = (
        "entry_type IN ('revenue','cost','inventory_purchase','inventory_use','transfer')"
    )

    op.create_table(
        "journal_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("journal_date", sa.Date(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("parse_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("total_revenue", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("net_profit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("clarification_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hash_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("org_id", "journal_date", name="uq_journal_org_date"),
        sa.UniqueConstraint("hash_key", name="uq_journal_hash"),
        sa.CheckConstraint(parse_status_check, name="ck_journal_status_valid"),
    )
    op.create_index("ix_journal_org_date", "journal_days", ["org_id", "journal_date"], unique=False)

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("journal_day_id", sa.Integer(), sa.ForeignKey("journal_days.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("total", sa.Numeric(18, 4), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("vat_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("vat_included", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ambiguous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(entry_type_check, name="ck_journal_entry_type_valid"),
    )
    op.create_index("ix_journal_entry_org_day", "journal_entries", ["org_id", "journal_day_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_journal_entry_org_day", table_name="journal_entries")
    op.drop_table("journal_entries")

    op.drop_index("ix_journal_org_date", table_name="journal_days")
    op.drop_table("journal_days")

    op.drop_table("organisation_settings")
