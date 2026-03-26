"""
Test configuration and shared fixtures.
All tests use an isolated test database with RLS policies active.
"""
import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, engine, Base, init_db
from app.db.models import Tenant, User, RefreshToken, ApiKey
from app.api.v1.endpoints.auth import pwd_ctx
from app.services.auth_service import create_access_token, create_refresh_token


# ── Event loop (session-scoped) ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Database setup ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    await init_db()
    yield


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Test database session with RLS bypass for test fixture setup.
    Each test gets a clean transaction that is rolled back after.
    """
    async with AsyncSessionLocal() as session:
        # Bypass RLS for test fixtures
        await session.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))
        yield session
        await session.rollback()


# ── Shared test factories ─────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant(db: AsyncSession) -> Tenant:
    """Create an isolated test tenant."""
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
    return t


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession, tenant: Tenant) -> User:
    """Create an admin user in the test tenant."""
    email = f"admin-{uuid.uuid4().hex[:8]}@test.com"
    u = User(
        tenant_id=tenant.id,
        auth0_user_id=email,
        email=email,
        full_name="Test Admin",
        role="admin",
        password_hash=pwd_ctx.hash("Test1234!"),
        email_verified=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def regular_user(db: AsyncSession, tenant: Tenant) -> User:
    """Create a regular user in the test tenant."""
    email = f"user-{uuid.uuid4().hex[:8]}@test.com"
    u = User(
        tenant_id=tenant.id,
        auth0_user_id=email,
        email=email,
        full_name="Test User",
        role="user",
        password_hash=pwd_ctx.hash("Test1234!"),
        email_verified=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def second_tenant(db: AsyncSession) -> Tenant:
    """A second tenant — for cross-tenant isolation tests."""
    t = Tenant(
        name=f"Other Co {uuid.uuid4().hex[:6]}",
        slug=f"other-{uuid.uuid4().hex[:8]}",
        license_key=secrets.token_urlsafe(32),
        allowed_jurisdictions=[],
        allowed_domains=[],
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def second_tenant_user(db: AsyncSession, second_tenant: Tenant) -> User:
    """User in the second tenant."""
    email = f"other-{uuid.uuid4().hex[:8]}@other.com"
    u = User(
        tenant_id=second_tenant.id,
        auth0_user_id=email,
        email=email,
        full_name="Other User",
        role="admin",
        password_hash=pwd_ctx.hash("Test1234!"),
        email_verified=True,
    )
    db.add(u)
    await db.flush()
    return u


# ── Auth helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def admin_token(admin_user: User, tenant: Tenant) -> str:
    """JWT access token for the admin user."""
    return create_access_token(
        user_id=str(admin_user.id),
        tenant_id=str(tenant.id),
        email=admin_user.email,
        role=admin_user.role,
    )


@pytest.fixture
def user_token(regular_user: User, tenant: Tenant) -> str:
    """JWT access token for the regular user."""
    return create_access_token(
        user_id=str(regular_user.id),
        tenant_id=str(tenant.id),
        email=regular_user.email,
        role=regular_user.role,
    )


@pytest.fixture
def second_tenant_token(second_tenant_user: User, second_tenant: Tenant) -> str:
    """JWT for a user in a different tenant."""
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
    """Async HTTP client pointed at the ASGI app."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,
    ) as ac:
        yield ac


# ── API key fixture ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_key(db: AsyncSession, admin_user: User, tenant: Tenant) -> tuple[str, ApiKey]:
    """Create a test API key. Returns (raw_key, ApiKey model)."""
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
    return raw, ak
