"""Add compliance review tables

Revision ID: 0009_compliance_review
Revises: 0008_document_editor
Create Date: 2026-04-12
"""
from alembic import op

revision = "0009_compliance_review"
down_revision = "0008_document_editor"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS compliance_reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            title TEXT NOT NULL,
            document_content TEXT NOT NULL,
            country TEXT,
            domain TEXT,
            regulation TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            score INTEGER,
            analysis JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_compliance_reviews_tenant_id ON compliance_reviews(tenant_id)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS compliance_reviews")
