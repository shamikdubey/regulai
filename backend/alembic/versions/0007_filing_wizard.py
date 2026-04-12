"""Add filing wizard tables

Revision ID: 0007_filing_wizard
Revises: 0006_phase1_auth
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0007_filing_wizard"
down_revision = "0006_phase1_auth"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS filing_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL,
            country TEXT NOT NULL,
            domain TEXT NOT NULL,
            device_class TEXT,
            food_category TEXT,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS filing_projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            product_name TEXT NOT NULL,
            country TEXT NOT NULL,
            domain TEXT NOT NULL,
            device_class TEXT,
            food_category TEXT,
            status TEXT NOT NULL DEFAULT 'planning',
            progress_pct INTEGER NOT NULL DEFAULT 0,
            deadline TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS filing_checklist_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES filing_projects(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            due_date TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_filing_projects_tenant_id ON filing_projects(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_filing_checklist_project_id ON filing_checklist_items(project_id)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON filing_templates TO regulai_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON filing_projects TO regulai_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON filing_checklist_items TO regulai_app")

def downgrade():
    op.execute("DROP TABLE IF EXISTS filing_checklist_items")
    op.execute("DROP TABLE IF EXISTS filing_projects")
    op.execute("DROP TABLE IF EXISTS filing_templates")
