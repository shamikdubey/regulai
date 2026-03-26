"""Add ingredient_specs, allowable_limits, labeling_requirements, licensing_pathways

Revision ID: 0003_new_features
Revises: 0002_alerts
Create Date: 2026-01-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_new_features"
down_revision: Union[str, None] = "0002_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingredient_specs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("synonyms", postgresql.JSON(), nullable=True),
        sa.Column("cas_number", sa.String(50), nullable=True),
        sa.Column("einecs", sa.String(50), nullable=True),
        sa.Column("ins_number", sa.String(20), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("pharmacopoeias", postgresql.JSON(), nullable=True),
        sa.Column("codex_standard", sa.String(255), nullable=True),
        sa.Column("jecfa_id", sa.String(50), nullable=True),
        sa.Column("fssai_schedule", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("molecular_formula", sa.String(100), nullable=True),
        sa.Column("molecular_weight", sa.String(50), nullable=True),
        sa.Column("appearance", sa.Text(), nullable=True),
        sa.Column("solubility", sa.Text(), nullable=True),
        sa.Column("assay_limits", postgresql.JSON(), nullable=True),
        sa.Column("heavy_metal_limits", postgresql.JSON(), nullable=True),
        sa.Column("microbiological_limits", postgresql.JSON(), nullable=True),
        sa.Column("impurity_limits", postgresql.JSON(), nullable=True),
        sa.Column("storage", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ingredient_specs_name", "ingredient_specs", ["name"])
    op.create_index("ix_ingredient_specs_cas", "ingredient_specs", ["cas_number"])

    op.create_table(
        "allowable_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("substance", sa.String(255), nullable=False),
        sa.Column("substance_aliases", postgresql.JSON(), nullable=True),
        sa.Column("cas_number", sa.String(50), nullable=True),
        sa.Column("ins_number", sa.String(20), nullable=True),
        sa.Column("limit_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("food_matrix", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("limit_value", sa.String(100), nullable=False),
        sa.Column("limit_unit", sa.String(50), nullable=False),
        sa.Column("adi_tdi", sa.String(100), nullable=True),
        sa.Column("regulatory_basis", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), default="active"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_allowable_limits_substance", "allowable_limits", ["substance"])
    op.create_index("ix_allowable_limits_jurisdiction", "allowable_limits", ["jurisdiction"])

    op.create_table(
        "labeling_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("product_type", sa.String(100), nullable=False),
        sa.Column("regulatory_basis", sa.String(255), nullable=False),
        sa.Column("competent_authority", sa.String(100), nullable=False),
        sa.Column("mandatory_fields", postgresql.JSON(), nullable=False),
        sa.Column("nutrition_declaration", postgresql.JSON(), nullable=True),
        sa.Column("allergen_rules", postgresql.JSON(), nullable=True),
        sa.Column("weights_measures", postgresql.JSON(), nullable=True),
        sa.Column("language_requirements", postgresql.JSON(), nullable=True),
        sa.Column("prohibited_claims", postgresql.JSON(), nullable=True),
        sa.Column("claim_rules", postgresql.JSON(), nullable=True),
        sa.Column("special_requirements", postgresql.JSON(), nullable=True),
        sa.Column("enforcement_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_labeling_req_jurisdiction", "labeling_requirements", ["jurisdiction"])
    op.create_index("ix_labeling_req_product_type", "labeling_requirements", ["product_type"])

    op.create_table(
        "licensing_pathways",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("product_type", sa.String(100), nullable=False),
        sa.Column("product_subtype", sa.String(100), nullable=True),
        sa.Column("license_type", sa.String(200), nullable=False),
        sa.Column("competent_authority", sa.String(150), nullable=False),
        sa.Column("application_portal", sa.String(300), nullable=True),
        sa.Column("pathway_steps", postgresql.JSON(), nullable=False),
        sa.Column("prerequisites", postgresql.JSON(), nullable=True),
        sa.Column("documents_required", postgresql.JSON(), nullable=True),
        sa.Column("fees", postgresql.JSON(), nullable=True),
        sa.Column("typical_timeline_months", sa.String(50), nullable=True),
        sa.Column("fast_track_available", sa.Boolean(), default=False),
        sa.Column("fast_track_details", sa.Text(), nullable=True),
        sa.Column("gmp_requirements", postgresql.JSON(), nullable=True),
        sa.Column("renewal_period_years", sa.Integer(), nullable=True),
        sa.Column("renewal_requirements", postgresql.JSON(), nullable=True),
        sa.Column("post_approval_obligations", postgresql.JSON(), nullable=True),
        sa.Column("reference_regulation", sa.String(255), nullable=False),
        sa.Column("complexity", sa.String(10), default="MEDIUM"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_licensing_jurisdiction", "licensing_pathways", ["jurisdiction"])
    op.create_index("ix_licensing_product_type", "licensing_pathways", ["product_type"])


def downgrade() -> None:
    op.drop_table("licensing_pathways")
    op.drop_table("labeling_requirements")
    op.drop_table("allowable_limits")
    op.drop_table("ingredient_specs")
