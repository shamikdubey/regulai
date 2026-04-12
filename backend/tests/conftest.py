"""
Test configuration and shared fixtures.
Compatible with pytest-asyncio 0.24+ (asyncio_mode=auto).

Key design: fixtures COMMIT data to the database so the ASGI test client
(which uses the app's own connection pool) can see the test data.
Cleanup happens via delete in teardown.
"""
import asyncio
import secrets
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, delete
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

import os
os.environ["TESTING"] = "true"  # Must be set before database.py engine is used

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import get_settings as _get_settings

# Force NullPool engine for tests — prevents "Future attached to different loop" error
# This patches the module-level engine AFTER import, guaranteeing NullPool is used
import app.db.database as _db_module
_settings = _get_settings()
_test_engine = create_async_engine(
    _settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={
        "server_settings": {
            "statement_timeout": "30000",
            "application_name": "regulai_test",
        }
    } if "asyncpg" in _settings.DATABASE_URL else {},
)
_db_module.engine = _test_engine
_db_module.AsyncSessionLocal = async_sessionmaker(
    _test_engine, class_=_db_module.AsyncSessionLocal.class_, expire_on_commit=False
)

from app.db.database import AsyncSessionLocal, init_db
from app.db.models import Tenant, User, ApiKey, RefreshToken
from app.services.auth_service import create_access_token


# ── Password hashing (using bcrypt directly, same as auth.py) ────────────────

import bcrypt as _bcrypt

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt(rounds=4)).decode("utf-8")


# ── Database setup (runs once per test session) ───────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    await init_db()
    # Disable RLS using owner credentials (regulai_app cannot ALTER TABLE or GRANT)
    owner_url = _settings.DATABASE_URL.replace("regulai_app:dev_app_secret", "regulai_owner:dev_owner_secret")
    owner_engine = create_async_engine(owner_url, poolclass=NullPool)
    async with owner_engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        tables = [
            "users", "tenants", "documents", "query_logs", "regulation_chunks",
            "alert_subscriptions", "refresh_tokens", "api_keys",
            "email_verification_tokens", "password_reset_tokens",
            "filing_projects", "filing_templates", "filing_checklist_items",
            "document_drafts", "document_draft_versions", "compliance_reviews",
        ]
        for table in tables:
            try:
                await conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
                await conn.execute(sa.text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
                await conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
                await conn.execute(sa.text(f"DROP POLICY IF EXISTS corpus_isolation ON {table}"))
            except Exception:
                pass
        try:
            await conn.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO regulai_app"))
            await conn.execute(sa.text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO regulai_app"))
        except Exception:
            pass
    await owner_engine.dispose()
    yield


# ── Admin DB session (bypasses RLS, commits data) ────────────────────────────

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session that COMMITS data so the ASGI test client can see it.
    Cleans up after the test by tracking created IDs.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))
        yield session
        # Commit so the app's connection pool can see the data
        await session.commit()


# ── Cleanup helper ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def cleanup_after_test():
    """Delete all test data after each test to keep DB clean."""
    yield
    # Clean up after test
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))
        # Delete in FK-safe order (children before parents)
        await session.execute(delete(RefreshToken))
        await session.execute(delete(ApiKey))
        # Delete optional tables that may not exist if init_db hasn't run yet
        optional_tables = [
            "alert_subscriptions", "regulation_chunks", "regulations",
            "documents", "password_reset_tokens",
            "email_verification_tokens", "query_logs",
        ]
        for tbl in optional_tables:
            # Use DO block to silently skip missing tables
            await session.execute(text(f"""
                DO $$ BEGIN
                    DELETE FROM {tbl};
                EXCEPTION WHEN undefined_table THEN NULL;
                END $$;
            """))
        await session.execute(delete(User))
        await session.execute(delete(Tenant))
        await session.commit()


