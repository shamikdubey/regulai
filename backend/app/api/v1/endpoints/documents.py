import os
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import Document, User
from app.schemas.schemas import DocumentOut
from app.services.auth_service import get_current_user
from app.services.ingestion_service import ingest_document

router = APIRouter()
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


@router.post("/upload", response_model=DocumentOut, summary="Upload a regulatory document")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    jurisdiction: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    # Size check
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    # Save to disk
    upload_dir = Path(settings.UPLOAD_DIR) / str(user.tenant_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / safe_filename
    file_path.write_bytes(content)

    # Create DB record
    doc = Document(
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        filename=file.filename or "unnamed",
        file_path=str(file_path),
        file_size_bytes=len(content),
        mime_type=file.content_type,
        jurisdiction=jurisdiction,
        domain=domain,
        processing_status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Kick off ingestion in background with a FRESH session (request session may be closed)
    from app.db.database import AsyncSessionLocal
    async def _run_ingestion():
        async with AsyncSessionLocal() as bg_db:
            try:
                await ingest_document(
                    bg_db, str(doc.id), str(file_path), file.content_type,
                    jurisdiction, domain, str(user.tenant_id),
                )
            except Exception as e:
                import structlog as _sl
                _sl.get_logger().error("ingestion_task_failed", error=str(e))

    background_tasks.add_task(_run_ingestion)

    return doc


@router.get("/", response_model=List[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == user.tenant_id)
        .order_by(Document.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()


@router.get("/{doc_id}/status")
async def document_status(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == uuid.UUID(doc_id),
            Document.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"id": str(doc.id), "status": doc.processing_status, "chunk_count": doc.chunk_count}
