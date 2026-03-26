from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import QueryLog, User
from app.schemas.schemas import AuditLogEntry
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AuditLogEntry])
async def get_audit_log(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    jurisdiction: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return audit log entries for the current tenant (most recent first)."""
    stmt = (
        select(QueryLog)
        .where(QueryLog.tenant_id == user.tenant_id)
        .order_by(QueryLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if jurisdiction:
        stmt = stmt.where(QueryLog.jurisdiction == jurisdiction)
    if domain:
        stmt = stmt.where(QueryLog.domain == domain)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        AuditLogEntry(
            id=log.id,
            query=log.query,
            jurisdiction=log.jurisdiction,
            domain=log.domain,
            confidence=log.confidence,
            latency_ms=log.latency_ms,
            sources_used=len(log.retrieved_chunk_ids) if log.retrieved_chunk_ids else 0,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/{log_id}")
async def get_audit_entry(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QueryLog).where(QueryLog.id == log_id, QueryLog.tenant_id == user.tenant_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(404, "Audit entry not found")
    return {
        "id": str(log.id),
        "query": log.query,
        "response": log.response,
        "citations": log.citations,
        "confidence": log.confidence,
        "jurisdiction": log.jurisdiction,
        "domain": log.domain,
        "latency_ms": log.latency_ms,
        "hmac_signature": log.hmac_signature,
        "created_at": log.created_at.isoformat(),
    }