# ── Tenant fixtures ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant(db: AsyncSession) -> Tenant:
    """Create and commit a test tenant."""
    t = Tenant(
        name=f"Test Co {uuid.uuid4().hex[:6]}",
        slug=f"test-{uuid.uuid4().hex[:8]}",
        license_key=secrets.token_urlsafe(32),
        allowed_jurisdictions=[],
        allowed_domains=[],
        query_limit_per_day=100,
    )
    db.add(t)
    await db.flush()
    await db.commit()
    return t


@pytest_asyncio.fixture
async def second_tenant(db: AsyncSession) -> Tenant:
    """A second tenant for cross-tenant isolation tests."""
    t = Tenant(
        name=f"Other Co {uuid.uuid4().hex[:6]}",
        slug=f"other-{uuid.uuid4().hex[:8]}",
        license_key=secrets.token_urlsafe(32),
        allowed_jurisdictions=[],
        allowed_domains=[],
    )
    db.add(t)
    await db.flush()
    await db.commit()
    return t


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db: AsyncSession, tenant: Tenant) -> User:
    """Create and commit an admin user."""
    email = f"admin-{uuid.uuid4().hex[:8]}@test.com"
    u = User(
        tenant_id=tenant.id,
        auth0_user_id=email,
        email=email,
        full_name="Test Admin",
        role="admin",
        password_hash=hash_password("Test1234!"),
        email_verified=True,
    )
    db.add(u)
    await db.flush()
    await db.commit()
    return u


@pytest_asyncio.fixture
async def regular_user(db: AsyncSession, tenant: Tenant) -> User:
    """Create and commit a regular user."""
    email = f"user-{uuid.uuid4().hex[:8]}@test.com"
    u = User(
        tenant_id=tenant.id,
        auth0_user_id=email,
        email=email,
        full_name="Test User",
        role="user",
        password_hash=hash_password("Test1234!"),
        email_verified=True,
    )
    db.add(u)
    await db.flush()
    await db.commit()
    return u


@pytest_asyncio.fixture
async def second_tenant_user(db: AsyncSession, second_tenant: Tenant) -> User:
    """User in the second tenant for isolation tests."""
    email = f"other-{uuid.uuid4().hex[:8]}@other.com"
    u = User(
        tenant_id=second_tenant.id,
        auth0_user_id=email,
        email=email,
        full_name="Other User",
        role="admin",
        password_hash=hash_password("Test1234!"),
        email_verified=True,
    )
    db.add(u)
    await db.flush()
    await db.commit()
    return u


# ── Token fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_token(admin_user: User, tenant: Tenant) -> str:
    return create_access_token(
        user_id=str(admin_user.id),
        tenant_id=str(tenant.id),
        email=admin_user.email,
        role=admin_user.role,
    )


@pytest.fixture
def user_token(regular_user: User, tenant: Tenant) -> str:
    return create_access_token(
        user_id=str(regular_user.id),
        tenant_id=str(tenant.id),
        email=regular_user.email,
        role=regular_user.role,
    )


@pytest.fixture
def second_tenant_token(second_tenant_user: User, second_tenant: Tenant) -> str:
    return create_access_token(
        user_id=str(second_tenant_user.id),
        tenant_id=str(second_tenant.id),
        email=second_tenant_user.email,
        role=second_tenant_user.role,
    )


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token: str) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def other_tenant_headers(second_tenant_token: str) -> dict:
    return {"Authorization": f"Bearer {second_tenant_token}"}


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client using the real ASGI app."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,
    ) as ac:
        yield ac


# ── API key fixture ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_key(db: AsyncSession, admin_user: User, tenant: Tenant):
    """Create and commit a test API key. Returns (raw_key, ApiKey model)."""
    raw, prefix, key_hash = ApiKey.generate_key("test")
    ak = ApiKey(
        tenant_id=tenant.id,
        created_by=admin_user.id,
        name="Test Key",
        prefix=prefix,
        key_hash=key_hash,
        scopes=["query:read", "docs:write", "*"],
    )
    db.add(ak)
    await db.flush()
    await db.commit()
    return raw, ak
