"""
Allowable Limits endpoint.
Covers: food additives (max use levels by food category), contaminants
(heavy metals, mycotoxins, pesticide MRLs), microbiological criteria,
and nutrient reference values — all per jurisdiction.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, String, func, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import datetime

from app.db.database import get_db, Base
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()


# ── Model ─────────────────────────────────────────────────────────────────────

class AllowableLimit(Base):
    __tablename__ = "allowable_limits"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    substance: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    substance_aliases: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    cas_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ins_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    limit_type: Mapped[str] = mapped_column(String(50), nullable=False)  # additive / contaminant / pesticide / microbiological / nutrient_rv
    category: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "preservative", "heavy_metal", "mycotoxin"
    food_matrix: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "Beverages", "Infant formula", "All foods"
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    limit_value: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "1000 mg/kg", "0.1 mg/kg", "absent"
    limit_unit: Mapped[str] = mapped_column(String(50), nullable=False)     # mg/kg / μg/kg / ppb / ppm / CFU/g / %
    adi_tdi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # ADI or TDI
    regulatory_basis: Mapped[str] = mapped_column(String(255), nullable=False)  # CODEX STAN 192, 21 CFR 172, FSSAI Schedule etc.
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active / withdrawn / under_review
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, server_default=func.now())


class AllowableLimitOut(BaseModel):
    id: uuid.UUID
    substance: str
    substance_aliases: Optional[list]
    cas_number: Optional[str]
    ins_number: Optional[str]
    limit_type: str
    category: str
    food_matrix: str
    jurisdiction: str
    limit_value: str
    limit_unit: str
    adi_tdi: Optional[str]
    regulatory_basis: str
    notes: Optional[str]
    status: str
    model_config = {"from_attributes": True}


# ── Comprehensive seed data ────────────────────────────────────────────────────

LIMITS_DATA = [
    # ── FOOD ADDITIVES — PRESERVATIVES ───────────────────────────────────────
    {"substance":"Sodium Benzoate","substance_aliases":["E211","INS 211","Benzoic acid sodium salt"],"cas_number":"532-32-1","ins_number":"211","limit_type":"additive","category":"preservative","food_matrix":"Carbonated water-based flavoured drinks","jurisdiction":"india","limit_value":"600","limit_unit":"mg/kg","adi_tdi":"ADI 0–5 mg/kg bw (JECFA)","regulatory_basis":"FSSAI FSS (FPS) Regs 2011 — Schedule II Part A","notes":"Expressed as benzoic acid. Combined use with sorbic acid not to exceed individual limits."},
    {"substance":"Sodium Benzoate","substance_aliases":["E211","INS 211"],"cas_number":"532-32-1","ins_number":"211","limit_type":"additive","category":"preservative","food_matrix":"Non-alcoholic flavoured beverages","jurisdiction":"usa","limit_value":"1000","limit_unit":"mg/kg","adi_tdi":"ADI 0–5 mg/kg bw","regulatory_basis":"21 CFR 184.1733 — GRAS; FDA maximum 0.1% (=1000 mg/kg)","notes":"GRAS when used in accordance with GMP. Limit is 0.1% of food."},
    {"substance":"Sodium Benzoate","substance_aliases":["E211"],"cas_number":"532-32-1","ins_number":"211","limit_type":"additive","category":"preservative","food_matrix":"Non-alcoholic flavoured beverages","jurisdiction":"eu","limit_value":"150","limit_unit":"mg/L","adi_tdi":"ADI 0–5 mg/kg bw","regulatory_basis":"EU Regulation 1333/2008 — Annex II, Category 14.1.4","notes":"EU limit significantly lower than US. Stricter for beverages. Ban applies in certain baby foods."},
    {"substance":"Sodium Benzoate","substance_aliases":["E211"],"cas_number":"532-32-1","ins_number":"211","limit_type":"additive","category":"preservative","food_matrix":"Non-alcoholic flavoured beverages","jurisdiction":"codex","limit_value":"600","limit_unit":"mg/kg","adi_tdi":"ADI 0–5 mg/kg bw","regulatory_basis":"CODEX STAN 192-1995 (Rev 2023) GSFA — Table 3","notes":"Codex GSFA reference value. Individual countries may be more restrictive."},

    {"substance":"Potassium Sorbate","substance_aliases":["E202","INS 202","Sorbic acid potassium salt"],"cas_number":"24634-61-5","ins_number":"202","limit_type":"additive","category":"preservative","food_matrix":"Bakery products (bread, cakes)","jurisdiction":"india","limit_value":"1000","limit_unit":"mg/kg","adi_tdi":"ADI 0–25 mg/kg bw (JECFA)","regulatory_basis":"FSSAI FSS Regulations — Schedule II Part A","notes":"Expressed as sorbic acid. Used to prevent mould growth."},
    {"substance":"Potassium Sorbate","substance_aliases":["E202"],"cas_number":"24634-61-5","ins_number":"202","limit_type":"additive","category":"preservative","food_matrix":"Cheese (processed)","jurisdiction":"eu","limit_value":"2000","limit_unit":"mg/kg","adi_tdi":"ADI 0–25 mg/kg bw","regulatory_basis":"EU Regulation 1333/2008 Annex II — Category 01.7","notes":"Expressed as sorbic acid."},

    # ── FOOD ADDITIVES — COLOURS ──────────────────────────────────────────────
    {"substance":"Tartrazine","substance_aliases":["FD&C Yellow 5","E102","INS 102","CI Food Yellow 4"],"cas_number":"1934-21-0","ins_number":"102","limit_type":"additive","category":"colour","food_matrix":"Soft drinks and beverages","jurisdiction":"india","limit_value":"100","limit_unit":"mg/kg","adi_tdi":"ADI 0–7.5 mg/kg bw (JECFA)","regulatory_basis":"FSSAI FSS Regulations — Schedule II Part B (Permitted Synthetic Colours)","notes":"Must be declared by name on label in India. Mandatory warning in EU."},
    {"substance":"Tartrazine","substance_aliases":["FD&C Yellow 5","E102"],"cas_number":"1934-21-0","ins_number":"102","limit_type":"additive","category":"colour","food_matrix":"Soft drinks","jurisdiction":"usa","limit_value":"GMP","limit_unit":"GMP","adi_tdi":"ADI 0–7.5 mg/kg bw","regulatory_basis":"21 CFR 74.705 — Certified colour; no specific max level; GMP applies","notes":"FD&C Yellow No. 5. Requires declaration on label under US law (allergy alert). GMP limits apply."},
    {"substance":"Tartrazine","substance_aliases":["E102"],"cas_number":"1934-21-0","ins_number":"102","limit_type":"additive","category":"colour","food_matrix":"Soft drinks","jurisdiction":"eu","limit_value":"100","limit_unit":"mg/L","adi_tdi":"ADI 0–7.5 mg/kg bw","regulatory_basis":"EU Regulation 1333/2008 Annex II; Directive 2010/67/EU","notes":"MANDATORY warning: 'may have an adverse effect on activity and attention in children' required on label when used."},
    {"substance":"Titanium Dioxide","substance_aliases":["E171","INS 171","CI 77891"],"cas_number":"13463-67-7","ins_number":"171","limit_type":"additive","category":"colour","food_matrix":"Confectionery","jurisdiction":"india","limit_value":"GMP","limit_unit":"GMP (quantum satis)","adi_tdi":"ADI 'not specified' (JECFA — historical)","regulatory_basis":"FSSAI FSS Regulations — Schedule II Part B","notes":"Permitted in India as white colour. GMP limits apply."},
    {"substance":"Titanium Dioxide","substance_aliases":["E171"],"cas_number":"13463-67-7","ins_number":"171","limit_type":"additive","category":"colour","food_matrix":"All food categories","jurisdiction":"eu","limit_value":"PROHIBITED","limit_unit":"N/A","adi_tdi":"Not established (genotoxicity concern)","regulatory_basis":"EU Regulation 2022/63 — Amendment to Annex II of Regulation 1333/2008","notes":"BANNED in EU as of 7 August 2022. No longer permitted as food additive. Still permitted in pharmaceuticals (coatings) pending separate review."},

    # ── CONTAMINANTS — HEAVY METALS ───────────────────────────────────────────
    {"substance":"Lead (Pb)","substance_aliases":["Lead","Plumbum"],"cas_number":"7439-92-1","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Fruit juices","jurisdiction":"india","limit_value":"0.5","limit_unit":"mg/kg","adi_tdi":"PTWI 25 μg/kg bw (JECFA, withdrawn 2010 — no safe level established)","regulatory_basis":"FSSAI FSS (Contaminants, Toxins and Residues) Regulations 2011","notes":"JECFA withdrew PTWI in 2010 as no safe threshold exists. Minimise as low as reasonably achievable (ALARA)."},
    {"substance":"Lead (Pb)","substance_aliases":["Lead"],"cas_number":"7439-92-1","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Cereals and cereal products","jurisdiction":"eu","limit_value":"0.2","limit_unit":"mg/kg","adi_tdi":"No safe level (EFSA 2010)","regulatory_basis":"EU Commission Regulation 2023/915 (amending 1881/2006)","notes":"EU has some of the strictest lead limits globally. Infant formula: 0.01 mg/kg."},
    {"substance":"Lead (Pb)","substance_aliases":["Lead"],"cas_number":"7439-92-1","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Canned vegetables","jurisdiction":"codex","limit_value":"0.1","limit_unit":"mg/kg","adi_tdi":"ALARA","regulatory_basis":"CODEX STAN 193-1995 (General Standard for Contaminants and Toxins in Food)","notes":"Codex general maximum level. Categories vary."},
    {"substance":"Lead (Pb)","substance_aliases":["Lead"],"cas_number":"7439-92-1","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Dietary supplements","jurisdiction":"usa","limit_value":"Not federally set (California Prop 65: 0.5 μg/day)","limit_unit":"μg/day","adi_tdi":"No safe level","regulatory_basis":"FDA guidance 2023 (not mandatory); California Prop 65 mandatory for CA","notes":"FDA has draft guidance on lead in food but no mandatory federal ML for supplements. California Prop 65 requires warning label above 0.5 μg/day."},
    {"substance":"Arsenic (As) — inorganic","substance_aliases":["Inorganic arsenic","iAs"],"cas_number":"7440-38-2","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Rice and rice products","jurisdiction":"india","limit_value":"0.3","limit_unit":"mg/kg","adi_tdi":"BMDL01: 0.3 μg/kg bw/day (EFSA/JECFA)","regulatory_basis":"FSSAI FSS (Contaminants) Regulations 2011","notes":"Inorganic arsenic is a Group 1 carcinogen (IARC). Rice is a major dietary source."},
    {"substance":"Arsenic (As) — inorganic","substance_aliases":["Inorganic arsenic"],"cas_number":"7440-38-2","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Rice (polished)","jurisdiction":"eu","limit_value":"0.2","limit_unit":"mg/kg","adi_tdi":"No safe threshold","regulatory_basis":"EU Commission Regulation 2023/915 amending 1881/2006","notes":"Infant rice products: 0.1 mg/kg. EU adopted lower limits than Codex."},
    {"substance":"Cadmium (Cd)","substance_aliases":["Cadmium"],"cas_number":"7440-43-9","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Leafy vegetables","jurisdiction":"india","limit_value":"0.2","limit_unit":"mg/kg","adi_tdi":"TWI 2.5 μg/kg bw/week (EFSA 2009)","regulatory_basis":"FSSAI FSS (Contaminants) Regulations 2011","notes":"Cadmium accumulates in kidneys. Spinach, celery particularly prone to accumulation."},
    {"substance":"Mercury (Total Hg)","substance_aliases":["Mercury","Hydrargyrum"],"cas_number":"7439-97-6","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Fish (non-predatory)","jurisdiction":"india","limit_value":"0.5","limit_unit":"mg/kg","adi_tdi":"PTWI 4 μg/kg bw for methylmercury (JECFA)","regulatory_basis":"FSSAI FSS Regulations 2011","notes":"Predatory fish (shark, swordfish): 1.0 mg/kg. Pregnant women advised to limit consumption."},
    {"substance":"Mercury (Total Hg)","substance_aliases":["Mercury"],"cas_number":"7439-97-6","ins_number":None,"limit_type":"contaminant","category":"heavy_metal","food_matrix":"Fish (predatory — tuna, swordfish)","jurisdiction":"eu","limit_value":"1.0","limit_unit":"mg/kg","adi_tdi":"TWI 1.3 μg/kg bw methylmercury (EFSA)","regulatory_basis":"EU Commission Regulation 2023/915","notes":"Advisory for vulnerable groups. Non-predatory fish: 0.3 mg/kg."},

    # ── CONTAMINANTS — MYCOTOXINS ─────────────────────────────────────────────
    {"substance":"Aflatoxin B1","substance_aliases":["AFB1"],"cas_number":"1162-65-8","ins_number":None,"limit_type":"contaminant","category":"mycotoxin","food_matrix":"Groundnuts (peanuts) for direct consumption","jurisdiction":"india","limit_value":"10","limit_unit":"μg/kg","adi_tdi":"No safe threshold (IARC Group 1 carcinogen)","regulatory_basis":"FSSAI FSS Regulations 2011 — Tolerance Limits for Aflatoxins","notes":"Combined aflatoxin limit (B1+B2+G1+G2): 15 μg/kg. For groundnut oil: AFB1 ≤10 μg/kg."},
    {"substance":"Aflatoxin B1","substance_aliases":["AFB1"],"cas_number":"1162-65-8","ins_number":None,"limit_type":"contaminant","category":"mycotoxin","food_matrix":"Cereals for direct human consumption","jurisdiction":"eu","limit_value":"2","limit_unit":"μg/kg","adi_tdi":"No safe threshold","regulatory_basis":"EU Commission Regulation 2023/915 amending 1881/2006","notes":"Baby foods: 0.1 μg/kg. EU has strictest global limits for aflatoxins."},
    {"substance":"Total Aflatoxins (B1+B2+G1+G2)","substance_aliases":["Total aflatoxins","Aflatoxins"],"cas_number":"Various","ins_number":None,"limit_type":"contaminant","category":"mycotoxin","food_matrix":"Tree nuts for human consumption","jurisdiction":"codex","limit_value":"10","limit_unit":"μg/kg","adi_tdi":"No safe threshold","regulatory_basis":"CODEX STAN 193-1995, amended 2023","notes":"Codex reference level. Sampling plans critical for mycotoxin testing."},
    {"substance":"Ochratoxin A (OTA)","substance_aliases":["OTA","Ochratoxin A"],"cas_number":"303-47-9","ins_number":None,"limit_type":"contaminant","category":"mycotoxin","food_matrix":"Cereals and cereal products","jurisdiction":"eu","limit_value":"3","limit_unit":"μg/kg","adi_tdi":"TDI 17 ng/kg bw/day (EFSA 2020)","regulatory_basis":"EU Commission Regulation 2023/915","notes":"Coffee (roasted beans): 10 μg/kg. Wine: 2 μg/L."},
    {"substance":"Deoxynivalenol (DON)","substance_aliases":["DON","Vomitoxin"],"cas_number":"51481-10-8","ins_number":None,"limit_type":"contaminant","category":"mycotoxin","food_matrix":"Cereal-based foods for infants","jurisdiction":"eu","limit_value":"200","limit_unit":"μg/kg","adi_tdi":"TDI 1 μg/kg bw/day (EFSA)","regulatory_basis":"EU Commission Regulation 2023/915","notes":"Unprocessed cereals: 1250 μg/kg. DON is the most prevalent mycotoxin in wheat."},

    # ── MICROBIOLOGICAL CRITERIA ───────────────────────────────────────────────
    {"substance":"Salmonella spp.","substance_aliases":["Salmonella"],"cas_number":None,"ins_number":None,"limit_type":"microbiological","category":"pathogen","food_matrix":"Ready-to-eat foods","jurisdiction":"india","limit_value":"Absent","limit_unit":"per 25g","adi_tdi":None,"regulatory_basis":"FSSAI FSS Regulations 2011 — Microbiological Standards, Schedule I","notes":"Zero tolerance for Salmonella in RTE foods. Mandatory testing for each batch."},
    {"substance":"Salmonella spp.","substance_aliases":["Salmonella"],"cas_number":None,"ins_number":None,"limit_type":"microbiological","category":"pathogen","food_matrix":"Ready-to-eat foods","jurisdiction":"eu","limit_value":"Absent","limit_unit":"per 25g","adi_tdi":None,"regulatory_basis":"EU Commission Regulation 2073/2005 — Microbiological Criteria","notes":"Food safety criterion. Unsatisfactory result requires product withdrawal and investigation."},
    {"substance":"E. coli (STEC O157)","substance_aliases":["STEC","Verocytotoxin-producing E. coli"],"cas_number":None,"ins_number":None,"limit_type":"microbiological","category":"pathogen","food_matrix":"Fresh leafy vegetables","jurisdiction":"eu","limit_value":"Absent","limit_unit":"per 25g","adi_tdi":None,"regulatory_basis":"EU Commission Regulation 2073/2005 as amended by 2019/229","notes":"Applies at production stage. Hygiene indicator E. coli (<100 CFU/g at process hygiene)."},
    {"substance":"Total Aerobic Plate Count","substance_aliases":["TPC","TAMC","Total viable count"],"cas_number":None,"ins_number":None,"limit_type":"microbiological","category":"indicator","food_matrix":"Dietary supplements / capsules","jurisdiction":"india","limit_value":"10,000 (10⁴)","limit_unit":"CFU/g","adi_tdi":None,"regulatory_basis":"IP 2022 — Microbial Limits for Preparations","notes":"For oral dietary supplements. Yeast & mould: ≤100 CFU/g. E. coli: absent/g."},
    {"substance":"Listeria monocytogenes","substance_aliases":["Listeria","L. monocytogenes"],"cas_number":None,"ins_number":None,"limit_type":"microbiological","category":"pathogen","food_matrix":"RTE foods for vulnerable populations","jurisdiction":"usa","limit_value":"Absent","limit_unit":"per 25g","adi_tdi":None,"regulatory_basis":"21 CFR — FDA zero tolerance policy for L. mono in RTE foods","notes":"USDA zero tolerance also applies to meat/poultry RTE products. High-risk for pregnant women, elderly, immunocompromised."},

    # ── PESTICIDE MRLS ────────────────────────────────────────────────────────
    {"substance":"Chlorpyrifos","substance_aliases":["Dursban","Lorsban"],"cas_number":"2921-88-2","ins_number":None,"limit_type":"pesticide","category":"organophosphate","food_matrix":"Apples (fresh)","jurisdiction":"india","limit_value":"0.5","limit_unit":"mg/kg","adi_tdi":"ADI 0.001 mg/kg bw (JECFA 2016)","regulatory_basis":"FSSAI FSS (Pesticides Residues) Regulations 2018","notes":"Chlorpyrifos use under review globally. EU banned for food use in 2020."},
    {"substance":"Chlorpyrifos","substance_aliases":["Dursban"],"cas_number":"2921-88-2","ins_number":None,"limit_type":"pesticide","category":"organophosphate","food_matrix":"All food of plant origin","jurisdiction":"eu","limit_value":"0.01","limit_unit":"mg/kg","adi_tdi":"No safe level established (EFSA 2019)","regulatory_basis":"EU Regulation 2020/1085 — default MRL (LOQ-based)","notes":"EU set to LOQ (0.01 mg/kg) as default — effectively banned for food use since October 2020."},
    {"substance":"Glyphosate","substance_aliases":["Roundup active","N-(phosphonomethyl)glycine"],"cas_number":"1071-83-6","ins_number":None,"limit_type":"pesticide","category":"herbicide","food_matrix":"Wheat (grain)","jurisdiction":"usa","limit_value":"30","limit_unit":"mg/kg","adi_tdi":"ADI 1.75 mg/kg bw/day (US EPA)","regulatory_basis":"40 CFR Part 180.364 — EPA MRL for glyphosate","notes":"Highly controversial. IARC classified as Group 2A (probable carcinogen). EPA and EFSA disagree on carcinogenicity. EU set much lower limits."},
    {"substance":"Glyphosate","substance_aliases":["Roundup active"],"cas_number":"1071-83-6","ins_number":None,"limit_type":"pesticide","category":"herbicide","food_matrix":"Wheat (grain)","jurisdiction":"eu","limit_value":"10","limit_unit":"mg/kg","adi_tdi":"ADI 0.5 mg/kg bw/day (EFSA 2015)","regulatory_basis":"EU Regulation 2023/2449 — Glyphosate MRLs","notes":"EU MRL significantly lower than US. Glyphosate authorisation in EU renewed until 2033 (Dec 2023) despite controversy."},

    # ── NUTRIENT REFERENCE VALUES ─────────────────────────────────────────────
    {"substance":"Vitamin C (Ascorbic Acid)","substance_aliases":["L-Ascorbic acid"],"cas_number":"50-81-7","ins_number":"300","limit_type":"nutrient_rv","category":"vitamin","food_matrix":"Daily intake reference (labelling)","jurisdiction":"india","limit_value":"40","limit_unit":"mg/day (RDA)","adi_tdi":None,"regulatory_basis":"ICMR 2020 RDA; FSSAI Nutrition & Health Claims Regulations 2022","notes":"FSSAI Nutrient Reference Value (NRV) for labelling: 40 mg. Upper safe level: 2000 mg/day."},
    {"substance":"Vitamin C (Ascorbic Acid)","substance_aliases":["L-Ascorbic acid"],"cas_number":"50-81-7","ins_number":"300","limit_type":"nutrient_rv","category":"vitamin","food_matrix":"Daily intake reference (labelling)","jurisdiction":"eu","limit_value":"80","limit_unit":"mg/day (NRV)","adi_tdi":None,"regulatory_basis":"EU Regulation 1169/2011 Annex XIII — Nutrient Reference Values","notes":"NRV used for % calculation on EU nutrition labels."},
    {"substance":"Vitamin C (Ascorbic Acid)","substance_aliases":["L-Ascorbic acid"],"cas_number":"50-81-7","ins_number":"300","limit_type":"nutrient_rv","category":"vitamin","food_matrix":"Daily intake reference (labelling)","jurisdiction":"usa","limit_value":"90","limit_unit":"mg/day (RDI)","adi_tdi":None,"regulatory_basis":"21 CFR 101.9 — Nutrition Labeling — Daily Values","notes":"Daily Value (DV) = 90 mg/day. Updated in 2020 FDA labeling rules."},
    {"substance":"Sodium","substance_aliases":["Sodium","Na","Salt sodium equivalent"],"cas_number":"7440-23-5","ins_number":None,"limit_type":"nutrient_rv","category":"mineral","food_matrix":"Daily intake reference (labelling)","jurisdiction":"india","limit_value":"2000","limit_unit":"mg/day (NRV)","adi_tdi":None,"regulatory_basis":"FSSAI Nutrition & Health Claims Regulations 2022 — NRV Table","notes":"NRV for sodium: 2000 mg/day (equivalent to ~5g salt). High sodium claim triggered at >600 mg/100g."},
    {"substance":"Sodium","substance_aliases":["Sodium","Na"],"cas_number":"7440-23-5","ins_number":None,"limit_type":"nutrient_rv","category":"mineral","food_matrix":"Daily intake reference (labelling)","jurisdiction":"eu","limit_value":"2000","limit_unit":"mg/day","adi_tdi":None,"regulatory_basis":"EU Regulation 1169/2011 Annex XIII","notes":"EU NRV: 2000 mg sodium/day. Reduced sodium claim: ≤120 mg/100g."},
    {"substance":"Sodium","substance_aliases":["Sodium","Na"],"cas_number":"7440-23-5","ins_number":None,"limit_type":"nutrient_rv","category":"mineral","food_matrix":"Daily intake reference (labelling)","jurisdiction":"usa","limit_value":"2300","limit_unit":"mg/day (DV)","adi_tdi":None,"regulatory_basis":"21 CFR 101.9 — 2020 Nutrition Label Rules","notes":"DV = 2300 mg/day. Low sodium: ≤140 mg/serving. Very low sodium: ≤35 mg/serving."},
]


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/allowable-limits", response_model=List[AllowableLimitOut])
async def list_limits(
    substance: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    limit_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    food_matrix: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(AllowableLimit).where(AllowableLimit.is_active == True)  # noqa

    if substance:
        stmt = stmt.where(
            or_(
                AllowableLimit.substance.ilike(f"%{substance}%"),
                func.cast(AllowableLimit.substance_aliases, String).ilike(f"%{substance}%"),
            )
        )
    if jurisdiction:
        stmt = stmt.where(AllowableLimit.jurisdiction == jurisdiction)
    if limit_type:
        stmt = stmt.where(AllowableLimit.limit_type == limit_type)
    if category:
        stmt = stmt.where(AllowableLimit.category == category)
    if food_matrix:
        stmt = stmt.where(AllowableLimit.food_matrix.ilike(f"%{food_matrix}%"))

    result = await db.execute(stmt.order_by(AllowableLimit.substance, AllowableLimit.jurisdiction).limit(limit))
    return result.scalars().all()


@router.post("/allowable-limits/seed", include_in_schema=False)
async def seed_limits(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import delete
    await db.execute(delete(AllowableLimit))
    for item in LIMITS_DATA:
        db.add(AllowableLimit(**item))
    await db.commit()
    return {"seeded": len(LIMITS_DATA)}
