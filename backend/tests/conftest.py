"""
Test configuration and shared fixtures.
Compatible with pytest-asyncio 0.24+ (asyncio_mode=auto).
"""
import asyncio
import hashlib
import secrets
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, init_db
from app.db.models import Tenant, User, ApiKey
from app.api.v1.endpoints.auth import pwd_ctx
from app.services.auth_service import create_access_token


# ── Database setup (runs once per test session) ───────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    await init_db()
    yield


# ── Database session per test ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Test database session with RLS bypassed for fixture setup."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))
        yield session
        await session.rollback()


# ── Tenant fixtures ───────────────────────────────────────────────────────────

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
    return t


# ── User fixtures ─────────────────────────────────────────────────────────────

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
    """Create a regular (non-admin) user."""
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
async def second_tenant_user(db: AsyncSession, second_tenant: Tenant) -> User:
    """User in the second tenant for isolation tests."""
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
    """Async HTTP test client."""
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
