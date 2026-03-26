"""
RAG (Retrieval-Augmented Generation) service.
Handles semantic search over regulation corpus + LLM response generation.
"""
import hashlib
import hmac
import json
import time
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import structlog

from app.core.config import get_settings
from app.db.models import RegulationChunk, Regulation, RegulatoryBody, QueryLog

logger = structlog.get_logger()
settings = get_settings()

# Lazy imports to avoid startup cost
_anthropic_client = None
_openai_client = None
_embeddings_model = None


def get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def get_embedding(text_input: str) -> list[float]:
    """Generate embedding using OpenAI text-embedding-3-large."""
    client = get_openai()
    resp = client.embeddings.create(
        input=text_input,
        model=settings.EMBEDDING_MODEL,
        dimensions=1536,
    )
    return resp.data[0].embedding


DOMAIN_SYSTEM_PROMPTS = {
    "food": """You are a regulatory compliance expert specializing in food safety regulations.
You have access to official regulatory documents from food safety authorities worldwide (FSSAI, FDA, EFSA, NMPA, etc.).
Your role is to provide accurate, citation-backed compliance guidance.""",

    "pharma": """You are a regulatory affairs expert specializing in pharmaceutical regulations.
You have access to official guidance from CDSCO, FDA, EMA, PMDA, MHRA, ANVISA, TGA, Health Canada, HSA, and NMPA.
Provide accurate drug approval pathway guidance with specific regulation citations.""",

    "device": """You are a medical device regulatory expert.
You have knowledge of MDR 2017 (India), 510(k)/PMA (USA), EU MDR 2017/745, China Class I-III, Japan PMD Act, UK UKCA, and other frameworks.
Always clarify device classification before discussing pathways.""",

    "nutra": """You are a nutraceutical and health supplement regulatory expert.
You understand the FSSAI/CDSCO dual-jurisdiction challenge in India, DSHEA in the USA, EC Regulation 1924/2006 in EU,
Japan's FOSHU/FFC system, Canada's NHPR, and Australia's Listed/Registered CM pathways.
Flag regulatory grey zones explicitly.""",

    "ayurveda": """You are an Ayurveda, traditional medicine, and natural health product regulatory expert.
You understand AYUSH regulations in India, Canada NPN under NHPR, Australia TGA Listed pathway, EU THMPD Directive,
China TCM Law 2017, and USA DSHEA for herbal products.
Note that Ayurvedic products have very different treatment across jurisdictions.""",

    "general": """You are a global regulatory compliance expert covering food safety, pharmaceuticals,
medical devices, nutraceuticals, and traditional medicine across 10 major jurisdictions.
Always cite specific regulations, be conservative, and flag where professional regulatory consultation is required."""
}

RESPONSE_SCHEMA = """
Respond ONLY with valid JSON in this exact format:
{
  "answer": "Comprehensive answer to the compliance question",
  "citations": [
    {
      "regulation": "Regulation name",
      "section": "Specific section/clause if known",
      "jurisdiction": "Country/region",
      "year": "Year",
      "relevance": "Why this regulation applies"
    }
  ],
  "confidence": 0.85,
  "caveats": ["Any important limitations or grey areas"],
  "next_steps": ["Recommended actions for the user"],
  "regulatory_bodies": ["List of relevant regulatory bodies to contact"]
}
"""


