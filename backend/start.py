"""
Startup script — runs once when app starts on Render.
Creates all tables and default admin user if they don't exist.
"""
import asyncio
import bcrypt
import os


async def initialize():
    from app.db.database import init_db, AsyncSessionLocal
    from app.db.models import Tenant, User
    from sqlalchemy import select

    print("==> Running startup initialization...")

    # Create all tables
    await init_db()
    print("==> Tables ready")

    # Check if admin user already exists
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == "admin@regulai.com")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("==> Admin user already exists, skipping creation")
            return

        # Create default tenant
        tenant = Tenant(
            name="RegulAI",
            slug="regulai-demo",
            license_key="demo-001",
            allowed_jurisdictions=[],
            allowed_domains=[],
            query_limit_per_day=500,
        )
        db.add(tenant)
        await db.flush()

        # Create admin user
        pw = bcrypt.hashpw(b"Admin@123456", bcrypt.gensalt()).decode()
        user = User(
            tenant_id=tenant.id,
            auth0_user_id="admin@regulai.com",
            email="admin@regulai.com",
            full_name="Admin",
            role="admin",
            password_hash=pw,
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        print("==> Admin user created: admin@regulai.com / Admin@123456")


if __name__ == "__main__":
    asyncio.run(initialize())
