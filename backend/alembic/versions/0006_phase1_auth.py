"""Phase 1 Auth tables — refresh tokens, API keys, sessions, password reset

Revision ID: 0006_phase1_auth
Revises: 0005_rls_security
Create Date: 2026-03-23 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase1_auth"
down_revision: Union[str, None] = "0005_rls_security"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Refresh tokens ────────────────────────────────────────────────────────
    # Stored as hashed values — plain token is returned once and never stored
    op.create_table(
        "refresh_tokens",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash",   sa.String(128), nullable=False, unique=True),
        sa.Column("family",       sa.String(64), nullable=False),   # rotation family
        sa.Column("is_revoked",   sa.Boolean, default=False, nullable=False),
        sa.Column("device_hint",  sa.String(255), nullable=True),   # "Chrome / macOS"
        sa.Column("ip_address",   sa.String(64), nullable=True),
        sa.Column("expires_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user",   "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family", "refresh_tokens", ["family"])
    op.create_index("ix_refresh_tokens_hash",   "refresh_tokens", ["token_hash"])

    # RLS on refresh tokens
    op.execute("""
        ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
        ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON refresh_tokens
        AS PERMISSIVE FOR ALL TO regulai_app
        USING (
            tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            OR current_setting('app.bypass_rls', TRUE) = 'on'
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
        );
    """)

    # ── API keys ──────────────────────────────────────────────────────────────
    # For programmatic access (integrations, scripts, CI/CD)
    op.create_table(
        "api_keys",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name",        sa.String(255), nullable=False),     # human label
        sa.Column("prefix",      sa.String(20),  nullable=False),     # "rkai_live_xxxxxxxx"
        sa.Column("key_hash",    sa.String(128), nullable=False, unique=True),
        sa.Column("scopes",      postgresql.ARRAY(sa.String), nullable=False,
                  server_default="{}"),     # ["query:read","docs:write",...]
        sa.Column("is_active",   sa.Boolean, default=True, nullable=False),
        sa.Column("last_used_at",sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("revoked_at",  sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_tenant",  "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_prefix",  "api_keys", ["prefix"])
    op.create_index("ix_api_keys_hash",    "api_keys", ["key_hash"])

    op.execute("""
        ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
        ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON api_keys
        AS PERMISSIVE FOR ALL TO regulai_app
        USING (
            tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            OR current_setting('app.bypass_rls', TRUE) = 'on'
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
        );
    """)

    # ── Password reset tokens ─────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("is_used",    sa.Boolean, default=False, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(64), nullable=True),
    )
    op.create_index("ix_prt_user",  "password_reset_tokens", ["user_id"])
    op.create_index("ix_prt_hash",  "password_reset_tokens", ["token_hash"])

    # ── Email verification tokens ─────────────────────────────────────────────
    op.create_table(
        "email_verification_tokens",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("is_used",    sa.Boolean, default=False, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── Add columns to users table ────────────────────────────────────────────
    op.add_column("users", sa.Column("password_hash",     sa.String(255), nullable=True))
    op.add_column("users", sa.Column("email_verified",    sa.Boolean, default=False,
                                     server_default="false", nullable=False))
    op.add_column("users", sa.Column("mfa_enabled",       sa.Boolean, default=False,
                                     server_default="false", nullable=False))
    op.add_column("users", sa.Column("mfa_secret",        sa.String(64), nullable=True))
    op.add_column("users", sa.Column("failed_login_count",sa.Integer, default=0,
                                     server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until",      sa.DateTime(timezone=True),
                                     nullable=True))

    # ── Add columns to query_logs — track API key usage ───────────────────────
    op.add_column("query_logs", sa.Column("api_key_id", postgresql.UUID(as_uuid=True),
                                          nullable=True))

    # ── Cleanup job helper: index expired tokens ───────────────────────────────
    op.execute("""
        CREATE INDEX ix_refresh_tokens_expires
        ON refresh_tokens(expires_at)
        WHERE is_revoked = false;

        CREATE INDEX ix_prt_expires
        ON password_reset_tokens(expires_at)
        WHERE is_used = false;
    """)


def downgrade() -> None:
    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("api_keys")
    op.drop_table("refresh_tokens")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "locked_until")
    op.drop_column("query_logs", "api_key_id")
