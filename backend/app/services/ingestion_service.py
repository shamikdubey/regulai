"""
Document ingestion service — handles PDF/DOCX upload, parsing, chunking, embedding, and vector storage.
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.models import Document, RegulationChunk, Regulation
from app.services.rag_service import get_embedding

logger = structlog.get_logger()
settings = get_settings()


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX."""
    from docx import Document as DocxDocument
    doc = DocxDocument(file_path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [{"content": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]


async def ingest_document(
    db: AsyncSession,
    document_id: str,
    file_path: str,
    mime_type: str,
    jurisdiction: Optional[str],
    domain: Optional[str],
    tenant_id: str,
) -> int:
    """
    Full ingestion pipeline:
    1. Extract text
    2. Chunk
    3. Embed each chunk
    4. Store in DB with vector
    Returns number of chunks created.
    """
    log = logger.bind(document_id=document_id, tenant_id=tenant_id)
    log.info("ingestion_start")

    # Extract
    try:
        if mime_type == "application/pdf":
            text = extract_text_from_pdf(file_path)
        elif mime_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
            text = extract_text_from_docx(file_path)
        elif mime_type == "text/plain":
            text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
    except Exception as e:
        log.error("extraction_failed", error=str(e))
        raise

    log.info("text_extracted", char_count=len(text))

    # Chunk
    chunks = chunk_text(text)
    log.info("chunking_complete", chunk_count=len(chunks))

    # Create a Regulation record linked to this document
    regulation = Regulation(
        name=f"Uploaded Document — {os.path.basename(file_path)}",
        jurisdiction=jurisdiction,
        domain=domain,
        status="active",
        description=f"User-uploaded document (tenant: {tenant_id})",
        metadata_={"source": "upload", "document_id": document_id, "tenant_id": tenant_id},
    )
    db.add(regulation)
    await db.flush()  # get regulation.id

    # Embed + store chunks
    for chunk_data in chunks:
        try:
            embedding = await get_embedding(chunk_data["content"])
        except Exception as e:
            log.warning("embedding_failed", chunk_index=chunk_data["chunk_index"], error=str(e))
            embedding = None

        chunk = RegulationChunk(
            regulation_id=regulation.id,
            chunk_index=chunk_data["chunk_index"],
            content=chunk_data["content"],
            embedding=embedding,
            token_count=len(chunk_data["content"].split()),
            metadata_={"source": "upload"},
        )
        db.add(chunk)
        # Small pause to avoid rate limiting embeddings API
        await asyncio.sleep(0.05)

    # Update document status
    from sqlalchemy import update
    await db.execute(
        update(Document)
        .where(Document.id == uuid.UUID(document_id))
        .values(processing_status="completed", chunk_count=len(chunks))
    )
    await db.commit()
    log.info("ingestion_complete", chunks=len(chunks))
    return len(chunks)
