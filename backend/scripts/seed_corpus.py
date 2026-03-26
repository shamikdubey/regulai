"""
Corpus seeding script — ingests sample regulation text chunks directly into
the vector DB so the RAG pipeline works immediately after deployment.

Usage:
    python -m scripts.seed_corpus

This seeds the DB with real regulation text excerpts.
For production, replace with scraped/parsed full regulation PDFs.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import AsyncSessionLocal, init_db
from app.db.models import RegulationChunk, Regulation
from sqlalchemy import select

# Representative text chunks — real regulation language.
# In production, these are replaced by content parsed from official PDFs.
CORPUS_CHUNKS = [
    # ── INDIA: FSSAI ──────────────────────────────────────────────────────────
    {
        "regulation_short": "FSS Nutraceuticals Regs",
        "jurisdiction": "india",
        "section": "2.1 Definitions",
        "content": (
            "Nutraceutical means a food or part of a food that provides medical or health benefits, "
            "including the prevention and treatment of disease. This includes dietary supplements, "
            "herbal products, processed foods such as cereals, soups and beverages. "
            "Health supplement means a product that supplements the diet and is intended to be taken "
            "orally in tablet, capsule, powder, softgel, gelcap, or liquid form."
        ),
    },
    {
        "regulation_short": "FSS Nutraceuticals Regs",
        "jurisdiction": "india",
        "section": "4.2 Labelling Requirements",
        "content": (
            "Every package of health supplements and nutraceuticals shall carry: "
            "(a) name of the product; (b) list of ingredients with quantities; "
            "(c) net quantity; (d) date of manufacture and expiry; (e) recommended dietary allowance; "
            "(f) direction for use; (g) claim, if any; (h) name and address of manufacturer/packer; "
            "(i) FSSAI logo and licence number. The label shall not claim to treat, cure, or prevent any disease."
        ),
    },
    {
        "regulation_short": "FSS Nutraceuticals Regs",
        "jurisdiction": "india",
        "section": "5.1 Permitted Ingredients",
        "content": (
            "Only ingredients from the positive list as specified in Schedule I and II shall be used "
            "in the manufacture of health supplements and nutraceuticals. "
            "Vitamins and minerals shall conform to the specifications prescribed in the relevant standards. "
            "Botanicals and herbal ingredients shall be used in forms and doses as specified in the Schedule. "
            "Any novel ingredient not in the positive list requires prior approval from FSSAI."
        ),
    },
    {
        "regulation_short": "FSS Nutraceuticals Regs",
        "jurisdiction": "india",
        "section": "7.1 Borderline Products",
        "content": (
            "Products that contain ingredients at doses that could have pharmacological effects "
            "may be regulated as drugs under the Drugs and Cosmetics Act 1940 rather than as food. "
            "The demarcation between a nutraceutical and a drug is determined by the dose, "
            "the claim made, and the intended use. Products making specific therapeutic claims "
            "fall under CDSCO jurisdiction irrespective of the form or labelling."
        ),
    },
    # ── INDIA: CDSCO Medical Devices ─────────────────────────────────────────
    {
        "regulation_short": "MDR 2017",
        "jurisdiction": "india",
        "section": "3. Classification of Medical Devices",
        "content": (
            "Medical devices are classified into four classes based on risk: "
            "Class A (low risk) — examples: tongue depressors, bandages; "
            "Class B (low-moderate risk) — examples: hypodermic needles, suction equipment; "
            "Class C (moderate-high risk) — examples: lung ventilators, bone fixation plates; "
            "Class D (high risk) — examples: heart valves, implantable defibrillators, HIV diagnostics. "
            "Class A devices require only registration. Class B, C, D require quality management system "
            "certification to ISO 13485 and submission of technical dossier to CDSCO."
        ),
    },
    {
        "regulation_short": "MDR 2017",
        "jurisdiction": "india",
        "section": "12. Import Licence",
        "content": (
            "No person shall import any medical device for sale or distribution except under and "
            "in accordance with an import licence. The application for import licence shall be made "
            "to the Central Licensing Authority in Form MD-14. "
            "For Class C and D devices, clinical investigation data generated in India or "
            "bridging study data may be required. Devices approved by a reference regulatory authority "
            "(USFDA, CE Mark, TGA) may be eligible for an expedited 30-day review track."
        ),
    },
    # ── INDIA: AYUSH ─────────────────────────────────────────────────────────
    {
        "regulation_short": "ASU Drugs Rules",
        "jurisdiction": "india",
        "section": "Schedule T — GMP for ASU Drugs",
        "content": (
            "Every manufacturer of Ayurvedic, Siddha, or Unani drugs shall comply with the "
            "Good Manufacturing Practices specified in Schedule T. "
            "The premises shall be of adequate size with separate areas for raw material storage, "
            "manufacturing, quality control, and finished product storage. "
            "All raw materials of plant origin shall be authenticated by a qualified Botanist or "
            "Pharmacognosist before use. The manufacturer shall maintain batch manufacturing records "
            "for each batch produced. Classical preparations listed in official formularies are "
            "exempt from clinical trial requirements."
        ),
    },
    # ── USA: FDA ──────────────────────────────────────────────────────────────
    {
        "regulation_short": "DSHEA",
        "jurisdiction": "usa",
        "section": "Section 3 — Definition of Dietary Supplement",
        "content": (
            "A dietary supplement is a product intended to supplement the diet that contains one or more "
            "of the following dietary ingredients: a vitamin, a mineral, an herb or other botanical, "
            "an amino acid, a dietary substance to supplement the diet by increasing the total dietary "
            "intake, or a concentrate, metabolite, constituent, extract, or combination of any ingredient "
            "described above. A dietary supplement must be labeled as a dietary supplement and is "
            "not represented as a conventional food or as a sole item of a meal or diet."
        ),
    },
    {
        "regulation_short": "DSHEA",
        "jurisdiction": "usa",
        "section": "Section 6 — Structure/Function Claims",
        "content": (
            "A manufacturer may make a claim about the effect of a nutrient or dietary ingredient "
            "intended to affect the structure or function of the body in humans. "
            "Such a claim shall be truthful and not misleading. The manufacturer shall notify FDA "
            "no later than 30 days after first marketing a product bearing such a claim. "
            "All labels bearing such claims must include the disclaimer: "
            "'This statement has not been evaluated by the Food and Drug Administration. "
            "This product is not intended to diagnose, treat, cure, or prevent any disease.'"
        ),
    },
    {
        "regulation_short": "21 CFR Part 111",
        "jurisdiction": "usa",
        "section": "Subpart C — Physical Plant and Grounds",
        "content": (
            "You must use adequate sanitation principles, including as appropriate: "
            "adequate cleaning and sanitizing of utensils and equipment, "
            "taking effective measures to exclude pests from the physical plant, "
            "excluding from the physical plant, areas where dietary supplement components or "
            "dietary supplements are exposed, animals; and preventing contamination of components, "
            "dietary supplements, and contact surfaces with microorganisms, chemicals, filth, or "
            "other extraneous material."
        ),
    },
    # ── EU: EFSA Health Claims ────────────────────────────────────────────────
    {
        "regulation_short": "EC 1924/2006",
        "jurisdiction": "eu",
        "section": "Article 5 — General Conditions for Use",
        "content": (
            "Nutrition and health claims may only be used if the following conditions are met: "
            "(a) the presence, absence or reduced content of a nutrient or other substance "
            "in respect of which the claim is made has been shown to have a beneficial nutritional "
            "or physiological effect as established by generally accepted scientific evidence; "
            "(b) the nutrient or other substance for which the claim is made is contained in the "
            "final product in a significant quantity as defined in Community legislation, "
            "or where no such rules exist, in a quantity that will produce the nutritional or "
            "physiological effect claimed as established by generally accepted scientific evidence."
        ),
    },
    {
        "regulation_short": "EU MDR 2017/745",
        "jurisdiction": "eu",
        "section": "Article 51 — Classification Rules",
        "content": (
            "Devices are divided into the following classes: Class I, Class IIa, Class IIb and Class III. "
            "Classification of devices shall be governed by Annex VIII taking into account the intended "
            "purpose of the devices. "
            "Software which drives a device or influences the use of a device falls into the same class "
            "as that device. Software which is independent of any other device shall be classified in "
            "its own right. Software intended to provide information which is used to take decisions with "
            "diagnosis or therapeutic purposes is classified as class IIa, except if such decisions have "
            "an impact that may cause death or serious deterioration of health, in which case it is "
            "classified as class III."
        ),
    },
    # ── CHINA: NMPA ───────────────────────────────────────────────────────────
    {
        "regulation_short": "Health Food Registration (BlueCap)",
        "jurisdiction": "china",
        "section": "Article 4 — Registration vs Filing",
        "content": (
            "Health foods produced domestically or imported using raw materials specified in the "
            "catalogue of vitamins and minerals and their corresponding amounts may be filed with "
            "the provincial market supervision administration. "
            "All other health foods, including those using novel raw materials or raw materials "
            "outside the permitted catalogue, shall be registered with NMPA. "
            "Imported health foods shall all be registered regardless of their raw material composition. "
            "The registration certificate is valid for 5 years and may be renewed."
        ),
    },
    # ── JAPAN: FOSHU ──────────────────────────────────────────────────────────
    {
        "regulation_short": "FOSHU",
        "jurisdiction": "japan",
        "section": "Eligibility Criteria",
        "content": (
            "To be eligible for FOSHU approval, a food must: "
            "(1) present a clear relationship between the food or food ingredients and health maintenance or promotion; "
            "(2) be based on established scientific evidence for the health effect; "
            "(3) not contain anything which may have adverse health effects; "
            "(4) not significantly differ in nutritional composition compared to similar foods; "
            "(5) the form of ingestion should be ordinary food form (not tablet, capsule, etc.); "
            "(6) each single serving should contain an effective dose of the active component. "
            "Applications are reviewed by the Consumer Affairs Agency (CAA) with scientific assessment "
            "by the Food Safety Commission of Japan."
        ),
    },
    # ── AUSTRALIA: TGA ────────────────────────────────────────────────────────
    {
        "regulation_short": "TG Act",
        "jurisdiction": "australia",
        "section": "Complementary Medicine — Listed vs Registered",
        "content": (
            "Complementary medicines may be either 'listed' or 'registered' on the ARTG. "
            "Listed medicines contain only low-risk, pre-approved ingredients from TGA's "
            "Permitted Ingredients list. Sponsors self-assess compliance and list via online portal. "
            "Listed medicines may make only 'general level health claims' that must be substantiated. "
            "Registered medicines contain higher-risk ingredients or make higher-level health claims. "
            "These require TGA evaluation of quality, safety, and efficacy evidence before inclusion on ARTG. "
            "Ayurvedic and traditional Chinese medicine products can be listed if they use permitted ingredients "
            "and adhere to TGA Advertising Codes."
        ),
    },
    # ── CANADA: Health Canada ────────────────────────────────────────────────
    {
        "regulation_short": "NHPR",
        "jurisdiction": "canada",
        "section": "Section 3 — Product Licence",
        "content": (
            "No person shall sell a natural health product unless the product has a product licence "
            "issued under these Regulations. An application for a product licence shall be submitted "
            "to the Minister and shall contain the product name, the name and address of the applicant, "
            "the brand name, a quantitative list of all medicinal ingredients, the non-medicinal ingredients, "
            "the recommended conditions of use including the recommended use, purpose, route of administration, "
            "dose, duration of use, and risk information. "
            "Evidence of safety and efficacy may include traditional use evidence (30+ years), "
            "references to traditional pharmacopoeias, or clinical evidence."
        ),
    },
    # ── SINGAPORE: HSA ───────────────────────────────────────────────────────
    {
        "regulation_short": "Health Products Act",
        "jurisdiction": "singapore",
        "section": "Part 3 — Health Supplements",
        "content": (
            "Health supplements are not required to undergo pre-market evaluation by HSA provided that "
            "all ingredients are on HSA's permitted ingredients list and claims comply with permitted "
            "health claims. Advertisers must ensure claims are not false or misleading. "
            "Products must be manufactured under GMP conditions. "
            "A health supplement shall not contain: scheduled poisons, potent botanicals above specified limits, "
            "or ingredients with significant pharmacological activity at the dose used. "
            "Post-market surveillance by HSA includes market sampling, adverse event monitoring, and "
            "compliance audits of manufacturers and importers."
        ),
    },
]


async def seed_corpus():
    await init_db()
    print("Seeding regulation corpus text chunks…")

    async with AsyncSessionLocal() as db:
        total = 0
        for chunk_data in CORPUS_CHUNKS:
            # Find matching regulation
            result = await db.execute(
                select(Regulation).where(
                    Regulation.short_name == chunk_data["regulation_short"],
                    Regulation.jurisdiction == chunk_data["jurisdiction"],
                )
            )
            regulation = result.scalar_one_or_none()

            if not regulation:
                print(f"  ⚠ Regulation not found: {chunk_data['regulation_short']} ({chunk_data['jurisdiction']}) — run seed_data.py first")
                continue

            # Check for duplicate chunk
            existing = await db.execute(
                select(RegulationChunk).where(
                    RegulationChunk.regulation_id == regulation.id,
                    RegulationChunk.section == chunk_data["section"],
                )
            )
            if existing.scalar_one_or_none():
                print(f"  ↩ Skipping existing chunk: {chunk_data['regulation_short']} § {chunk_data['section']}")
                continue

            # Get current max chunk_index
            from sqlalchemy import func
            idx_result = await db.execute(
                select(func.count(RegulationChunk.id)).where(
                    RegulationChunk.regulation_id == regulation.id
                )
            )
            idx = idx_result.scalar() or 0

            # Try to embed — if no API key, store without embedding (keyword search still works)
            embedding = None
            try:
                from app.services.rag_service import get_embedding
                embedding = await get_embedding(chunk_data["content"])
                print(f"  ✓ Embedded: {chunk_data['regulation_short']} § {chunk_data['section']}")
            except Exception as e:
                print(f"  ⚠ No embedding (no API key?): {str(e)[:60]} — storing text only")

            chunk = RegulationChunk(
                regulation_id=regulation.id,
                chunk_index=idx,
                section=chunk_data["section"],
                content=chunk_data["content"],
                embedding=embedding,
                token_count=len(chunk_data["content"].split()),
                metadata_={"source": "seed"},
            )
            db.add(chunk)
            total += 1

        await db.commit()
        print(f"✅ Seeded {total} regulation text chunks")
        print("💡 For full coverage, run ingestion with official PDF files")


if __name__ == "__main__":
    asyncio.run(seed_corpus())
