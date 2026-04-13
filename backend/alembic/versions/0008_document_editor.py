"""Add document editor tables

Revision ID: 0008_document_editor
Revises: 0007_filing_wizard
Create Date: 2026-04-12
"""
from alembic import op

revision = "0008_document_editor"
down_revision = "0007_filing_wizard"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_drafts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            document_type TEXT NOT NULL DEFAULT 'general',
            country TEXT,
            domain TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_draft_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            draft_id UUID NOT NULL REFERENCES document_drafts(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL,
            content TEXT NOT NULL,
            comment TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_drafts_tenant_id ON document_drafts(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_draft_versions_draft_id ON document_draft_versions(draft_id)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS document_draft_versions")
    op.execute("DROP TABLE IF EXISTS document_drafts")
