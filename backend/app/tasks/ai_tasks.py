"""
AI Celery Tasks — Gap Assessment, Dossier, Cleanup
===================================================
These are the long-running AI jobs that were previously blocking HTTP requests.

Progress reporting:
  Each task updates its state with fine-grained progress via
  self.update_state(state="PROGRESS", meta={...}) so the frontend
  can show a live progress bar.

Progress states:
  PENDING   → task queued, not started yet
  PROGRESS  → task running (includes step, percent, message)
  SUCCESS   → completed (result in meta)
  FAILURE   → failed (error in meta)
"""
import json
import time
import asyncio
import structlog
from typing import Optional
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


# ── Progress helper ───────────────────────────────────────────────────────────

def progress(task: Task, step: str, percent: int, message: str) -> None:
    """Update task progress state — polled by frontend."""
    task.update_state(
        state="PROGRESS",
        meta={
            "step": step,
            "percent": percent,
            "message": message,
        },
    )


# ── Gap Assessment Task ───────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.tasks.ai_tasks.run_gap_assessment",
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def run_gap_assessment(
    self: Task,
    product_name: str,
    product_description: str,
    product_type: str,
    target_jurisdictions: list[str],
    current_approvals: list[str],
    intended_claims: str,
    tenant_id: str,
    user_id: str,
) -> dict:
    """
    Run a multi-jurisdiction compliance gap assessment.
    Performs one RAG call per jurisdiction then synthesises the full report.
    """
    try:
        progress(self, "init", 5, "Starting gap assessment…")

        # Run the async RAG pipeline in a new event loop
        # (Celery workers are synchronous — we spin up an event loop per task)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _run_gap_assessment_async(
                    self=self,
                    product_name=product_name,
                    product_description=product_description,
                    product_type=product_type,
                    target_jurisdictions=target_jurisdictions,
                    current_approvals=current_approvals,
                    intended_claims=intended_claims,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            )
        finally:
            loop.close()

        return result

    except SoftTimeLimitExceeded:
        logger.error("gap_assessment_timeout", tenant_id=tenant_id)
        raise self.retry(
            exc=SoftTimeLimitExceeded("Gap assessment timed out"),
            countdown=5,
        )
    except Exception as exc:
        logger.error("gap_assessment_failed", error=str(exc), tenant_id=tenant_id)
        raise


