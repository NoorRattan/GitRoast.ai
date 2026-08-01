"""Persist observable signal snapshots and versioned population baselines.

Revision ID: 20260801_0002
Revises: 20260728_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20260801_0002"
down_revision = "20260728_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    audit_columns = {column["name"] for column in inspector.get_columns("audits")}
    if "metric_snapshot" not in audit_columns:
        op.add_column("audits", sa.Column("metric_snapshot", sa.JSON(), nullable=True))
    if not inspector.has_table("signal_baseline_configurations"):
        op.create_table(
            "signal_baseline_configurations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("version", sa.String(length=80), nullable=False, unique=True),
            sa.Column("source_schema_version", sa.Integer(), nullable=False),
            sa.Column("sample_size", sa.Integer(), nullable=False),
            sa.Column("baselines", sa.JSON(), nullable=False),
            sa.Column("distribution_summary", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("activated_by", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("signal_baseline_configurations"):
        op.drop_table("signal_baseline_configurations")
    audit_columns = {column["name"] for column in sa.inspect(bind).get_columns("audits")}
    if "metric_snapshot" in audit_columns:
        op.drop_column("audits", "metric_snapshot")
