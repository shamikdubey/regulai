"""
Dossier Drafting — Phase 2
  POST /dossier       — enqueue Celery job (async)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


class DossierRequest(BaseModel):
    product_name: str; product_type: str; jurisdiction: str
    submission_type: str; product_description: str
    active_ingredients: Optional[str] = ""
    indication_or_use: Optional[str] = ""
    manufacturing_site: Optional[str] = ""
    sections_requested: Optional[List[str]] = []


class DossierSection(BaseModel):
    section_id: str; title: str; content: str
    completeness: str; missing_data: List[str]


class DossierResponse(BaseModel):
    product_name: str; jurisdiction: str; submission_type: str
    sections: List[DossierSection]; cover_letter_draft: str
    submission_checklist: List[str]


@router.post("/dossier")
async def draft_dossier(
    body: DossierRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kwargs = dict(
        product_name=body.product_name, product_type=body.product_type,
        jurisdiction=body.jurisdiction, submission_type=body.submission_type,
        product_description=body.product_description,
        active_ingredients=body.active_ingredients or "",
        indication_or_use=body.indication_or_use or "",
        manufacturing_site=body.manufacturing_site or "",
        sections_requested=body.sections_requested or [],
        tenant_id=str(user.tenant_id), user_id=str(user.id),
    )

    if settings.ENABLE_CELERY:
        from app.tasks.ai_tasks import run_dossier
        job = run_dossier.apply_async(kwargs=kwargs)
        return {
            "job_id": job.id,
            "status": "queued",
            "poll_url": f"/api/v1/jobs/{job.id}",
            "message": "Dossier generation started. Poll poll_url for progress.",
        }
    else:
        from app.tasks.ai_tasks import _run_dossier_async
        class _FakeTask:
            def update_state(self, **kwargs): pass
        return await _run_dossier_async(_FakeTask(), **kwargs)
