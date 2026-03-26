"""
Query endpoints — Phase 2
  POST /query          — synchronous (backward-compatible fallback)
  POST /query/stream   — SSE streaming (primary web endpoint)
  GET  /jobs/{job_id}  — poll background job status
"""
import asyncio
import json
import time
import uuid
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User, Tenant, QueryLog
from app.schemas.schemas import QueryRequest, QueryResponse
from app.services.auth_service import get_current_user, get_current_tenant
from app.services.rag_service import hybrid_search, build_context, get_embedding, DOMAIN_SYSTEM_PROMPTS, sign_log
from app.middleware.rate_limit import check_tenant_query_limit
from app.core.config import get_settings
import structlog

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


# ── SSE streaming query (primary endpoint) ─────────────────────────────────

@router.post("/query/stream")
async def compliance_query_stream(
    request_body: QueryRequest,
    request: Request,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream a compliance query response token-by-token via Server-Sent Events.
    Frontend uses EventSource / fetch ReadableStream to display tokens as they arrive.

    SSE format:
      data: {"token": "text fragment"}\n\n
      data: {"citations": [...], "confidence": 0.85, ...}\n\n
      data: [DONE]\n\n
    """
    # Access control
    if request_body.jurisdiction and tenant.allowed_jurisdictions:
        if request_body.jurisdiction not in tenant.allowed_jurisdictions:
            raise HTTPException(403, f"Jurisdiction '{request_body.jurisdiction}' not licensed")
    if request_body.domain and tenant.allowed_domains:
        if request_body.domain not in tenant.allowed_domains:
            raise HTTPException(403, f"Domain '{request_body.domain}' not licensed")

    await check_tenant_query_limit(user, db)

    async def event_generator() -> AsyncGenerator[str, None]:
        start = time.time()
        full_response = []

        try:
            # 1. Retrieval phase — emit status event
            yield _sse({"type": "status", "step": "retrieval", "message": "Searching regulatory corpus…"})
            await asyncio.sleep(0)  # yield to event loop

            chunks = await hybrid_search(
                db, request_body.query,
                request_body.jurisdiction, request_body.domain,
                top_k=settings.RAG_TOP_K,
            )
            context = build_context(chunks) if chunks else "No specific documents found in corpus."

            yield _sse({"type": "status", "step": "generating", "message": f"Found {len(chunks)} relevant sources. Generating response…"})
            await asyncio.sleep(0)

            # 2. Build prompt
            domain_key = request_body.domain if request_body.domain in DOMAIN_SYSTEM_PROMPTS else "general"
            system_prompt = DOMAIN_SYSTEM_PROMPTS[domain_key]
            if request_body.jurisdiction:
                system_prompt += f" Focus on {request_body.jurisdiction.upper()} regulations."
            system_prompt += "\n\nALWAYS base answers on the provided regulatory context. Be conservative. NEVER fabricate regulation names."

            user_message = f"""REGULATORY CONTEXT:\n{context}\n\nUSER QUESTION:\n{request_body.query}

Respond with a clear, well-structured answer. After your full answer, on a new line output a JSON block like this:
```json
{{"citations": [...], "confidence": 0.85, "caveats": [...], "next_steps": [...], "regulatory_bodies": [...]}}
```"""

            # 3. Stream tokens
            if settings.DEFAULT_LLM == "claude" and settings.ANTHROPIC_API_KEY:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

                with client.messages.stream(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=settings.MAX_TOKENS,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                ) as stream:
                    for text_chunk in stream.text_stream:
                        full_response.append(text_chunk)
                        yield _sse({"type": "token", "token": text_chunk})
                        await asyncio.sleep(0)

            elif settings.OPENAI_API_KEY:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                stream = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    max_tokens=settings.MAX_TOKENS,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        full_response.append(delta)
                        yield _sse({"type": "token", "token": delta})
                        await asyncio.sleep(0)
            else:
                yield _sse({"type": "error", "message": "No LLM API key configured"})
                return

            # 4. Parse metadata from response
            raw = "".join(full_response)
            citations, confidence, caveats, next_steps, reg_bodies = _parse_metadata(raw)
            latency_ms = int((time.time() - start) * 1000)

            # 5. Save audit log
            log_data = {
                "tenant_id": str(user.tenant_id), "user_id": str(user.id),
                "query": request_body.query, "jurisdiction": request_body.jurisdiction,
                "domain": request_body.domain, "citations": citations,
                "confidence": confidence, "chunk_ids": [c["id"] for c in chunks],
                "latency_ms": latency_ms,
            }
            query_log = QueryLog(
                tenant_id=user.tenant_id, user_id=user.id,
                query=request_body.query, jurisdiction=request_body.jurisdiction,
                domain=request_body.domain, response=raw[:5000],
                citations=citations, confidence=confidence,
                retrieved_chunk_ids=[c["id"] for c in chunks],
                latency_ms=latency_ms,
                hmac_signature=sign_log(log_data),
            )
            db.add(query_log)
            await db.commit()

            # 6. Emit final metadata event
            yield _sse({
                "type": "done",
                "query_id": str(query_log.id),
                "citations": citations,
                "confidence": confidence,
                "caveats": caveats,
                "next_steps": next_steps,
                "regulatory_bodies": reg_bodies,
                "latency_ms": latency_ms,
                "sources_used": len(chunks),
            })
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            # Client disconnected — don't error, just stop
            logger.info("stream_cancelled", user_id=str(user.id))
        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield _sse({"type": "error", "message": "An error occurred during generation"})
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering for SSE
        },
    )


# ── Synchronous query (backward compat) ───────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def compliance_query(
    request_body: QueryRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Non-streaming fallback. Use /query/stream for web UI."""
    if request_body.jurisdiction and tenant.allowed_jurisdictions:
        if request_body.jurisdiction not in tenant.allowed_jurisdictions:
            raise HTTPException(403, f"Jurisdiction '{request_body.jurisdiction}' not licensed")

    await check_tenant_query_limit(user, db)

    from app.services.rag_service import query_compliance
    result = await query_compliance(
        db=db, query=request_body.query,
        jurisdiction=request_body.jurisdiction,
        domain=request_body.domain,
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
    )
    return QueryResponse(**result)


# ── Job status polling ──────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """
    Poll the status of a background Celery job (gap assessment, dossier).

    Returns:
      { "status": "PENDING|PROGRESS|SUCCESS|FAILURE",
        "percent": 0-100,
        "message": "...",
        "result": {...} (only when status=SUCCESS),
        "error": "..." (only when status=FAILURE) }
    """
    if not settings.ENABLE_CELERY:
        raise HTTPException(503, "Background jobs not enabled (ENABLE_CELERY=false)")

    from celery.result import AsyncResult
    from app.celery_app import celery_app

    result = AsyncResult(job_id, app=celery_app)

    if result.state == "PENDING":
        return {"status": "PENDING", "percent": 0, "message": "Job queued…"}

    if result.state == "PROGRESS":
        meta = result.info or {}
        return {
            "status": "PROGRESS",
            "percent": meta.get("percent", 0),
            "step": meta.get("step", ""),
            "message": meta.get("message", "Processing…"),
        }

    if result.state == "SUCCESS":
        return {"status": "SUCCESS", "percent": 100, "result": result.result}

    if result.state == "FAILURE":
        return {
            "status": "FAILURE",
            "percent": 0,
            "error": str(result.info) if result.info else "Unknown error",
        }

    return {"status": result.state, "percent": 0}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _parse_metadata(raw: str) -> tuple:
    """Extract JSON metadata block from end of streamed response."""
    citations, confidence, caveats, next_steps, reg_bodies = [], 0.7, [], [], []
    try:
        if "```json" in raw:
            json_part = raw.split("```json")[-1].split("```")[0].strip()
            meta = json.loads(json_part)
            citations = meta.get("citations", [])
            confidence = meta.get("confidence", 0.7)
            caveats = meta.get("caveats", [])
            next_steps = meta.get("next_steps", [])
            reg_bodies = meta.get("regulatory_bodies", [])
    except Exception:
        pass
    return citations, confidence, caveats, next_steps, reg_bodies
