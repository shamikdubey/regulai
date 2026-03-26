"""Add regulatory_alerts and alert_subscriptions tables

Revision ID: 0002_alerts
Revises: 0001_initial
Create Date: 2026-01-02 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_alerts"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regulatory_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), default="medium"),
        sa.Column("effective_date", sa.String(50), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("regulatory_body", sa.String(100), nullable=True),
        sa.Column("action_required", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("published_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_jurisdiction", "regulatory_alerts", ["jurisdiction"])
    op.create_index("ix_alerts_domain", "regulatory_alerts", ["domain"])
    op.create_index("ix_alerts_severity", "regulatory_alerts", ["severity"])

    op.create_table(
        "alert_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("jurisdictions", postgresql.JSON(), nullable=False),
        sa.Column("domains", postgresql.JSON(), nullable=False),
        sa.Column("severity_threshold", sa.String(20), default="medium"),
        sa.Column("email_enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("alert_subscriptions")
    op.drop_table("regulatory_alerts")
