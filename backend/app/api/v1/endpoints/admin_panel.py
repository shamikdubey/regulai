"""
Admin Panel — ported from Reguard into RegulAI
  GET    /admin/users
  GET    /admin/users/{id}
  PUT    /admin/users/{id}/role
  PUT    /admin/users/{id}/deactivate
  GET    /admin/tenants
  GET    /admin/tenants/{id}
  GET    /admin/stats
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()

VALID_ROLES = {"admin", "user", "viewer"}

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

class RoleUpdate(BaseModel):
    role: str

    def validate_role(self):
        if self.role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")

async def log_admin_action(db: AsyncSession, admin_id: str, action: str, target: str):
    try:
        await db.execute(text("""
            INSERT INTO query_logs (id, tenant_id, user_id, query_text, response_text, tokens_used)
            VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000000'::uuid, :user_id, :action, :target, 0)
        """), {"user_id": admin_id, "action": f"ADMIN:{action}", "target": target})
    except Exception:
        pass

@router.get("/admin/users")
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    tenant_id: Optional[str] = None,
):
    query = "SELECT id, tenant_id, email, full_name, role, is_active, created_at FROM users"
    params = {}
    if tenant_id:
        query += " WHERE tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    query += " ORDER BY created_at DESC"
    result = await db.execute(text(query), params)
    return [dict(r) for r in result.mappings().all()]

@router.get("/admin/users/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT id, tenant_id, email, full_name, role, is_active, created_at
        FROM users WHERE id = :id
    """), {"id": str(user_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)

@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    body: RoleUpdate = ...,
):
    body.validate_role()
    result = await db.execute(text(
        "SELECT id FROM users WHERE id = :id"
    ), {"id": str(user_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute(text(
        "UPDATE users SET role = :role WHERE id = :id"
    ), {"role": body.role, "id": str(user_id)})
    await log_admin_action(db, str(admin.id), "UPDATE_ROLE", f"user:{user_id}:role:{body.role}")
    await db.commit()
    return {"status": "updated", "user_id": str(user_id), "role": body.role}

@router.put("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if str(user_id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    result = await db.execute(text(
        "SELECT id FROM users WHERE id = :id"
    ), {"id": str(user_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute(text(
        "UPDATE users SET is_active = FALSE WHERE id = :id"
    ), {"id": str(user_id)})
    await log_admin_action(db, str(admin.id), "DEACTIVATE_USER", f"user:{user_id}")
    await db.commit()
    return {"status": "deactivated", "user_id": str(user_id)}

@router.get("/admin/tenants")
async def list_tenants(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT t.id, t.name, t.created_at,
               COUNT(u.id) as user_count
        FROM tenants t
        LEFT JOIN users u ON u.tenant_id = t.id
        GROUP BY t.id, t.name, t.created_at
        ORDER BY t.created_at DESC
    """))
    return [dict(r) for r in result.mappings().all()]

@router.get("/admin/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT t.id, t.name, t.created_at,
               COUNT(u.id) as user_count
        FROM tenants t
        LEFT JOIN users u ON u.tenant_id = t.id
        WHERE t.id = :id
        GROUP BY t.id, t.name, t.created_at
    """), {"id": str(tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return dict(row)

@router.get("/admin/stats")
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    users = await db.execute(text("SELECT COUNT(*) as total FROM users"))
    tenants = await db.execute(text("SELECT COUNT(*) as total FROM tenants"))
    queries = await db.execute(text("SELECT COUNT(*) as total FROM query_logs"))
    reviews = await db.execute(text("SELECT COUNT(*) as total FROM compliance_reviews"))
    projects = await db.execute(text("SELECT COUNT(*) as total FROM filing_projects"))
    drafts = await db.execute(text("SELECT COUNT(*) as total FROM document_drafts"))
    return {
        "total_users": users.scalar(),
        "total_tenants": tenants.scalar(),
        "total_queries": queries.scalar(),
        "total_compliance_reviews": reviews.scalar(),
        "total_filing_projects": projects.scalar(),
        "total_document_drafts": drafts.scalar(),
    }