async def _run_gap_assessment_async(
    self: Task,
    product_name: str,
    product_description: str,
    product_type: str,
    target_jurisdictions: list[str],
    current_approvals: list[str],
    intended_claims: str,
    tenant_id: str,
    user_id: str,
) -> dict:
    """Async implementation of gap assessment."""
    from app.db.database import AsyncSessionLocal
    from app.services.rag_service import hybrid_search, get_anthropic, get_openai

    start = time.time()
    n = len(target_jurisdictions)

    # Step 1: Retrieve relevant regulations for each jurisdiction
    progress(self, "retrieval", 10, f"Retrieving regulations for {n} jurisdiction(s)…")

    all_chunks = []
    async with AsyncSessionLocal() as db:
        # Set RLS context for tenant
        from sqlalchemy import text
        await db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
            {"tid": tenant_id},
        )

        for i, jur in enumerate(target_jurisdictions):
            pct = 10 + int((i / n) * 30)
            progress(self, "retrieval", pct, f"Searching {jur.upper()} regulations…")

            chunks = await hybrid_search(
                db=db,
                query=f"{product_name} {product_type} regulatory requirements {intended_claims}",
                jurisdiction=jur,
                domain=product_type,
                top_k=4,
            )
            all_chunks.extend(chunks)

    # Step 2: Build context
    progress(self, "context", 42, "Building regulatory context…")

    from app.services.rag_service import build_context, DOMAIN_SYSTEM_PROMPTS
    context = build_context(all_chunks) if all_chunks else "No specific corpus matches found."

    jur_list = ", ".join(j.upper() for j in target_jurisdictions)
    approvals_note = (
        f"\nCurrent approvals held: {', '.join(current_approvals)}"
        if current_approvals else ""
    )
    claims_note = f"\nIntended claims: {intended_claims}" if intended_claims else ""

    domain_key = product_type if product_type in DOMAIN_SYSTEM_PROMPTS else "general"

    system_prompt = """You are a senior regulatory affairs expert with access to web search.

You have 20+ years experience across global markets including FDA, EMA, CDSCO, TGA, PMDA, \
NMPA, and ANVISA. You provide specific, actionable, jurisdiction-accurate compliance guidance \
grounded in published regulations and official guidance documents.

Use web search to:
1. Check official regulatory databases for product registration status
2. Verify the latest regulatory requirements and guidance documents
3. Find official regulatory body URLs for each jurisdiction

Base your analysis ONLY on established, verifiable regulatory requirements. \
Do not invent or guess requirements. Be consistent — the same product in the same \
jurisdiction must always produce the same core gaps."""

    user_confirmed = ", ".join(current_approvals) if current_approvals else "none"

    user_message = f"""Analyze compliance gaps for:
Product: {product_name}
Type: {product_type}
Description: {product_description}
Target jurisdictions: {jur_list}{approvals_note}{claims_note}

REGULATORY CONTEXT FROM CORPUS:
{context}

STEP 1 — REGISTRATION STATUS CHECK:
For each target jurisdiction, determine registration status:

A) Jurisdictions confirmed approved by user: [{user_confirmed}]
   For these jurisdictions:
   - Set registration_status = "USER_CONFIRMED_APPROVED"
   - Focus gap analysis ONLY on post-market obligations and renewal requirements

B) For all OTHER jurisdictions, use web search to check official databases:
   - US FDA: search "site:accessdata.fda.gov {product_name}"
   - EU EUDAMED: search "site:ec.europa.eu eudamed {product_name}"
   - India CDSCO: search "site:cdsco.gov.in {product_name}"
   - UK MHRA: search "site:gov.uk mhra {product_name}"
   - Australia TGA: search "site:tga.gov.au {product_name}"
   - Canada: search "site:canada.ca {product_name} medical device"
   - Japan PMDA: search "site:pmda.go.jp {product_name}"
   - Singapore HSA: search "site:hsa.gov.sg {product_name}"
   - Malaysia MDA: search "site:portal.mdb.gov.my {product_name}"
   - South Korea MFDS: search "site:mfds.go.kr {product_name}"
   - Brazil ANVISA: search "site:anvisa.gov.br {product_name}"
   - China NMPA: search "site:nmpa.gov.cn {product_name}"
   - UAE MOHAP: search "site:mohap.gov.ae {product_name}"
   - Saudi SFDA: search "site:sfda.gov.sa {product_name}"
   - Thailand FDA: search "site:fda.moph.go.th {product_name}"
   - Indonesia BPOM: search "site:pom.go.id {product_name}"
   - Philippines FDA: search "site:fda.gov.ph {product_name}"
   - New Zealand Medsafe: search "site:medsafe.govt.nz {product_name}"
   - Israel MOH: search "site:health.gov.il {product_name}"
   - Turkey TITCK: search "site:titck.gov.tr {product_name}"
   - South Africa SAHPRA: search "site:sahpra.org.za {product_name}"
   - Switzerland Swissmedic: search "site:swissmedic.ch {product_name}"

   Results:
   - Found in database: registration_status = "FOUND_IN_DATABASE", record source_url
   - Not found: registration_status = "NOT_FOUND"
   - Unable to determine: registration_status = "UNKNOWN"

STEP 2 — PRODUCT RECOGNITION:
Identify if this product is likely already marketed or registered globally \
(e.g. well-known branded medical devices, established drugs, widely sold food supplements).
If it appears to be an already-marketed product:
- State which markets it is likely already approved in
- Focus gaps ONLY on markets where it is NOT yet approved
- Include a note in the summary

STEP 3 — PER-JURISDICTION GAP ANALYSIS:
For EACH jurisdiction, provide a structured analysis:
1. Registration status (from Step 1) and source URL if found
2. Regulatory framework: name the exact law/regulation governing this product type
3. Market status: whether similar products are commonly/rarely/restricted in that market
4. Specific compliance gaps: reference the exact regulation name AND article/rule number \
   (e.g. "EU MDR 2017/745 Article 52", "21 CFR Part 820.30", "India MDR 2017 Schedule 4", \
   "FSSAI FSS Act 2006 Section 22", "ICH Q8(R2)", "DSHEA 1994 Section 5", \
   "WHO TRS No. 961 Annex 4")
5. Minimum required documents: enumerate the mandatory submission documents
6. Realistic timeline in months and cost range in USD based on regulatory authority data
7. Risk level HIGH/MEDIUM/LOW with reason tied to a specific regulation or enforcement record
8. The single most important question the applicant must answer before proceeding
9. Verification URL: the official database URL to verify registration manually

ORDERING RULE: Within each jurisdiction, always list gaps in severity order: HIGH → MEDIUM → LOW.

DATA CONFIDENCE RULE: For each gap, assign data_confidence based on:
- HIGH = requirement is stated explicitly in a published regulation or official guidance
- MEDIUM = based on established regulatory practice or agency precedent
- LOW = estimated or inferred from analogous products or markets

Be specific — do NOT give generic advice. Do NOT invent regulation names or article numbers. \
If a specific article number is uncertain, state the regulation name and mark data_confidence as MEDIUM.

Provide the response in this exact JSON format:
{{
  "product_name": "{product_name}",
  "overall_risk": "HIGH|MEDIUM|LOW",
  "already_marketed_in": ["list of markets where product appears already approved, or empty list"],
  "summary": "2-3 sentence executive summary including registration status findings and markets searched.",
  "gaps": [
    {{
      "jurisdiction": "country/region name",
      "registration_status": "USER_CONFIRMED_APPROVED|FOUND_IN_DATABASE|NOT_FOUND|UNKNOWN",
      "source_url": "URL where registration was found, or null if not found",
      "verification_url": "official regulatory database URL for manual verification",
      "gap": "specific gap referencing the exact regulation name and article/rule number",
      "requirement": "exact regulatory requirement (cite regulation name, article/rule number, and issuing authority)",
      "risk_level": "HIGH|MEDIUM|LOW",
      "risk_reason": "specific reason tied to the cited regulation or documented enforcement history",
      "data_confidence": "HIGH|MEDIUM|LOW",
      "estimated_timeline": "e.g. 18-24 months",
      "cost_range_usd": "e.g. $50,000-$150,000",
      "required_documents": ["specific document 1", "specific document 2"],
      "action_required": "specific first step the applicant must take",
      "key_question": "the single most important question to answer before proceeding"
    }}
  ],
  "critical_path": ["ordered list of 3-5 critical actions referencing actual regulation names"],
  "estimated_total_months": integer_months_to_full_compliance
}}"""

    # Step 3: LLM call
    progress(self, "analysis", 55, "Analysing compliance gaps with AI…")

    raw_response = ""
    try:
        if settings.DEFAULT_LLM == "claude" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                }],
            )
            # Collect all text blocks — web search produces multiple content blocks
            raw_response = ""
            for block in msg.content:
                if block.type == "text":
                    raw_response += block.text
        else:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                max_tokens=3000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            raw_response = resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("gap_llm_failed", error=str(e))
        raise

    # Step 4: Parse result
    progress(self, "parsing", 85, "Parsing gap analysis report…")

    try:
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
            if clean.endswith("```"):
                clean = clean[:-3]
        result = json.loads(clean)
    except json.JSONDecodeError:
        result = {
            "product_name": product_name,
            "overall_risk": "UNKNOWN",
            "summary": raw_response[:500],
            "gaps": [],
            "critical_path": [],
            "estimated_total_months": 0,
        }

    latency_ms = int((time.time() - start) * 1000)
    result["latency_ms"] = latency_ms
    result["sources_used"] = len(all_chunks)

    progress(self, "complete", 100, "Gap assessment complete")
    return result


