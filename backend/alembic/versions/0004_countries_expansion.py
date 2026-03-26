"""Add countries reference table and tier column to all regulatory tables

Revision ID: 0004_countries_expansion
Revises: 0003_new_features
Create Date: 2026-01-04 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_countries_expansion"
down_revision: Union[str, None] = "0003_new_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Countries reference table (drives the 110-country selector)
    op.create_table(
        "countries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("value", sa.String(50), nullable=False, unique=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("flag", sa.String(10), nullable=True),
        sa.Column("tier", sa.Integer(), default=2, nullable=False),
        sa.Column("region_id", sa.String(50), nullable=True),
        sa.Column("region_label", sa.String(100), nullable=True),
        sa.Column("region_color", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_countries_value", "countries", ["value"])
    op.create_index("ix_countries_region", "countries", ["region_id"])

    # Add tier column to existing tables
    for table in ["regulatory_bodies", "regulations", "regulatory_alerts",
                  "ingredient_specs", "allowable_limits", "labeling_requirements",
                  "licensing_pathways"]:
        op.add_column(table, sa.Column("tier", sa.Integer(), nullable=True, server_default="2"))
        op.add_column(table, sa.Column("region_id", sa.String(50), nullable=True))

    # Add covering indexes for jurisdiction queries (performance with 110 countries)
    op.create_index("ix_reg_bodies_jurisdiction", "regulatory_bodies", ["jurisdiction"])
    op.create_index("ix_allowable_limits_limit_type", "allowable_limits", ["limit_type"])
    op.create_index("ix_licensing_complexity", "licensing_pathways", ["complexity"])
    op.create_index("ix_labeling_jurisdiction_product", "labeling_requirements",
                    ["jurisdiction", "product_type"])


def downgrade() -> None:
    op.drop_table("countries")
    for table in ["regulatory_bodies", "regulations", "regulatory_alerts",
                  "ingredient_specs", "allowable_limits", "labeling_requirements",
                  "licensing_pathways"]:
        op.drop_column(table, "tier")
        op.drop_column(table, "region_id")