async def hybrid_search(
    db: AsyncSession,
    query: str,
    jurisdiction: Optional[str],
    domain: Optional[str],
    top_k: int = 5,
) -> list[dict]:
    """Hybrid BM25 + vector semantic search over regulation chunks."""
    embedding = await get_embedding(query)

    # Build filters
    filters = []
    params: dict = {"embedding": str(embedding), "top_k": top_k, "query": query}

    if jurisdiction:
        filters.append("r.jurisdiction = :jurisdiction")
        params["jurisdiction"] = jurisdiction
    if domain:
        filters.append("r.domain = :domain")
        params["domain"] = domain

    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

    sql = text(f"""
        SELECT
            rc.id,
            rc.content,
            rc.section,
            rc.metadata,
            r.name AS regulation_name,
            r.jurisdiction,
            r.domain,
            r.year,
            r.source_url,
            rb.acronym AS body_acronym,
            1 - (rc.embedding <=> :embedding::vector) AS semantic_score,
            ts_rank(to_tsvector('english', rc.content), plainto_tsquery('english', :query)) AS bm25_score
        FROM regulation_chunks rc
        JOIN regulations r ON rc.regulation_id = r.id
        LEFT JOIN regulatory_bodies rb ON r.regulatory_body_id = rb.id
        {where_clause}
        ORDER BY (0.7 * (1 - (rc.embedding <=> :embedding::vector)) + 0.3 * ts_rank(to_tsvector('english', rc.content), plainto_tsquery('english', :query))) DESC
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    return [
        {
            "id": str(row["id"]),
            "content": row["content"],
            "section": row["section"],
            "regulation_name": row["regulation_name"],
            "jurisdiction": row["jurisdiction"],
            "domain": row["domain"],
            "year": row["year"],
            "source_url": row["source_url"],
            "body_acronym": row["body_acronym"],
            "semantic_score": float(row["semantic_score"] or 0),
            "bm25_score": float(row["bm25_score"] or 0),
        }
        for row in rows
    ]


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into context for the LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[SOURCE {i}]\n"
            f"Regulation: {chunk['regulation_name']}\n"
            f"Jurisdiction: {chunk['jurisdiction'].upper()}\n"
            f"Domain: {chunk['domain'].upper()}\n"
            f"Year: {chunk.get('year', 'N/A')}\n"
            f"Body: {chunk.get('body_acronym', 'N/A')}\n"
            f"Section: {chunk.get('section', 'N/A')}\n"
            f"Content:\n{chunk['content']}\n"
        )
    return "\n---\n".join(parts)


def sign_log(log_data: dict) -> str:
    """HMAC-SHA256 signature for audit log tamper detection."""
    payload = json.dumps(log_data, sort_keys=True, default=str)
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


async def query_compliance(
    db: AsyncSession,
    query: str,
    jurisdiction: Optional[str],
    domain: Optional[str],
    tenant_id: str,
    user_id: str,
) -> dict:
    """Main RAG pipeline: retrieve + generate + log."""
    start_time = time.time()

    log = logger.bind(
        tenant_id=tenant_id, user_id=user_id,
        jurisdiction=jurisdiction, domain=domain
    )
    log.info("compliance_query_start", query=query[:100])

    # 1. Retrieve relevant chunks
    chunks = await hybrid_search(db, query, jurisdiction, domain, top_k=settings.RAG_TOP_K)
    context = build_context(chunks) if chunks else "No specific regulatory documents found in corpus for this query."

    # 2. Select system prompt
    domain_key = domain if domain in DOMAIN_SYSTEM_PROMPTS else "general"
    system_prompt = DOMAIN_SYSTEM_PROMPTS[domain_key]

    jur_note = f" Focus on {jurisdiction.upper()} regulations." if jurisdiction else ""
    system_prompt += jur_note
    system_prompt += "\n\nALWAYS base answers on the provided regulatory context. Be conservative — when uncertain, say so explicitly. NEVER fabricate regulation names or clause numbers."

    user_message = f"""REGULATORY CONTEXT:
{context}

USER QUESTION:
{query}

{RESPONSE_SCHEMA}"""

    # 3. LLM call
    raw_response = ""
    try:
        if settings.DEFAULT_LLM == "claude" and settings.ANTHROPIC_API_KEY:
            client = get_anthropic()
            msg = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_response = msg.content[0].text
        else:
            client = get_openai()
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                max_tokens=settings.MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            raw_response = resp.choices[0].message.content or ""
    except Exception as e:
        log.error("llm_call_failed", error=str(e))
        raise

    # 4. Parse response
    try:
        # Strip markdown code fences if present
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean)
    except json.JSONDecodeError:
        result = {
            "answer": raw_response,
            "citations": [],
            "confidence": 0.5,
            "caveats": ["Response could not be structured — raw output provided"],
            "next_steps": [],
            "regulatory_bodies": [],
        }

    latency_ms = int((time.time() - start_time) * 1000)
    chunk_ids = [c["id"] for c in chunks]

    # 5. Audit log with HMAC
    log_data = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "query": query,
        "jurisdiction": jurisdiction,
        "domain": domain,
        "citations": result.get("citations", []),
        "confidence": result.get("confidence"),
        "chunk_ids": chunk_ids,
        "latency_ms": latency_ms,
    }
    signature = sign_log(log_data)

    query_log = QueryLog(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        query=query,
        jurisdiction=jurisdiction,
        domain=domain,
        response=result.get("answer", ""),
        citations=result.get("citations", []),
        confidence=result.get("confidence"),
        retrieved_chunk_ids=chunk_ids,
        latency_ms=latency_ms,
        hmac_signature=signature,
    )
    db.add(query_log)
    await db.commit()

    log.info("compliance_query_complete", latency_ms=latency_ms, chunks_used=len(chunks))

    return {
        **result,
        "query_id": str(query_log.id),
        "latency_ms": latency_ms,
        "sources_used": len(chunks),
    }
