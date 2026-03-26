from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import RegulatoryBody, Regulation, User
from app.schemas.schemas import RegulatoryBodyOut, RegulationOut
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/bodies", response_model=List[RegulatoryBodyOut])
async def list_regulatory_bodies(
    jurisdiction: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(RegulatoryBody).where(RegulatoryBody.is_active == True)  # noqa
    if jurisdiction:
        stmt = stmt.where(RegulatoryBody.jurisdiction == jurisdiction)
    if domain:
        stmt = stmt.where(RegulatoryBody.domains.contains([domain]))
    result = await db.execute(stmt.order_by(RegulatoryBody.jurisdiction, RegulatoryBody.acronym))
    return result.scalars().all()


@router.get("/regulations", response_model=List[RegulationOut])
async def list_regulations(
    jurisdiction: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Regulation)
    if jurisdiction:
        stmt = stmt.where(Regulation.jurisdiction == jurisdiction)
    if domain:
        stmt = stmt.where(Regulation.domain == domain)
    result = await db.execute(stmt.order_by(Regulation.jurisdiction, Regulation.domain).limit(limit))
    return result.scalars().all()
