"""
Privacy & GDPR Endpoints — Phase 3
====================================
DELETE /privacy/me          — Right to erasure (deletes all personal data)
GET    /privacy/export      — Data portability export (JSON download)
POST   /privacy/check-pii   — Check uploaded file for PII before ingestion
GET    /privacy/dpa         — Data Processing Agreement (rendered HTML)
POST   /privacy/consent     — Record/update consent choices
GET    /privacy/consent      — Get current consent state
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user, revoke_all_user_sessions
from app.services.gdpr import erase_user_data, export_user_data, check_document_for_pii
from app.core.config import get_settings

router = APIRouter(prefix="/privacy", tags=["Privacy"])
settings = get_settings()


class EraseRequest(BaseModel):
    confirmation: str         # must be "DELETE MY ACCOUNT"
    reason: Optional[str] = "user_request"


class ConsentUpdate(BaseModel):
    analytics: bool = False
    marketing: bool = False
    third_party_sharing: bool = False


# ── Right to Erasure ─────────────────────────────────────────────────────────

@router.delete("/me", status_code=200)
async def erase_my_data(
    body: EraseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete all personal data.

    This action is IRREVERSIBLE. Requires confirmation string "DELETE MY ACCOUNT".
    - Deletes user account, sessions, API keys, uploaded documents
    - Anonymises query log entries (removes query text/responses, keeps metadata)
    - Deletes all document files from S3

    Complies with GDPR Art. 17 and India DPDP Act 2023 §13.
    """
    if body.confirmation != "DELETE MY ACCOUNT":
        raise HTTPException(
            400,
            "Confirmation must be exactly: DELETE MY ACCOUNT"
        )

    summary = await erase_user_data(
        db=db,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        requested_by=str(user.id),
        reason=body.reason or "user_request",
    )

    return {
        "message": "Your account and all associated data has been permanently deleted.",
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Data Portability Export ───────────────────────────────────────────────────

@router.get("/export")
async def export_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all personal data as a JSON download.
    Complies with GDPR Art. 20 (Right to Data Portability).
    """
    data = await export_user_data(
        db=db,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
    )

    filename = f"regulai_data_export_{user.email}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


# ── PII Check ─────────────────────────────────────────────────────────────────

@router.post("/check-pii")
async def check_file_for_pii(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Scan an uploaded file for PII before ingestion.
    Call this before /documents/upload to warn users about sensitive content.
    """
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large for PII scan (max 10 MB)")

    content = await file.read()
    findings = await check_document_for_pii(content, file.content_type or "text/plain")

    return {
        "filename": file.filename,
        "pii_detected": len(findings) > 0,
        "findings": findings,
        "recommendation": (
            "This document contains potential PII. Ensure you have lawful basis to process it "
            "and that it is necessary for your compliance workflow."
            if findings else
            "No common PII patterns detected."
        ),
    }


# ── Consent Management ────────────────────────────────────────────────────────

@router.get("/consent")
async def get_consent(user: User = Depends(get_current_user)):
    """Get current consent state for this user."""
    meta = user.metadata_ or {}
    consent = meta.get("consent", {})
    return {
        "analytics": consent.get("analytics", False),
        "marketing": consent.get("marketing", False),
        "third_party_sharing": consent.get("third_party_sharing", False),
        "updated_at": consent.get("updated_at"),
        "version": consent.get("version", "1.0"),
    }


@router.post("/consent")
async def update_consent(
    body: ConsentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record or update user consent choices."""
    meta = user.metadata_ or {}
    meta["consent"] = {
        "analytics": body.analytics,
        "marketing": body.marketing,
        "third_party_sharing": body.third_party_sharing,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "ip_recorded": True,    # IP is recorded at middleware level
    }
    user.metadata_ = meta
    await db.commit()
    return {"message": "Consent preferences saved", "consent": meta["consent"]}


# ── Data Processing Information ───────────────────────────────────────────────

@router.get("/processing-info")
async def data_processing_info(_: User = Depends(get_current_user)):
    """
    Return data processing information per GDPR Art. 13/14 and DPDP §6.
    """
    return {
        "controller": {
            "name": "RegulAI",
            "contact": "privacy@regulai.app",
            "dpo": "dpo@regulai.app",
        },
        "india_grievance_officer": {
            "name": "Grievance Officer",
            "email": "grievance@regulai.app",
            "response_time_days": 30,
        },
        "data_categories": [
            {
                "category": "Identity data",
                "data": ["Name", "Email address", "Role"],
                "purpose": "Account management and authentication",
                "legal_basis": "Contract (GDPR Art. 6(1)(b)) / DPDP Consent",
                "retention": "Duration of account + 30 days after deletion",
            },
            {
                "category": "Usage data",
                "data": ["Query text", "Jurisdictions queried", "AI responses"],
                "purpose": "Providing the compliance AI service",
                "legal_basis": "Contract performance",
                "retention": "12 months",
            },
            {
                "category": "Technical data",
                "data": ["IP address", "Device/browser info", "Session tokens"],
                "purpose": "Security and fraud prevention",
                "legal_basis": "Legitimate interests (GDPR Art. 6(1)(f))",
                "retention": "90 days",
            },
            {
                "category": "Uploaded documents",
                "data": ["Document content", "Vector embeddings"],
                "purpose": "Powering custom regulatory corpus queries",
                "legal_basis": "Contract performance",
                "retention": "Until deleted or account closure",
            },
        ],
        "rights": [
            "Right to access (GET /privacy/export)",
            "Right to erasure (DELETE /privacy/me)",
            "Right to rectification (PUT /auth/me)",
            "Right to portability (GET /privacy/export)",
            "Right to object (POST /privacy/consent)",
            "Right to restrict processing (contact privacy@regulai.app)",
        ],
        "transfers": "Data processed in AWS ap-south-1 (Mumbai) by default. "
                     "EU customers may request EU-region processing.",
        "automated_decision_making": "AI responses are generated automatically but do not "
                                      "constitute binding regulatory decisions. Human review required.",
    }
