"""
Compliance Review — ported from Reguard into RegulAI
  POST   /compliance-review/reviews
  GET    /compliance-review/reviews
  GET    /compliance-review/reviews/{id}
  POST   /compliance-review/reviews/{id}/analyze
  DELETE /compliance-review/reviews/{id}
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user
from app.core.config import get_settings
import anthropic
import json

router = APIRouter()
settings = get_settings()

class ReviewCreate(BaseModel):
    title: str
    document_content: str
    country: Optional[str] = None
    domain: Optional[str] = None
    regulation: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("title must not be blank")
        return v

    @field_validator("document_content")
    @classmethod
    def content_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("document_content must not be blank")
        return v

class AnalyzeRequest(BaseModel):
    additional_context: Optional[str] = ""

@router.post("/compliance-review/reviews", status_code=201)
async def create_review(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: ReviewCreate = ...,
):
    review_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO compliance_reviews
            (id, tenant_id, user_id, title, document_content, country, domain, regulation, status, score)
        VALUES
            (:id, :tenant_id, :user_id, :title, :document_content, :country, :domain, :regulation, 'pending', NULL)
    """), {
        "id": review_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
        "title": body.title,
        "document_content": body.document_content,
        "country": body.country,
        "domain": body.domain,
        "regulation": body.regulation,
    })
    await db.commit()
    return {
        "id": review_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
        "title": body.title,
        "status": "pending",
        "score": None,
        "country": body.country,
        "domain": body.domain,
        "regulation": body.regulation,
    }

@router.get("/compliance-review/reviews")
async def list_reviews(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    domain: Optional[str] = None,
):
    query = "SELECT * FROM compliance_reviews WHERE tenant_id = :tenant_id"
    params = {"tenant_id": str(user.tenant_id)}
    if status:
        query += " AND status = :status"
        params["status"] = status
    if domain:
        query += " AND domain = :domain"
        params["domain"] = domain
    result = await db.execute(text(query), params)
    return [dict(r) for r in result.mappings().all()]

@router.get("/compliance-review/reviews/{review_id}")
async def get_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT * FROM compliance_reviews
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(review_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    return dict(row)

@router.post("/compliance-review/reviews/{review_id}/analyze")
async def analyze_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: AnalyzeRequest = ...,
):
    result = await db.execute(text("""
        SELECT * FROM compliance_reviews
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(review_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": f"""
You are a regulatory compliance expert. Review this document and score it 0-100.

Document: {row['document_content'][:3000]}
Country: {row['country'] or 'General'}
Domain: {row['domain'] or 'General'}
Regulation: {row['regulation'] or 'General'}
Additional context: {body.additional_context}

Respond ONLY in JSON format:
{{
  "score": <0-100>,
  "status": "compliant" | "partially_compliant" | "non_compliant",
  "critical_issues": [{{"issue": "...", "requirement": "...", "status": "NOT_MET"}}],
  "warnings": [{{"issue": "...", "requirement": "...", "status": "PARTIALLY_MET"}}],
  "passed": [{{"item": "...", "status": "MET"}}],
  "summary": "..."
}}
        """}]
    )

    try:
        analysis = json.loads(message.content[0].text)
    except Exception:
        analysis = {
            "score": 50,
            "status": "partially_compliant",
            "critical_issues": [],
            "warnings": [],
            "passed": [],
            "summary": message.content[0].text
        }

    score = analysis.get("score", 50)
    status = analysis.get("status", "partially_compliant")

    await db.execute(text("""
        UPDATE compliance_reviews
        SET score = :score, status = :status, analysis = :analysis
        WHERE id = :id
    """), {
        "score": score,
        "status": status,
        "analysis": json.dumps(analysis),
        "id": str(review_id),
    })
    await db.commit()
    return analysis

@router.delete("/compliance-review/reviews/{review_id}", status_code=204)
async def delete_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT id FROM compliance_reviews
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(review_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Review not found")
    await db.execute(text(
        "DELETE FROM compliance_reviews WHERE id = :id"
    ), {"id": str(review_id)})
    await db.commit()
