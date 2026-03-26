import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Tenant, User
from app.schemas.schemas import TenantOut, TenantCreate
from app.services.auth_service import get_current_user, require_admin

router = APIRouter()


@router.get("/me", response_model=TenantOut)
async def get_my_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant


@router.post("/", response_model=TenantOut, dependencies=[Depends(require_admin)])
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Tenant).where(Tenant.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Slug '{data.slug}' already taken")

    tenant = Tenant(
        **data.model_dump(),
        license_key=secrets.token_urlsafe(32),
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/", response_model=List[TenantOut], dependencies=[Depends(require_admin)])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return result.scalars().all()
