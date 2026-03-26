"""
Document Processing Tasks
=========================
Handles the full pipeline for user-uploaded documents:
  1. Extract text from PDF/DOCX
  2. Chunk into overlapping segments
  3. Generate embeddings (OpenAI text-embedding-3-large)
  4. Store chunks with tenant_id in regulation_chunks (private corpus)
  5. Update document processing_status
"""
import asyncio
import structlog
from celery.exceptions import SoftTimeLimitExceeded
from app.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

CHUNK_SIZE = 800        # tokens per chunk
CHUNK_OVERLAP = 150     # token overlap between chunks


@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.ingest_document",
    max_retries=2,
    soft_time_limit=120,
    time_limit=180,
)
def ingest_document(
    self,
    document_id: str,
    tenant_id: str,
    file_path: str,
    mime_type: str,
    jurisdiction: str | None,
    domain: str | None,
) -> dict:
    """Process and embed an uploaded document into the tenant's private corpus."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                _ingest_async(self, document_id, tenant_id, file_path, mime_type, jurisdiction, domain)
            )
        finally:
            loop.close()
    except SoftTimeLimitExceeded:
        _update_status(document_id, tenant_id, "failed", "Timeout during processing")
        raise
    except Exception as exc:
        logger.error("document_ingest_failed", document_id=document_id, error=str(exc))
        _update_status(document_id, tenant_id, "failed", str(exc))
        raise


def _update_status(document_id: str, tenant_id: str, status: str, error: str | None = None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_update_status_async(document_id, tenant_id, status, error))
    finally:
        loop.close()


async def _update_status_async(document_id: str, tenant_id: str, status: str, error: str | None):
    from app.db.database import AsyncSessionLocal
    from app.db.models import Document
    from sqlalchemy import select, text
    import uuid

    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))
        result = await db.execute(select(Document).where(Document.id == uuid.UUID(document_id)))
        doc = result.scalar_one_or_none()
        if doc:
            doc.processing_status = status
            if error:
                doc.metadata_ = {**(doc.metadata_ or {}), "error": error}
            await db.commit()


async def _ingest_async(
    task,
    document_id: str,
    tenant_id: str,
    file_path: str,
    mime_type: str,
    jurisdiction: str | None,
    domain: str | None,
) -> dict:
    from app.db.database import AsyncSessionLocal
    from app.db.models import Document, Regulation, RegulationChunk
    from app.services.storage import storage
    from app.services.rag_service import get_embedding
    from sqlalchemy import select, text
    import uuid

    task.update_state(state="PROGRESS", meta={"step": "extract", "percent": 10, "message": "Extracting text…"})

    # Read file bytes
    content_bytes = storage.get_file_bytes(file_path, tenant_id)

    # Extract text
    text_content = _extract_text(content_bytes, mime_type)
    if not text_content.strip():
        raise ValueError("No readable text found in document")

    task.update_state(state="PROGRESS", meta={"step": "chunk", "percent": 30, "message": "Chunking document…"})

    # Chunk the text
    chunks = _chunk_text(text_content, CHUNK_SIZE, CHUNK_OVERLAP)
    n_chunks = len(chunks)
    logger.info("document_chunked", document_id=document_id, chunks=n_chunks)

    task.update_state(state="PROGRESS", meta={"step": "embed", "percent": 40, "message": f"Embedding {n_chunks} chunks…"})

    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))

        # Create a synthetic Regulation record for this document
        # (reuses the existing regulation_chunks table structure)
        doc_result = await db.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Create parent regulation entry representing this document
        reg = Regulation(
            name=doc.filename,
            short_name=doc.filename[:50],
            jurisdiction=jurisdiction or "unknown",
            domain=domain or "general",
            status="active",
            description=f"User-uploaded document: {doc.filename}",
        )
        db.add(reg)
        await db.flush()

        # Embed and store chunks
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            pct = 40 + int((i / n_chunks) * 50)
            if i % 5 == 0:
                task.update_state(
                    state="PROGRESS",
                    meta={"step": "embed", "percent": pct, "message": f"Embedding chunk {i+1}/{n_chunks}…"},
                )
            try:
                embedding = await get_embedding(chunk_text)
            except Exception as e:
                logger.warning("embedding_failed", chunk=i, error=str(e))
                embedding = None

            chunk_obj = RegulationChunk(
                regulation_id=reg.id,
                tenant_id=uuid.UUID(tenant_id),   # Private corpus — scoped to tenant
                chunk_index=i,
                content=chunk_text,
                embedding=embedding,
                token_count=len(chunk_text.split()),
            )
            chunk_objects.append(chunk_obj)
            db.add(chunk_obj)

        # Update document status
        doc.processing_status = "processed"
        doc.chunk_count = n_chunks

        await db.commit()

    task.update_state(state="PROGRESS", meta={"step": "complete", "percent": 100, "message": "Document processed"})
    return {"document_id": document_id, "chunks": n_chunks, "status": "processed"}


def _extract_text(content_bytes: bytes, mime_type: str) -> str:
    """Extract plain text from PDF or DOCX."""
    if mime_type == "application/pdf":
        try:
            import pypdf
            import io
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            return "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as e:
            raise ValueError(f"PDF extraction failed: {e}")

    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(content_bytes))
            return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
        except Exception as e:
            raise ValueError(f"DOCX extraction failed: {e}")

    elif mime_type == "text/plain":
        return content_bytes.decode("utf-8", errors="replace")

    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping word-count chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += chunk_size - overlap
    return [c for c in chunks if c.strip()]