# ── Dossier Task ──────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.tasks.ai_tasks.run_dossier",
    max_retries=1,
    soft_time_limit=180,
    time_limit=240,
)
def run_dossier(
    self: Task,
    product_name: str,
    product_type: str,
    jurisdiction: str,
    submission_type: str,
    product_description: str,
    active_ingredients: str,
    indication_or_use: str,
    manufacturing_site: str,
    sections_requested: list[str],
    tenant_id: str,
    user_id: str,
) -> dict:
    """Generate a regulatory submission dossier."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_dossier_async(
                    self=self,
                    product_name=product_name,
                    product_type=product_type,
                    jurisdiction=jurisdiction,
                    submission_type=submission_type,
                    product_description=product_description,
                    active_ingredients=active_ingredients,
                    indication_or_use=indication_or_use,
                    manufacturing_site=manufacturing_site,
                    sections_requested=sections_requested,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            )
        finally:
            loop.close()
        return result
    except SoftTimeLimitExceeded:
        raise self.retry(exc=SoftTimeLimitExceeded("Dossier generation timed out"), countdown=5)
    except Exception as exc:
        logger.error("dossier_failed", error=str(exc))
        raise


# Dossier section templates per submission type
DOSSIER_SECTIONS = {
    "CTD": [
        ("1.0", "Module 1: Administrative Information"),
        ("1.1", "1.1 Cover Letter and Application Form"),
        ("1.2", "1.2 Product Information"),
        ("2.0", "Module 2: CTD Summaries"),
        ("2.3", "2.3 Quality Overall Summary (QOS)"),
        ("2.4", "2.4 Nonclinical Overview"),
        ("2.5", "2.5 Clinical Overview"),
        ("2.7", "2.7 Clinical Summary"),
        ("3.0", "Module 3: Quality"),
        ("3.2", "3.2 Drug Substance and Drug Product"),
        ("4.0", "Module 4: Nonclinical Study Reports"),
        ("5.0", "Module 5: Clinical Study Reports"),
    ],
    "FSSAI": [
        ("A", "Part A: Product Identification and Composition"),
        ("B", "Part B: Safety and Nutritional Assessment"),
        ("C", "Part C: Manufacturing Process and GMP"),
        ("D", "Part D: Labeling Compliance"),
        ("E", "Part E: Clinical/Scientific Evidence"),
        ("F", "Part F: Regulatory Summary and Declaration"),
    ],
    "510K": [
        ("1", "Device Description"),
        ("2", "Substantial Equivalence Discussion"),
        ("3", "Proposed Labeling"),
        ("4", "Sterilization and Shelf Life"),
        ("5", "Biocompatibility"),
        ("6", "Performance Testing — Bench"),
        ("7", "Performance Testing — Clinical"),
        ("8", "Summary of Safety and Effectiveness (SSEN)"),
    ],
    "DEFAULT": [
        ("1", "Product Overview and Description"),
        ("2", "Regulatory Background and Justification"),
        ("3", "Quality and Manufacturing"),
        ("4", "Safety Assessment"),
        ("5", "Efficacy / Performance Data"),
        ("6", "Labeling Proposal"),
        ("7", "Regulatory Checklist and Declarations"),
    ],
}


async def _run_dossier_async(
    self: Task,
    product_name: str,
    product_type: str,
    jurisdiction: str,
    submission_type: str,
    product_description: str,
    active_ingredients: str,
    indication_or_use: str,
    manufacturing_site: str,
    sections_requested: list[str],
    tenant_id: str,
    user_id: str,
) -> dict:
    from app.db.database import AsyncSessionLocal
    from app.services.rag_service import hybrid_search, build_context

    start = time.time()
    progress(self, "init", 5, "Initialising dossier generation…")

    # Get applicable sections
    sub_type_upper = submission_type.upper().replace("-", "").replace(" ", "")
    section_map = DOSSIER_SECTIONS.get(
        next((k for k in DOSSIER_SECTIONS if k in sub_type_upper), "DEFAULT"),
        DOSSIER_SECTIONS["DEFAULT"],
    )
    if sections_requested:
        section_map = [(sid, title) for sid, title in section_map if sid in sections_requested]

    n_sections = len(section_map)
    progress(self, "retrieval", 10, f"Retrieving regulatory context for {jurisdiction.upper()}…")

    async with AsyncSessionLocal() as db:
        from sqlalchemy import text
        await db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
            {"tid": tenant_id},
        )
        chunks = await hybrid_search(db, f"{submission_type} dossier requirements {product_type} {jurisdiction}", jurisdiction, product_type, top_k=6)

    context = build_context(chunks) if chunks else "No specific corpus matches found."

    # Generate each section
    progress(self, "generating", 20, f"Generating {n_sections} dossier sections…")

    product_info = f"""Product: {product_name}
