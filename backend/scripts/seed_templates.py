"""
Seed initial document templates for top 10 country/domain combos.

Run from repo root:
  cd backend && python -m scripts.seed_templates

Requires ANTHROPIC_API_KEY in environment (or .env file).
Uses Neon DB (DATABASE_URL from environment or .env).
"""
import asyncio
import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import anthropic
import asyncpg

NEON_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_ZW5xkQL7CnYO@ep-little-grass-amlbd07z.c-5.us-east-1.aws.neon.tech/neondb",
).replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-6"

SEED_COMBOS = [
    ("India",  "MEDICAL_DEVICE", "CHECKLIST"),
    ("India",  "MEDICAL_DEVICE", "COVER_LETTER"),
    ("US",     "MEDICAL_DEVICE", "CHECKLIST"),
    ("US",     "MEDICAL_DEVICE", "COVER_LETTER"),
    ("EU",     "MEDICAL_DEVICE", "CHECKLIST"),
    ("India",  "FOOD",           "CHECKLIST"),
    ("US",     "FOOD",           "CHECKLIST"),
    ("India",  "PHARMA",         "CHECKLIST"),
    ("US",     "PHARMA",         "CHECKLIST"),
    ("India",  "NUTRACEUTICAL",  "CHECKLIST"),
]

TRUST_SCORE = 65
TRUST_LEVEL = "MODERATE"


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text[:120]


def generate_template(client: anthropic.Anthropic, country: str, domain: str, document_type: str) -> dict:
    prompt = f"""You are a senior regulatory affairs expert creating a {document_type} template.

Country: {country}
Regulatory Domain: {domain}

Create a detailed, professional {document_type} that:
1. References specific regulations by name and article number
2. Includes all mandatory sections required by {country} regulations
3. Uses [PLACEHOLDER] for fields the user must fill in
4. Is formatted clearly with numbered sections
5. Includes a "Regulatory Basis" section citing exact regulations

For the trust score, extract:
- regulation_reference: the primary regulation this is based on
- confidence_note: one sentence explaining basis for this template

IMPORTANT: Only reference regulations you are certain exist.
Mark uncertain items with [VERIFY: description]

Return JSON:
{{
  "title": "template title",
  "content_html": "full HTML content with sections using <h2>, <p>, <ol>, <ul> tags",
  "regulation_reference": "specific regulation cited",
  "confidence_note": "basis for this template",
  "suggested_trust_score": 65
}}"""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw[:-3]

    return json.loads(raw)


async def seed():
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    conn = await asyncpg.connect(NEON_DSN)

    print(f"Connected to Neon DB. Seeding {len(SEED_COMBOS)} templates...\n")

    seeded = 0
    for country, domain, document_type in SEED_COMBOS:
        label = f"{country} / {domain} / {document_type}"
        print(f"  Generating: {label} ...", end=" ", flush=True)

        try:
            data = generate_template(client, country, domain, document_type)
        except Exception as e:
            print(f"FAILED (AI error): {e}")
            continue

        title = data.get("title") or f"{document_type} — {country} {domain}"
        content_html = data.get("content_html", "")
        regulation_reference = data.get("regulation_reference", "")

        base_slug = _slugify(f"{country}-{domain}-{document_type}")
        slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"
        template_id = str(uuid.uuid4())

        try:
            await conn.execute("""
                INSERT INTO document_templates (
                    id, tenant_id, title, slug, country, domain, document_type,
                    content_html, regulation_reference, trust_score, trust_level,
                    is_ai_generated, generation_model
                ) VALUES (
                    $1, NULL, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10,
                    TRUE, $11
                )
            """,
                template_id, title, slug, country, domain, document_type,
                content_html, regulation_reference, TRUST_SCORE, TRUST_LEVEL,
                CLAUDE_MODEL,
            )
            print(f"OK — trust={TRUST_SCORE} [{TRUST_LEVEL}]")
            seeded += 1
        except Exception as e:
            print(f"FAILED (DB error): {e}")

    await conn.close()
    print(f"\nDone. {seeded}/{len(SEED_COMBOS)} templates seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
