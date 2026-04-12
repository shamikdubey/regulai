"""
Document Editor — ported from Reguard into RegulAI
  POST   /document-editor/drafts
  GET    /document-editor/drafts
  GET    /document-editor/drafts/{id}
  PUT    /document-editor/drafts/{id}
  DELETE /document-editor/drafts/{id}
  POST   /document-editor/drafts/{id}/ai-review
  POST   /document-editor/drafts/{id}/ai-template
  POST   /document-editor/drafts/{id}/ai-restructure
  GET    /document-editor/drafts/{id}/versions
  POST   /document-editor/drafts/{id}/versions
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

router = APIRouter()
settings = get_settings()

class DraftCreate(BaseModel):
    title: str
    content: str = ""
    document_type: str = "general"
    country: Optional[str] = None
    domain: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("title must not be blank")
        return v

class DraftUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None

class AIReviewRequest(BaseModel):
    focus: Optional[str] = "general compliance"

class AITemplateRequest(BaseModel):
    document_type: str
    country: Optional[str] = None
    domain: Optional[str] = None

class AIRestructureRequest(BaseModel):
    instruction: Optional[str] = "improve structure and clarity"

class VersionCreate(BaseModel):
    content: str
    comment: Optional[str] = ""

@router.post("/document-editor/drafts", status_code=201)
async def create_draft(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: DraftCreate = ...,
):
    draft_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO document_drafts
            (id, tenant_id, user_id, title, content, document_type, country, domain, status)
        VALUES
            (:id, :tenant_id, :user_id, :title, :content, :document_type, :country, :domain, 'draft')
    """), {
        "id": draft_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
        "title": body.title,
        "content": body.content,
        "document_type": body.document_type,
        "country": body.country,
        "domain": body.domain,
    })
    await db.commit()
    return {
        "id": draft_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
        "title": body.title,
        "content": body.content,
        "document_type": body.document_type,
        "country": body.country,
        "domain": body.domain,
        "status": "draft",
    }

@router.get("/document-editor/drafts")
async def list_drafts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_type: Optional[str] = None,
    status: Optional[str] = None,
):
    query = "SELECT * FROM document_drafts WHERE tenant_id = :tenant_id"
    params = {"tenant_id": str(user.tenant_id)}
    if document_type:
        query += " AND document_type = :document_type"
        params["document_type"] = document_type
    if status:
        query += " AND status = :status"
        params["status"] = status
    result = await db.execute(text(query), params)
    return [dict(r) for r in result.mappings().all()]

@router.get("/document-editor/drafts/{draft_id}")
async def get_draft(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT * FROM document_drafts
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Draft not found")
    return dict(row)

@router.put("/document-editor/drafts/{draft_id}")
async def update_draft(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: DraftUpdate = ...,
):
    result = await db.execute(text("""
        SELECT id FROM document_drafts
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Draft not found")
    if body.title:
        await db.execute(text(
            "UPDATE document_drafts SET title = :title WHERE id = :id"
        ), {"title": body.title, "id": str(draft_id)})
    if body.content is not None:
        await db.execute(text(
            "UPDATE document_drafts SET content = :content WHERE id = :id"
        ), {"content": body.content, "id": str(draft_id)})
    if body.status:
        await db.execute(text(
            "UPDATE document_drafts SET status = :status WHERE id = :id"
        ), {"status": body.status, "id": str(draft_id)})
    await db.commit()
    return {"status": "updated"}

@router.delete("/document-editor/drafts/{draft_id}", status_code=204)
async def delete_draft(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT id FROM document_drafts
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.execute(text(
        "DELETE FROM document_drafts WHERE id = :id"
    ), {"id": str(draft_id)})
    await db.commit()

@router.post("/document-editor/drafts/{draft_id}/ai-review")
async def ai_review(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: AIReviewRequest = ...,
):
    result = await db.execute(text("""
        SELECT * FROM document_drafts
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Draft not found")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": f"""
Review this regulatory document for compliance issues.
Focus: {body.focus}
Document type: {row['document_type']}
Content: {row['content'][:3000]}

Respond in JSON: {{"general_feedback": "...", "suggestions": [{{"issue": "...", "recommendation": "..."}}]}}
        """}]
    )
    import json
    try:
        feedback = json.loads(message.content[0].text)
    except Exception:
        feedback = {"general_feedback": message.content[0].text, "suggestions": []}
    return feedback

@router.post("/document-editor/drafts/{draft_id}/ai-template")
async def ai_template(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: AITemplateRequest = ...,
):
    result = await db.execute(text("""
        SELECT id FROM document_drafts WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Draft not found")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""
Generate a regulatory document template.
Type: {body.document_type}
Country: {body.country or 'General'}
Domain: {body.domain or 'General'}
Return only the template text, ready to fill in.
        """}]
    )
    template = message.content[0].text
    await db.execute(text(
        "UPDATE document_drafts SET content = :content WHERE id = :id"
    ), {"content": template, "id": str(draft_id)})
    await db.commit()
    return {"template": template}

@router.post("/document-editor/drafts/{draft_id}/ai-restructure")
async def ai_restructure(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: AIRestructureRequest = ...,
):
    result = await db.execute(text("""
        SELECT * FROM document_drafts WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Draft not found")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""
Restructure this document: {body.instruction}
Content: {row['content'][:3000]}
Return only the restructured document text.
        """}]
    )
    restructured = message.content[0].text
    await db.execute(text(
        "UPDATE document_drafts SET content = :content WHERE id = :id"
    ), {"content": restructured, "id": str(draft_id)})
    await db.commit()
    return {"content": restructured}

@router.get("/document-editor/drafts/{draft_id}/versions")
async def list_versions(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT id FROM document_drafts WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Draft not found")
    versions = await db.execute(text("""
        SELECT * FROM document_draft_versions WHERE draft_id = :draft_id ORDER BY created_at DESC
    """), {"draft_id": str(draft_id)})
    return [dict(r) for r in versions.mappings().all()]

@router.post("/document-editor/drafts/{draft_id}/versions", status_code=201)
async def create_version(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: VersionCreate = ...,
):
    result = await db.execute(text("""
        SELECT id FROM document_drafts WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(draft_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Draft not found")
    version_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO document_draft_versions (id, draft_id, tenant_id, content, comment)
        VALUES (:id, :draft_id, :tenant_id, :content, :comment)
    """), {
        "id": version_id,
        "draft_id": str(draft_id),
        "tenant_id": str(user.tenant_id),
        "content": body.content,
        "comment": body.comment,
    })
    await db.commit()
    return {"id": version_id, "draft_id": str(draft_id), "comment": body.comment}