Type: {product_type}
Jurisdiction: {jurisdiction.upper()}
Submission: {submission_type}
Description: {product_description}
Active ingredients: {active_ingredients or 'Not specified'}
Indication/Use: {indication_or_use or 'Not specified'}
Manufacturing site: {manufacturing_site or 'Not specified'}"""

    generated_sections = []

    for i, (section_id, section_title) in enumerate(section_map):
        pct = 20 + int((i / n_sections) * 65)
        progress(self, "generating", pct, f"Writing section {section_id}: {section_title[:40]}…")

        section_prompt = f"""You are a regulatory affairs expert drafting a {submission_type} submission dossier.

PRODUCT INFORMATION:
{product_info}

REGULATORY CONTEXT:
{context}

Draft the following dossier section. Be specific, professional, and flag data gaps.

Section: {section_id} — {section_title}

Respond in JSON:
{{
  "section_id": "{section_id}",
  "title": "{section_title}",
  "content": "full drafted section content in markdown format",
  "completeness": "COMPLETE|DRAFT|NEEDS_DATA",
  "missing_data": ["list of data points needed to complete this section"]
}}"""

        try:
            if settings.DEFAULT_LLM == "claude" and settings.ANTHROPIC_API_KEY:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                msg = client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": section_prompt}],
                )
                raw = msg.content[0].text
            else:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": section_prompt}],
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content or ""

            clean = raw.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:]).rstrip("`")
            section_data = json.loads(clean)
        except Exception as e:
            section_data = {
                "section_id": section_id,
                "title": section_title,
                "content": f"Section generation failed: {e}",
                "completeness": "NEEDS_DATA",
                "missing_data": ["Complete manually"],
            }

        generated_sections.append(section_data)

    # Generate cover letter
    progress(self, "cover_letter", 87, "Drafting cover letter…")

    try:
        cover_prompt = f"""Write a professional regulatory submission cover letter for:
{product_info}
Submission to: {jurisdiction.upper()} regulatory authority for {submission_type}
Keep it concise (3-4 paragraphs), professional, and reference key enclosed documents."""

        if settings.DEFAULT_LLM == "claude" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model=settings.CLAUDE_MODEL, max_tokens=600,
                messages=[{"role": "user", "content": cover_prompt}],
            )
            cover_letter = msg.content[0].text
        else:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL, max_tokens=600,
                messages=[{"role": "user", "content": cover_prompt}],
            )
            cover_letter = resp.choices[0].message.content or ""
    except Exception:
        cover_letter = f"[Cover letter for {submission_type} submission of {product_name} to {jurisdiction.upper()} authorities]"

    latency_ms = int((time.time() - start) * 1000)

    # Build submission checklist
    checklist = [
        f"✓ Completed {len(generated_sections)} dossier sections",
        "☐ Fill in NEEDS_DATA sections with actual product data",
        "☐ Obtain GMP certificate from manufacturing site",
        "☐ Commission stability studies if not available",
        f"☐ Engage local regulatory agent in {jurisdiction.upper()}",
        "☐ Verify all laboratory tests from accredited facility",
        "☐ Legal review of all product claims",
        "☐ Submit via official regulatory portal",
    ]

    progress(self, "complete", 100, "Dossier generation complete")

    return {
        "product_name": product_name,
        "jurisdiction": jurisdiction,
        "submission_type": submission_type,
        "sections": generated_sections,
        "cover_letter_draft": cover_letter,
        "submission_checklist": checklist,
        "latency_ms": latency_ms,
        "sources_used": len(chunks),
    }


# ── Periodic maintenance tasks ────────────────────────────────────────────────

@celery_app.task(name="app.tasks.ai_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> dict:
    """Remove expired refresh tokens and reset tokens from the DB."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup_async())
    finally:
        loop.close()


async def _cleanup_async() -> dict:
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text, delete
    from app.db.models import RefreshToken, PasswordResetToken
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        # Bypass RLS for maintenance
        await db.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))

        rt = await db.execute(
            delete(RefreshToken).where(
                RefreshToken.expires_at < now,
                RefreshToken.is_revoked == True,
            ).returning(RefreshToken.id)
        )
        prt = await db.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.expires_at < now,
            ).returning(PasswordResetToken.id)
        )
        await db.commit()

    deleted_rt = len(rt.all())
    deleted_prt = len(prt.all())
    logger.info("token_cleanup", refresh_tokens=deleted_rt, password_reset_tokens=deleted_prt)
    return {"refresh_tokens_deleted": deleted_rt, "reset_tokens_deleted": deleted_prt}


@celery_app.task(name="app.tasks.ai_tasks.refresh_alerts")
def refresh_alerts() -> dict:
    """Placeholder: fetch latest regulatory alerts from external sources."""
    logger.info("alerts_refresh_triggered")
    return {"status": "ok", "message": "Alert refresh triggered (implement external feed)"}
