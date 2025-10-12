"""align models after sprint: inventory + precision + indexes + column rename

Revision ID: 0003_align_models_after_sprint
Revises: cd808be30a8b
Create Date: 2025-09-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_align_models_after_sprint"
down_revision = "cd808be30a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # transactions: rename metadata -> metadata_json (if exists)
    # ---------------------------------------------------------
    with op.batch_alter_table("transactions") as batch:
        insp = sa.inspect(batch.get_bind())
        cols = [c["name"] for c in insp.get_columns("transactions")]
        if "metadata" in cols and "metadata_json" not in cols:
            batch.alter_column("metadata", new_column_name="metadata_json")
        # precision upgrade (Float -> Numeric(18,4))
        try:
            batch.alter_column("amount", type_=sa.Numeric(18, 4))
        except Exception:
            # some DBs may already be numeric; ignore
            pass

    # ---------------------------------------------------------
    # Helpful indexes (idempotent try/except to avoid clashes)
    # ---------------------------------------------------------
    try:
        op.create_index("ix_tx_org_ts", "transactions", ["org_id", "txn_date"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("ix_doc_org_time", "documents", ["org_id", "created_at"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("ix_upload_org_time", "uploads", ["org_id", "uploaded_at"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("ix_upload_org_status", "uploads", ["org_id", "status"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("ix_users_org_email", "users", ["org_id", "email"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("ix_sub_org_status", "subscriptions", ["org_id", "status"], unique=False)
    except Exception:
        pass

    # ---------------------------------------------------------
    # Inventory tables
    # ---------------------------------------------------------
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="unit"),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("org_id", "name", "unit", name="uq_item_name_unit_org"),
    )
    op.create_index("ix_item_org_name", "inventory_items", ["org_id", "name"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("qty_delta", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("ref_document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("memo", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_imv_org_time", "inventory_movements", ["org_id", "ts"], unique=False)


def downgrade() -> None:
    # Drop inventory tables + indexes
    op.drop_index("ix_imv_org_time", table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index("ix_item_org_name", table_name="inventory_items")
    op.drop_table("inventory_items")

    # Drop helper indexes (ignore if missing)
    for name, table in [
        ("ix_sub_org_status", "subscriptions"),
        ("ix_users_org_email", "users"),
        ("ix_upload_org_status", "uploads"),
        ("ix_upload_org_time", "uploads"),
        ("ix_doc_org_time", "documents"),
        ("ix_tx_org_ts", "transactions"),
    ]:
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass

    # Revert transactions column rename if desired
    with op.batch_alter_table("transactions") as batch:
        insp = sa.inspect(batch.get_bind())
        cols = [c["name"] for c in insp.get_columns("transactions")]
        if "metadata_json" in cols and "metadata" not in cols:
            batch.alter_column("metadata_json", new_column_name="metadata")
        # Optionally revert amount precision (not strictly necessary)
        # batch.alter_column("amount", type_=sa.Float())
