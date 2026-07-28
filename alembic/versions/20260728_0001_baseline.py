"""Baseline the existing schema and add benchmark cohort data.

Revision ID: 20260728_0001
Revises:
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260728_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("audits"):
        op.create_table(
            "audits",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.String(length=39), nullable=False),
            sa.Column("profile_strength", sa.Integer(), nullable=False),
            sa.Column("project_depth", sa.Integer(), nullable=False),
            sa.Column("commit_consistency", sa.Integer(), nullable=False),
            sa.Column("tech_diversity", sa.Integer(), nullable=False),
            sa.Column("percentile_benchmark", sa.Integer(), nullable=False),
            sa.Column("account_age_months", sa.Integer(), nullable=True),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_audits_username", "audits", ["username"])

    inspector = sa.inspect(bind)
    if not inspector.has_table("opted_out_usernames"):
        op.create_table(
            "opted_out_usernames",
            sa.Column("username", sa.String(length=39), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("review_queue"):
        op.create_table(
            "review_queue",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id"), nullable=False),
            sa.Column("generated_content", sa.Text(), nullable=False),
            sa.Column(
                "review_status",
                sa.Enum("pending", "approved", "rejected", name="review_status"),
                nullable=False,
            ),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_review_queue_audit_id", "review_queue", ["audit_id"])

    audit_columns = {column["name"] for column in sa.inspect(bind).get_columns("audits")}
    if "account_age_months" not in audit_columns:
        op.add_column("audits", sa.Column("account_age_months", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    audit_columns = {column["name"] for column in sa.inspect(bind).get_columns("audits")}
    if "account_age_months" in audit_columns:
        op.drop_column("audits", "account_age_months")
