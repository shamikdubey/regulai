"""
Ingredient & Material Specifications endpoint.
Covers: USP, EP, IP, BP, JP, ChP, Codex, JECFA, FSSAI Schedule, IS standards.
Each monograph: identity, assay, purity, impurities, micro limits, storage.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

from app.db.database import get_db, Base
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()


# ── Model ─────────────────────────────────────────────────────────────────────

class IngredientSpec(Base):
    __tablename__ = "ingredient_specs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    synonyms: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    cas_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    einecs: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ins_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # vitamin / mineral / botanical / additive / excipient / API
    domain: Mapped[str] = mapped_column(String(50), nullable=False)     # food / pharma / nutra / ayurveda
    pharmacopoeias: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list of {source, grade, assay, monograph_ref}
    codex_standard: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    jecfa_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fssai_schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    molecular_formula: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    molecular_weight: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    appearance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solubility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assay_limits: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)   # {USP: "98.0-101.0%", EP: "99.0-100.5%"}
    heavy_metal_limits: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    microbiological_limits: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    impurity_limits: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    storage: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at = mapped_column(nullable=True)


# ── Schema ────────────────────────────────────────────────────────────────────

class IngredientSpecOut(BaseModel):
    id: uuid.UUID
    name: str
    synonyms: Optional[list]
    cas_number: Optional[str]
    ins_number: Optional[str]
    category: str
    domain: str
    pharmacopoeias: Optional[list]
    codex_standard: Optional[str]
    jecfa_id: Optional[str]
    fssai_schedule: Optional[str]
    description: Optional[str]
    molecular_formula: Optional[str]
    molecular_weight: Optional[str]
    appearance: Optional[str]
    solubility: Optional[str]
    assay_limits: Optional[dict]
    heavy_metal_limits: Optional[dict]
    microbiological_limits: Optional[dict]
    impurity_limits: Optional[dict]
    storage: Optional[str]
    model_config = {"from_attributes": True}


# ── Seed data ─────────────────────────────────────────────────────────────────

INGREDIENT_SPECS_DATA = [
    # ── VITAMINS ─────────────────────────────────────────────────────────────
    {
        "name": "Ascorbic Acid (Vitamin C)",
        "synonyms": ["L-Ascorbic Acid", "Vitamin C", "E300", "2,3-Didehydro-L-threo-hexono-1,4-lactone"],
        "cas_number": "50-81-7", "ins_number": "300",
        "category": "vitamin", "domain": "nutra",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Ascorbic Acid>", "assay": "99.0–100.5% (dried basis)"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0253", "assay": "99.0–100.5%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022 Vol I", "assay": "99.0–100.5%"},
            {"source": "BP", "grade": "Pharmaceutical", "monograph_ref": "BP 2023", "assay": "99.0–100.5%"},
            {"source": "FCC (Food Chemicals Codex)", "grade": "Food Grade", "monograph_ref": "FCC 13th Ed.", "assay": "99.0–100.5%"},
            {"source": "JECFA", "grade": "Food Additive", "monograph_ref": "JECFA Monograph 1973, Rev 2019", "assay": "≥99.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS (Food Products Standards) Regulations 2011, Schedule", "assay": "≥99.0%"},
        ],
        "codex_standard": "CODEX STAN 193 (contaminants); used as antioxidant per GSFA",
        "jecfa_id": "JECFA 389", "fssai_schedule": "Schedule I Part III (Vitamins)",
        "description": "White or almost white, crystalline powder or colourless crystals. Freely soluble in water. Used as antioxidant, nutrient supplement, and vitamin C source.",
        "molecular_formula": "C₆H₈O₆", "molecular_weight": "176.12 g/mol",
        "appearance": "White or almost white crystalline powder or colourless crystals",
        "solubility": "Freely soluble in water; slightly soluble in ethanol (96%); practically insoluble in dichloromethane",
        "assay_limits": {
            "USP": "99.0–100.5% (dried basis, titrimetry)",
            "EP": "99.0–100.5% (dried basis)",
            "IP": "99.0–100.5%",
            "FCC": "99.0–100.5%",
            "FSSAI Food Grade": "≥99.0%"
        },
        "heavy_metal_limits": {"Lead (Pb)": "≤2 ppm (USP/EP)", "Arsenic (As)": "≤1 ppm", "Heavy metals (total)": "≤20 ppm (IP)"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "Total yeast & mould": "≤10² CFU/g", "E. coli": "Absent/g", "Salmonella spp.": "Absent/10g"},
        "impurity_limits": {"Oxalic acid": "≤0.2%", "Specific optical rotation": "+20.5° to +21.5° (aqueous)", "Loss on drying": "≤0.4%"},
        "storage": "Store in airtight containers, protected from light. At controlled room temperature (15–30°C)."
    },
    {
        "name": "Cholecalciferol (Vitamin D3)",
        "synonyms": ["Vitamin D3", "Colecalciferol", "(3β,5Z,7E)-9,10-Secocholesta-5,7,10(19)-trien-3-ol"],
        "cas_number": "67-97-0", "ins_number": None,
        "category": "vitamin", "domain": "nutra",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Cholecalciferol>", "assay": "97.0–103.0% (HPLC)"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0072", "assay": "97.0–103.0%"},
            {"source": "BP", "grade": "Pharmaceutical", "monograph_ref": "BP 2023 Vol I", "assay": "97.0–103.0%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022", "assay": "97.0–103.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS Nutraceuticals Regs 2022, Schedule II", "assay": "≥97.0%"},
        ],
        "codex_standard": "Codex Committee on Nutrition — not listed as food additive; nutrient supplement guidance applies",
        "jecfa_id": "JECFA 1002",
        "fssai_schedule": "Schedule II Part I (Fat-Soluble Vitamins — Permitted in Health Supplements)",
        "description": "White crystalline powder. Practically insoluble in water; freely soluble in ethanol and fatty oils. Sensitive to air, heat, and light.",
        "molecular_formula": "C₂₇H₄₄O", "molecular_weight": "384.64 g/mol",
        "appearance": "White crystalline powder; odourless",
        "solubility": "Practically insoluble in water; freely soluble in ethanol (96%) and in fatty oils",
        "assay_limits": {"USP/EP/BP/IP": "97.0–103.0% (HPLC, based on C₂₇H₄₄O)", "FSSAI": "≥97.0%"},
        "heavy_metal_limits": {"Lead": "≤0.1 ppm", "Cadmium": "≤0.1 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g"},
        "impurity_limits": {"Pre-vitamin D3": "≤2.0%", "Tachysterol": "≤1.0%", "Related sterols": "≤3.0%"},
        "storage": "In sealed airtight containers, protected from light, at –20°C to –10°C (pharmaceutical grade). Protect from oxidation."
    },
    {
        "name": "Thiamine Hydrochloride (Vitamin B1)",
        "synonyms": ["Thiamine HCl", "Aneurine hydrochloride", "Vitamin B1"],
        "cas_number": "67-03-8", "ins_number": None,
        "category": "vitamin", "domain": "nutra",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Thiamine Hydrochloride>", "assay": "98.0–101.0%"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0303", "assay": "99.0–101.0%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022", "assay": "98.5–101.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "Schedule I Part III", "assay": "≥98.0%"},
        ],
        "codex_standard": "Used as nutrient supplement under Codex General Standard for Food Additives (GSFA)",
        "jecfa_id": "JECFA 3194", "fssai_schedule": "Schedule I Part III (Water-Soluble Vitamins)",
        "description": "White or almost white crystalline powder with slight yeast-like odour. Very soluble in water. Used as vitamin B1 source.",
        "molecular_formula": "C₁₂H₁₇ClN₄OS·HCl", "molecular_weight": "337.27 g/mol",
        "appearance": "White or almost white crystalline powder",
        "solubility": "Very soluble in water; slightly soluble in ethanol (96%); practically insoluble in acetone",
        "assay_limits": {"USP": "98.0–101.0%", "EP": "99.0–101.0%", "IP": "98.5–101.0%"},
        "heavy_metal_limits": {"Heavy metals (total)": "≤20 ppm", "Lead": "≤2 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g"},
        "impurity_limits": {"Loss on drying": "≤5.0%", "Sulphated ash": "≤0.2%", "Nitrates": "≤200 ppm"},
        "storage": "Store in airtight containers, protected from light and moisture."
    },

    # ── MINERALS ──────────────────────────────────────────────────────────────
    {
        "name": "Zinc Gluconate",
        "synonyms": ["Zinc D-gluconate", "Zinc(2+) gluconate"],
        "cas_number": "4468-02-4", "ins_number": None,
        "category": "mineral", "domain": "nutra",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Zinc Gluconate>", "assay": "97.0–102.0%"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 1210", "assay": "98.0–102.0%"},
            {"source": "FCC", "grade": "Food Grade", "monograph_ref": "FCC 13th Ed.", "assay": "97.0–102.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS Regulations 2011 — Mineral List", "assay": "≥97.0%"},
        ],
        "codex_standard": "Codex GSFA — permitted as nutrient supplement",
        "jecfa_id": "JECFA 959", "fssai_schedule": "Schedule I Part IV (Minerals)",
        "description": "White or almost white granular or crystalline powder. Freely soluble in water. Used as zinc supplement.",
        "molecular_formula": "C₁₂H₂₂O₁₄Zn", "molecular_weight": "455.7 g/mol",
        "appearance": "White or almost white powder or granules",
        "solubility": "Freely soluble in water; practically insoluble in ethanol (96%)",
        "assay_limits": {"USP/EP": "97.0–102.0% (calculated as Zn)", "FSSAI": "Zinc content ≥14.35%"},
        "heavy_metal_limits": {"Lead": "≤2 ppm", "Cadmium": "≤1 ppm", "Arsenic": "≤1 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g", "Salmonella": "Absent/10g"},
        "impurity_limits": {"Reducing sugars": "No further reducing sugars", "Chlorides": "≤200 ppm", "Sulphates": "≤500 ppm"},
        "storage": "Store in well-closed containers, protected from moisture."
    },
    {
        "name": "Ferrous Sulphate",
        "synonyms": ["Iron(II) sulphate", "Ferrous sulfate", "Iron vitriol", "FeSO₄·7H₂O"],
        "cas_number": "7782-63-0", "ins_number": "520",
        "category": "mineral", "domain": "pharma",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Ferrous Sulfate>", "assay": "99.5–104.5% (Fe)"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0083", "assay": "98.0–105.0%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022", "assay": "99.0–104.0%"},
            {"source": "IS", "grade": "Industrial/Food", "monograph_ref": "IS 266 (Food Grade Ferrous Sulphate)", "assay": "≥98.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS Regulations 2011 — Fortification", "assay": "≥98.0%"},
        ],
        "codex_standard": "Used for food fortification per CODEX GL 09-1987 (General Principles for the Addition of Essential Nutrients to Foods)",
        "jecfa_id": "JECFA 344", "fssai_schedule": "Schedule I Part IV (Iron Salts — Fortification)",
        "description": "Pale blue-green crystalline solid. Efflorescent in dry air. Soluble in water. Primary iron supplement and fortification agent.",
        "molecular_formula": "FeSO₄·7H₂O", "molecular_weight": "278.01 g/mol",
        "appearance": "Pale bluish-green crystals or crystalline powder; efflorescent",
        "solubility": "Freely soluble in water; practically insoluble in ethanol",
        "assay_limits": {"USP": "99.5–104.5% FeSO₄·7H₂O", "EP": "98.0–105.0%", "IP": "99.0–104.0%", "IS 266": "≥98.0%"},
        "heavy_metal_limits": {"Lead": "≤5 ppm", "Arsenic": "≤2 ppm", "Ferric iron (Fe³⁺)": "≤2.0%"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g"},
        "impurity_limits": {"Sulphate (excess)": "Complies", "Loss on drying": "24.0–26.0% (heptahydrate)"},
        "storage": "In airtight containers, protected from light and oxidation. Cool dry place."
    },
    {
        "name": "Magnesium Stearate",
        "synonyms": ["Magnesium octadecanoate", "Stearic acid magnesium salt"],
        "cas_number": "557-04-0", "ins_number": "470(iii)",
        "category": "excipient", "domain": "pharma",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Magnesium Stearate>", "assay": "Mg 4.0–5.0%"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0229", "assay": "Mg 4.0–5.0%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022", "assay": "Mg 4.0–5.0%"},
            {"source": "NF (National Formulary)", "grade": "Pharmaceutical", "monograph_ref": "NF 42", "assay": "Mg 4.0–5.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS (FPS) Regulations — Emulsifiers & Stabilisers List", "assay": "Mg ≥4.0%"},
        ],
        "codex_standard": "CODEX STAN 192 GSFA — INS 470(iii) permitted as emulsifier/stabiliser/flour treatment",
        "jecfa_id": "JECFA 476 (Magnesium salts of fatty acids)", "fssai_schedule": "Schedule II Part IV (Emulsifying & Stabilising Agents)",
        "description": "Light white powder. Slightly unctuous. Practically insoluble in water and organic solvents. Used as lubricant in tablet/capsule manufacture.",
        "molecular_formula": "C₃₆H₇₀MgO₄", "molecular_weight": "591.27 g/mol",
        "appearance": "Light white powder; slightly unctuous feel",
        "solubility": "Practically insoluble in water, ethanol, and ether",
        "assay_limits": {"USP/EP/IP": "Magnesium (Mg): 4.0–5.0% (w/w)", "NF": "4.0–5.0%"},
        "heavy_metal_limits": {"Heavy metals (total)": "≤20 ppm", "Lead": "≤2 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g"},
        "impurity_limits": {"Loss on drying": "≤6.0%", "Free acid (as stearic acid)": "≤3.0%", "Chlorides": "≤200 ppm"},
        "storage": "Store in well-closed containers, dry conditions."
    },

    # ── FOOD ADDITIVES ────────────────────────────────────────────────────────
    {
        "name": "Sodium Benzoate",
        "synonyms": ["Benzoic acid, sodium salt", "Sobenate", "E211"],
        "cas_number": "532-32-1", "ins_number": "211",
        "category": "food additive", "domain": "food",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical/Food", "monograph_ref": "USP-NF <Sodium Benzoate>", "assay": "99.0–100.5%"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0123", "assay": "99.0–100.5%"},
            {"source": "FCC", "grade": "Food Grade", "monograph_ref": "FCC 13th Ed.", "assay": "99.0–100.5%"},
            {"source": "JECFA", "grade": "Food Additive", "monograph_ref": "JECFA Monograph 1974, Rev 2016", "assay": "≥99.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS (FPS) Regulations — Preservatives List", "assay": "≥99.0%"},
            {"source": "IS", "grade": "Food Grade", "monograph_ref": "IS 1786 (Sodium Benzoate — Food Grade)", "assay": "≥99.0%"},
        ],
        "codex_standard": "CODEX STAN 192 GSFA INS 211 — Benzoates (Benzoic acid, Sodium benzoate): ADI 0–5 mg/kg bw",
        "jecfa_id": "JECFA 217", "fssai_schedule": "Schedule II Part A (Permitted Preservatives)",
        "description": "White granular or crystalline powder. Freely soluble in water. Used as antimicrobial preservative in food and pharmaceutical products.",
        "molecular_formula": "C₇H₅NaO₂", "molecular_weight": "144.10 g/mol",
        "appearance": "White granular or crystalline powder; odourless or with faint characteristic odour",
        "solubility": "Freely soluble in water (1 g in 2 mL); sparingly soluble in ethanol (96%)",
        "assay_limits": {"USP/EP": "99.0–100.5% (dried basis)", "FCC/JECFA/FSSAI/IS": "≥99.0%"},
        "heavy_metal_limits": {"Lead": "≤2 ppm", "Arsenic": "≤1 ppm", "Heavy metals (total)": "≤10 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g"},
        "impurity_limits": {"Loss on drying": "≤1.5%", "Chlorinated compounds": "≤300 ppm (as Cl)", "Polycyclic aromatic hydrocarbons": "Complies"},
        "storage": "Store in well-closed containers, away from strong oxidising agents."
    },
    {
        "name": "Titanium Dioxide",
        "synonyms": ["TiO₂", "Titania", "E171", "CI 77891"],
        "cas_number": "13463-67-7", "ins_number": "171",
        "category": "food additive", "domain": "food",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Titanium Dioxide>", "assay": "99.0–100.5% TiO₂"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0150", "assay": "98.0–100.5%"},
            {"source": "FCC", "grade": "Food Grade", "monograph_ref": "FCC 13th Ed.", "assay": "99.0% min"},
            {"source": "JECFA", "grade": "Food Additive", "monograph_ref": "JECFA 1969, Rev 2021", "assay": "≥99.0%"},
            {"source": "FSSAI", "grade": "Food Grade", "monograph_ref": "FSS Regulations — Colours List (White)", "assay": "≥99.0%"},
        ],
        "codex_standard": "Codex GSFA INS 171; ADI 'not specified' (JECFA) — NOTE: EU banned E171 in food from August 2022; still permitted in other jurisdictions",
        "jecfa_id": "JECFA 176", "fssai_schedule": "Schedule II Part B (Permitted Colours) — permitted as white colour in India",
        "description": "White amorphous or crystalline powder. Practically insoluble in water and most organic solvents. IMPORTANT: Banned as food additive in EU since August 2022 due to genotoxicity concerns. Still permitted in USA, India, Japan, and other markets.",
        "molecular_formula": "TiO₂", "molecular_weight": "79.87 g/mol",
        "appearance": "White amorphous powder or crystals",
        "solubility": "Practically insoluble in water, dilute acids, and organic solvents; soluble in concentrated sulphuric acid",
        "assay_limits": {"USP/EP": "98.0–100.5%", "FCC/FSSAI": "≥99.0%"},
        "heavy_metal_limits": {"Lead": "≤10 ppm", "Arsenic": "≤1 ppm", "Antimony": "≤1 ppm", "Mercury": "≤1 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g"},
        "impurity_limits": {"Water-soluble substances": "≤0.5%", "Matter soluble in 0.5M H₂SO₄": "≤0.5%"},
        "storage": "Store in well-closed containers."
    },

    # ── BOTANICALS / AYURVEDIC ────────────────────────────────────────────────
    {
        "name": "Withania somnifera Dry Extract (Ashwagandha)",
        "synonyms": ["Ashwagandha extract", "Indian ginseng extract", "Winter cherry extract"],
        "cas_number": "90147-43-6", "ins_number": None,
        "category": "botanical", "domain": "ayurveda",
        "pharmacopoeias": [
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022 — Withania somnifera Root Powder", "assay": "Withanolides ≥5.0% (HPLC)"},
            {"source": "USP", "grade": "Dietary Supplement", "monograph_ref": "USP-NF <Ashwagandha Root>", "assay": "Withanolides ≥1.5% (USP Reference Standard)"},
            {"source": "AYUSH", "grade": "Classical", "monograph_ref": "AYUSH Pharmacopoeia Vol I — Asvagandha", "assay": "Total alkaloids ≥0.3%"},
            {"source": "WHO", "grade": "Herbal Medicine", "monograph_ref": "WHO Monographs on Selected Medicinal Plants Vol 2", "assay": "Withanolides — as per validated method"},
            {"source": "FSSAI", "grade": "Functional Food/Nutra", "monograph_ref": "FSS Nutraceuticals Regs 2022 — Ashwagandha entry", "assay": "Total withanolides ≥1.5% (as per FSSAI approved method)"},
        ],
        "codex_standard": "Not listed in GSFA. Subject to national botanical supplement regulations.",
        "jecfa_id": None, "fssai_schedule": "FSS Nutraceuticals Regulations 2022 — Permitted Botanical Ingredients List",
        "description": "Dried root extract standardised to withanolide content. An adaptogen used in Ayurvedic medicine. Multiple grades exist: 1.5%, 2.5%, 5%, 10% withanolides.",
        "molecular_formula": "Complex mixture — marker: Withaferin A (C₂₈H₃₈O₆, MW: 470.6)", "molecular_weight": "Variable (extract)",
        "appearance": "Light brown to brownish-yellow fine powder with characteristic odour",
        "solubility": "Partially soluble in water; more soluble in ethanol and methanol",
        "assay_limits": {
            "IP 2022": "Total withanolides ≥5.0% (w/w) for concentrated extract",
            "USP": "Total withanolides ≥1.5% (w/w)",
            "FSSAI": "Total withanolides ≥1.5% (w/w)",
            "Standard grade": "1.5% — 10% depending on specification"
        },
        "heavy_metal_limits": {"Lead (Pb)": "≤5.0 ppm (IP/USP)", "Arsenic (As)": "≤1.0 ppm", "Cadmium (Cd)": "≤0.3 ppm", "Mercury (Hg)": "≤0.1 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10⁵ CFU/g", "Total yeast & mould": "≤10³ CFU/g", "E. coli": "Absent/g", "Salmonella": "Absent/10g", "Staphylococcus aureus": "Absent/g"},
        "impurity_limits": {"Pesticide residues": "Per IP/USP multiresidue method", "Aflatoxins (B1+B2+G1+G2)": "≤4 ppb", "Loss on drying": "≤10.0%", "Acid-insoluble ash": "≤2.0%"},
        "storage": "Store in airtight containers, protected from light and moisture, below 25°C."
    },

    # ── APIs ──────────────────────────────────────────────────────────────────
    {
        "name": "Metformin Hydrochloride",
        "synonyms": ["Metformin HCl", "1,1-Dimethylbiguanide hydrochloride"],
        "cas_number": "1115-70-4", "ins_number": None,
        "category": "API", "domain": "pharma",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Metformin Hydrochloride>", "assay": "99.0–101.0%"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0931", "assay": "99.0–101.0%"},
            {"source": "BP", "grade": "Pharmaceutical", "monograph_ref": "BP 2023", "assay": "99.0–101.0%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022 Vol I", "assay": "99.0–101.0%"},
            {"source": "ChP (Chinese Pharmacopoeia)", "grade": "Pharmaceutical", "monograph_ref": "ChP 2020 Vol II", "assay": "98.5–101.0%"},
            {"source": "JP (Japanese Pharmacopoeia)", "grade": "Pharmaceutical", "monograph_ref": "JP XVIII", "assay": "99.0–101.0%"},
        ],
        "codex_standard": "Not applicable (pharmaceutical API)",
        "jecfa_id": None, "fssai_schedule": "Not applicable — regulated under D&C Act / CDSCO",
        "description": "White crystalline powder. Freely soluble in water. Oral antidiabetic agent (biguanide class). Not hygroscopic.",
        "molecular_formula": "C₄H₁₁N₅·HCl", "molecular_weight": "165.62 g/mol",
        "appearance": "White or almost white crystalline powder; slightly hygroscopic",
        "solubility": "Freely soluble in water; practically insoluble in acetone, ether, and dichloromethane",
        "assay_limits": {"USP/EP/BP/IP": "99.0–101.0% (dried basis, titrimetry)", "ChP": "98.5–101.0%", "JP": "99.0–101.0%"},
        "heavy_metal_limits": {"Lead": "≤0.5 ppm", "Total heavy metals": "≤20 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g"},
        "impurity_limits": {
            "Melamine": "≤2 ppm (ICH Q3A)",
            "Dicyandiamide": "≤100 ppm",
            "Loss on drying": "≤0.5%",
            "Residue on ignition": "≤0.1%",
            "Chlorides": "≤200 ppm",
            "Related impurities (any individual)": "≤0.1% (ICH Q3A)"
        },
        "storage": "Store in well-closed containers at controlled room temperature. Protect from moisture."
    },
    {
        "name": "Ibuprofen",
        "synonyms": ["(RS)-2-(4-(2-methylpropyl)phenyl)propanoic acid", "Brufen", "Advil active ingredient"],
        "cas_number": "15687-27-1", "ins_number": None,
        "category": "API", "domain": "pharma",
        "pharmacopoeias": [
            {"source": "USP", "grade": "Pharmaceutical", "monograph_ref": "USP-NF <Ibuprofen>", "assay": "97.0–103.0%"},
            {"source": "EP", "grade": "Pharmaceutical", "monograph_ref": "Ph. Eur. 0721", "assay": "98.5–101.5%"},
            {"source": "BP", "grade": "Pharmaceutical", "monograph_ref": "BP 2023", "assay": "98.5–101.5%"},
            {"source": "IP", "grade": "Pharmaceutical", "monograph_ref": "IP 2022", "assay": "97.0–103.0%"},
            {"source": "JP", "grade": "Pharmaceutical", "monograph_ref": "JP XVIII", "assay": "98.0–102.0%"},
        ],
        "codex_standard": "Not applicable",
        "jecfa_id": None, "fssai_schedule": "Not applicable — Schedule H drug under D&C Act",
        "description": "White crystalline powder with slight characteristic odour. Practically insoluble in water; very soluble in acetone, dichloromethane and ethanol. NSAID.",
        "molecular_formula": "C₁₃H₁₈O₂", "molecular_weight": "206.28 g/mol",
        "appearance": "White or almost white crystalline powder; slight characteristic odour",
        "solubility": "Practically insoluble in water; freely soluble in acetone; very soluble in DCM and EtOH",
        "assay_limits": {"USP": "97.0–103.0%", "EP/BP": "98.5–101.5%", "IP": "97.0–103.0%", "JP": "98.0–102.0%"},
        "heavy_metal_limits": {"Lead": "≤0.5 ppm", "Total heavy metals": "≤20 ppm"},
        "microbiological_limits": {"Total aerobic microbial count": "≤10³ CFU/g", "E. coli": "Absent/g"},
        "impurity_limits": {"4-Isobutylacetophenone": "≤10 ppm", "Related substances (total)": "≤0.3%", "Residue on ignition": "≤0.1%", "Loss on drying": "≤0.5%"},
        "storage": "Store below 30°C in well-closed containers."
    },
]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/ingredient-specs", response_model=List[IngredientSpecOut])
async def list_ingredient_specs(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    pharmacopoeia: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(IngredientSpec).where(IngredientSpec.is_active == True)  # noqa

    if search:
        stmt = stmt.where(
            or_(
                IngredientSpec.name.ilike(f"%{search}%"),
                IngredientSpec.cas_number.ilike(f"%{search}%"),
                IngredientSpec.ins_number.ilike(f"%{search}%"),
                func.cast(IngredientSpec.synonyms, String).ilike(f"%{search}%"),
            )
        )
    if category:
        stmt = stmt.where(IngredientSpec.category == category)
    if domain:
        stmt = stmt.where(IngredientSpec.domain == domain)

    result = await db.execute(stmt.order_by(IngredientSpec.name).limit(limit))
    return result.scalars().all()


@router.get("/ingredient-specs/{spec_id}", response_model=IngredientSpecOut)
async def get_ingredient_spec(
    spec_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(IngredientSpec).where(IngredientSpec.id == uuid.UUID(spec_id))
    )
    spec = result.scalar_one_or_none()
    if not spec:
        raise HTTPException(404, "Ingredient specification not found")
    return spec


@router.post("/ingredient-specs/seed", include_in_schema=False)
async def seed_ingredient_specs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import delete
    await db.execute(delete(IngredientSpec))
    for item in INGREDIENT_SPECS_DATA:
        db.add(IngredientSpec(**item))
    await db.commit()
    return {"seeded": len(INGREDIENT_SPECS_DATA)}
