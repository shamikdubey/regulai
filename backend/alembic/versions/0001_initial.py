"""Initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("auth0_org_id", sa.String(100), unique=True, nullable=True),
        sa.Column("license_key", sa.String(255), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("allowed_jurisdictions", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("allowed_domains", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("settings", postgresql.JSON(), nullable=True),
        sa.Column("query_limit_per_day", sa.Integer(), default=500),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("auth0_user_id", sa.String(255), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), default="user"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_auth0_user_id", "users", ["auth0_user_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "regulatory_bodies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("acronym", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("domains", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("established_year", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_regulatory_bodies_acronym", "regulatory_bodies", ["acronym"])
    op.create_index("ix_regulatory_bodies_jurisdiction", "regulatory_bodies", ["jurisdiction"])

    op.create_table(
        "regulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("short_name", sa.String(100), nullable=True),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("year", sa.String(20), nullable=True),
        sa.Column("status", sa.String(50), default="active"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("regulatory_body_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("regulatory_bodies.id"), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_regulations_name", "regulations", ["name"])
    op.create_index("ix_regulations_jurisdiction", "regulations", ["jurisdiction"])
    op.create_index("ix_regulations_domain", "regulations", ["domain"])

    op.create_table(
        "regulation_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("regulation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.execute("""
        CREATE INDEX ix_chunks_embedding ON regulation_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("domain", sa.String(50), nullable=True),
        sa.Column("processing_status", sa.String(50), default="pending"),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("domain", sa.String(50), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("retrieved_chunk_ids", postgresql.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("hmac_signature", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_query_logs_tenant_created", "query_logs", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_table("documents")
    op.drop_table("regulation_chunks")
    op.drop_table("regulations")
    op.drop_table("regulatory_bodies")
    op.drop_table("users")
    op.drop_table("tenants")
