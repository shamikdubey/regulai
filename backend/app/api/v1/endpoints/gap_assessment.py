"""
Gap Assessment — Phase 2
  POST /gap-assessment         — enqueue Celery job (async)
  POST /gap-assessment/sync    — synchronous fallback (no Celery required)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


class GapAssessmentRequest(BaseModel):
    product_name: str
    product_description: str
    product_type: str
    target_jurisdictions: List[str]
    current_approvals: Optional[List[str]] = []
    intended_claims: Optional[str] = ""


class GapItem(BaseModel):
    jurisdiction: str; gap: str; requirement: str
    risk_level: str; estimated_timeline: str; action_required: str


class GapAssessmentResponse(BaseModel):
    product_name: str; overall_risk: str; gaps: List[GapItem]
    summary: str; critical_path: List[str]; estimated_total_months: int


@router.post("/gap-assessment")
async def gap_assessment(
    body: GapAssessmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueue a gap assessment job.
    If Celery is enabled: returns job_id immediately, poll /jobs/{id}.
    If Celery is disabled: runs synchronously (may be slow).
    """
    kwargs = dict(
        product_name=body.product_name,
        product_description=body.product_description,
        product_type=body.product_type,
        target_jurisdictions=body.target_jurisdictions,
        current_approvals=body.current_approvals or [],
        intended_claims=body.intended_claims or "",
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
    )

    if settings.ENABLE_CELERY:
        from app.tasks.ai_tasks import run_gap_assessment
        job = run_gap_assessment.apply_async(kwargs=kwargs)
        return {
            "job_id": job.id,
            "status": "queued",
            "poll_url": f"/api/v1/jobs/{job.id}",
            "message": "Gap assessment started. Poll poll_url for progress.",
        }
    else:
        # Synchronous fallback
        from app.tasks.ai_tasks import _run_gap_assessment_async
        import asyncio

        class _FakeTask:
            def update_state(self, **kwargs): pass

        result = await _run_gap_assessment_async(_FakeTask(), **kwargs)
        return result
