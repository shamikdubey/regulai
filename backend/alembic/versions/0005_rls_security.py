"""Enable PostgreSQL Row-Level Security (RLS) on all tenant-scoped tables

This is the most critical production security migration.
Without RLS, a bug in application code could expose cross-tenant data.
RLS enforces tenant isolation at the Postgres level as a second defence layer.

Revision ID: 0005_rls_security
Revises: 0004_countries_expansion
Create Date: 2026-03-23 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_rls_security"
down_revision: Union[str, None] = "0004_countries_expansion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that contain tenant-scoped data
TENANT_SCOPED_TABLES = [
    "users",
    "documents",
    "query_logs",
    "alert_subscriptions",
]

# Tables with user_id only (get user-scoped RLS via join with users)
USER_SCOPED_TABLES: list[str] = []


def upgrade() -> None:
    conn = op.get_bind()

    # ── Create the app role that the API uses ─────────────────────────────────
    # The API connects as 'regulai_app' (limited role), not as superuser
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'regulai_app') THEN
                CREATE ROLE regulai_app LOGIN;
            END IF;
        END
        $$;
    """))

    conn.execute(sa.text("GRANT CONNECT ON DATABASE regulai TO regulai_app"))
    conn.execute(sa.text("GRANT USAGE ON SCHEMA public TO regulai_app"))
    conn.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO regulai_app"))
    conn.execute(sa.text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO regulai_app"))

    # ── Enable RLS on each tenant-scoped table ────────────────────────────────
    for table in TENANT_SCOPED_TABLES:
        # Enable RLS
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

        # Force RLS even for table owner (critical — superuser bypasses RLS by default)
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

        # DROP existing policies if re-running
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation_insert ON {table}"))

        # SELECT / UPDATE / DELETE policy: row must match current_setting tenant
        conn.execute(sa.text(f"""
            CREATE POLICY tenant_isolation ON {table}
            AS PERMISSIVE
            FOR ALL
            TO regulai_app
            USING (
                tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
                OR current_setting('app.bypass_rls', TRUE) = 'on'
            )
            WITH CHECK (
                tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            );
        """))

    # ── Special: regulation_chunks needs tenant_id column for RLS ─────────────
    # Currently regulation_chunks has no tenant_id — public shared corpus stays open
    # Private uploaded document chunks get tenant_id via document join
    # We handle this at the application layer — corpus chunks are public, doc chunks are private

    # ── RLS on audit log (query_logs) — read your own tenant only ─────────────
    # Already covered by tenant_isolation policy above

    # ── Create helper function for setting tenant context ─────────────────────
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id uuid)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_tenant_id', p_tenant_id::text, TRUE);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """))

    conn.execute(sa.text("GRANT EXECUTE ON FUNCTION set_tenant_context(uuid) TO regulai_app"))

    # ── Create function to bypass RLS for admin operations ────────────────────
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION set_bypass_rls(p_bypass boolean)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.bypass_rls', CASE WHEN p_bypass THEN 'on' ELSE 'off' END, TRUE);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """))

    # ── Index additions for RLS performance ───────────────────────────────────
    # RLS scans need fast tenant_id lookups
    for table in TENANT_SCOPED_TABLES:
        try:
            conn.execute(sa.text(
                f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table}(tenant_id);"
            ))
        except Exception:
            pass  # Index may already exist

    # ── Document chunks: add tenant_id for private corpus isolation ───────────
    # regulation_chunks from seed data have no tenant_id (public corpus)
    # Document chunks uploaded by tenants need isolation
    try:
        conn.execute(sa.text("""
            ALTER TABLE regulation_chunks
            ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE CASCADE;
        """))
        # NULL tenant_id = public corpus (shared, readable by all)
        # Non-null tenant_id = private corpus (RLS enforced)
        conn.execute(sa.text("ALTER TABLE regulation_chunks ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text("ALTER TABLE regulation_chunks FORCE ROW LEVEL SECURITY"))
        conn.execute(sa.text("DROP POLICY IF EXISTS corpus_isolation ON regulation_chunks"))
        conn.execute(sa.text("""
            CREATE POLICY corpus_isolation ON regulation_chunks
            AS PERMISSIVE
            FOR ALL
            TO regulai_app
            USING (
                tenant_id IS NULL
                OR tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
                OR current_setting('app.bypass_rls', TRUE) = 'on'
            )
            WITH CHECK (
                tenant_id IS NULL
                OR tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            )
        """))
    except Exception as e:
        print(f"Note: {e}")


def downgrade() -> None:
    conn = op.get_bind()

    for table in TENANT_SCOPED_TABLES + ["regulation_chunks"]:
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS corpus_isolation ON {table}"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    conn.execute(sa.text("DROP FUNCTION IF EXISTS set_tenant_context(uuid);"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS set_bypass_rls(boolean);"))

    try:
        conn.execute(sa.text(
            "ALTER TABLE regulation_chunks DROP COLUMN IF EXISTS tenant_id;"
        ))
    except Exception:
        pass
