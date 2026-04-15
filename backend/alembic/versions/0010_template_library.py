"""Add template library tables

Revision ID: 0010_template_library
Revises: 0009_compliance_review
Create Date: 2026-04-15
"""
from alembic import op

revision = "0010_template_library"
down_revision = "0009_compliance_review"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            country TEXT NOT NULL,
            domain TEXT NOT NULL,
            document_type TEXT NOT NULL,
            content_html TEXT,
            regulation_reference TEXT,
            trust_score INTEGER DEFAULT 40,
            trust_level TEXT DEFAULT 'UNVERIFIED',
            verified_by UUID,
            verified_at TIMESTAMPTZ,
            avg_user_rating NUMERIC(3,2) DEFAULT 0,
            feedback_count INTEGER DEFAULT 0,
            is_ai_generated BOOLEAN DEFAULT TRUE,
            generation_model TEXT DEFAULT 'claude-opus-4-6',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS template_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id UUID NOT NULL REFERENCES document_templates(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            tenant_id UUID NOT NULL,
            rating INTEGER NOT NULL,
            is_accurate BOOLEAN,
            feedback_text TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_templates_country_domain
        ON document_templates(country, domain)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_templates_trust_level
        ON document_templates(trust_level)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_template_feedback_template_id
        ON template_feedback(template_id)
    """)

    op.execute("""
        GRANT SELECT, INSERT, UPDATE, DELETE
        ON document_templates TO neondb_owner
    """)

    op.execute("""
        GRANT SELECT, INSERT, UPDATE, DELETE
        ON template_feedback TO neondb_owner
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS template_feedback")
    op.execute("DROP TABLE IF EXISTS document_templates")
