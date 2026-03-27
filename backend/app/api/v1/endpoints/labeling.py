"""
Labeling Requirements endpoint.
Per product type + jurisdiction: mandatory fields, nutrition declaration format,
allergen rules, weights & measures, language requirements, prohibited claims.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import datetime

from app.db.database import get_db, Base
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()


class LabelingRequirement(Base):
    __tablename__ = "labeling_requirements"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    regulatory_basis: Mapped[str] = mapped_column(String(255), nullable=False)
    competent_authority: Mapped[str] = mapped_column(String(100), nullable=False)
    mandatory_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    nutrition_declaration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    allergen_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    weights_measures: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    language_requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    prohibited_claims: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    claim_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    special_requirements: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    enforcement_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, server_default=func.now())


class LabelingRequirementOut(BaseModel):
    id: uuid.UUID
    jurisdiction: str
    product_type: str
    regulatory_basis: str
    competent_authority: str
    mandatory_fields: list
    nutrition_declaration: Optional[dict]
    allergen_rules: Optional[dict]
    weights_measures: Optional[dict]
    language_requirements: Optional[dict]
    prohibited_claims: Optional[list]
    claim_rules: Optional[dict]
    special_requirements: Optional[list]
    enforcement_notes: Optional[str]
    model_config = {"from_attributes": True}


LABELING_DATA = [
    # ── INDIA — PACKAGED FOOD ─────────────────────────────────────────────────
    {
        "jurisdiction": "india",
        "product_type": "packaged_food",
        "regulatory_basis": "FSS (Labelling and Display) Regulations 2020; FSS Nutrition & Health Claims Regs 2022",
        "competent_authority": "FSSAI",
        "mandatory_fields": [
            "Name of food / product name",
            "List of ingredients (descending order by weight)",
            "Nutritional information per 100g or 100mL AND per serving",
            "Declaration of allergens (in bold, contrasting colour)",
            "Net quantity (weight or volume)",
            "Date of manufacture / packaging",
            "Best before / Use by date",
            "Name and address of manufacturer / packer / importer",
            "Country of origin (if imported)",
            "FSSAI licence number of manufacturer",
            "Batch / lot number",
            "Customer care details (name, address, phone/email)",
            "Vegetarian (green dot) or Non-vegetarian (brown/red dot) symbol",
            "Organic mark (if claimed) — 'India Organic' logo with FSSAI licence",
        ],
        "nutrition_declaration": {
            "mandatory_nutrients": ["Energy (kcal)", "Total Fat (g)", "Saturated Fat (g)", "Trans Fat (g)", "Total Carbohydrate (g)", "Total Sugars (g)", "Protein (g)", "Sodium (mg)"],
            "per_serving_required": True,
            "per_100g_required": True,
            "format": "Tabular format mandatory. RDA% based on FSSAI NRVs. Trans fat 0g if <0.2g/serving.",
            "nrv_reference": "ICMR 2020 RDA values; FSSAI NRV Table (Schedule I, Nutrition & Health Claims Regs 2022)",
            "serving_size_rule": "Manufacturer may define serving size but must be realistic. FSSAI may prescribe standardised serving sizes.",
            "added_sugar_required": False,
            "fibre_mandatory": False,
        },
        "allergen_rules": {
            "top_allergens": ["Cereals containing gluten (wheat, rye, barley, oats)", "Crustaceans", "Eggs", "Fish", "Peanuts", "Soybeans", "Milk and dairy", "Tree nuts", "Celery", "Mustard", "Sesame seeds", "Sulphur dioxide and sulphites (>10 mg/kg)"],
            "declaration_method": "Declare in ingredient list with emphasis (bold, underline, or contrasting colour) AND in 'Contains' statement",
            "regulatory_basis": "FSS (Labelling) Regulations 2020 — Regulation 6",
            "cross_contact_required": False,
        },
        "weights_measures": {
            "net_weight_position": "Principal display panel (PDP)",
            "net_weight_font_size": "Minimum 2mm for packages <50g/mL; 3mm for 50–200g/mL; 4mm for 200g–1kg/L; 6mm above 1kg/L",
            "weight_units": "SI units mandatory (g, kg, mL, L). If using non-SI in addition, SI must be prominent.",
            "pre-packaged_definition": "Product pre-packed before sale, not to be opened in the presence of buyer",
            "regulatory_basis": "Legal Metrology (Packaged Commodities) Rules 2011; FSSAI Labelling Regs 2020",
            "pack_sizes": "For cereals, pulses, spices: pack sizes must conform to Legal Metrology specified sizes",
            "mrp_required": "Maximum Retail Price (MRP) inclusive of all taxes must appear on label",
        },
        "language_requirements": {
            "mandatory_language": "Hindi (Devanagari) and English both mandatory on PDP",
            "additional_languages": "State/regional languages may be added but Hindi and English are primary",
            "font_minimum": "1.5mm minimum for readable text; 2mm for mandatory declarations",
            "script_rule": "Hindi declarations must be in Devanagari script; no transliteration",
        },
        "prohibited_claims": [
            "Disease treatment or cure claims (e.g. 'cures diabetes', 'prevents cancer')",
            "Claims implying product can substitute a varied diet",
            "Medicinal or therapeutic claims on food products",
            "Misleading comparisons with other products",
            "Implied endorsement by government bodies",
            "'Recommended by nutritionists' without substantiation per FSSAI guidelines",
        ],
        "claim_rules": {
            "low_fat": "≤3g fat per 100g solid or ≤1.5g per 100mL liquid",
            "fat_free": "<0.5g fat per 100g/100mL",
            "low_sugar": "≤5g total sugars per 100g solid or ≤2.5g per 100mL liquid",
            "sugar_free": "<0.5g total sugars per 100g/100mL",
            "low_sodium": "≤120mg sodium per 100g solid",
            "source_of_vitamin": "≥15% NRV per 100g/100mL (or per serving if stated)",
            "high_in_vitamin": "≥30% NRV per 100g/100mL (or per serving)",
            "high_fibre": "≥6g dietary fibre per 100g",
            "whole_grain_claim": "No formal FSSAI definition — follow FSSAI guidance 2022",
        },
        "special_requirements": [
            "Red colour coding warning for 'High in Fat', 'High in Sugar', 'High in Sodium' — mandatory per FSSAI 2022 amendment (front-of-pack label)",
            "FSSAI logo with licence number must appear on label",
            "Vegetarian/Non-vegetarian symbol mandatory — 6mm diameter circle with dot; green = veg, brown/red = non-veg",
            "Jain food symbol if claimed — additional symbol required",
            "Halal/Kosher claims need third-party certification mark",
            "Organic claims require 'India Organic' certification and logo",
            "Best before date format: DD/MM/YYYY or MM/YYYY",
        ],
        "enforcement_notes": "FSSAI enforces through Food Safety Officers (FSOs) and Central Food Laboratory (CFL) testing. Non-compliant labels attract penalties under FSS Act Section 52 (up to ₹3 lakhs for first offence)."
    },

    # ── INDIA — HEALTH SUPPLEMENT / NUTRACEUTICAL ─────────────────────────────
    {
        "jurisdiction": "india",
        "product_type": "nutraceutical",
        "regulatory_basis": "FSS (Health Supplements, Nutraceuticals…) Regulations 2022",
        "competent_authority": "FSSAI",
        "mandatory_fields": [
            "Product name including the word 'Health Supplement' or appropriate category",
            "List of all ingredients including active and non-active (excipients)",
            "Quantity of each active ingredient per serving",
            "Recommended serving size and directions for use",
            "Recommended daily intake / maximum daily dose",
            "Warning: 'This product is not intended to diagnose, treat, cure or prevent any disease'",
            "Warning: 'Not a substitute for a varied balanced diet'",
            "Warning: 'Consult your physician before use' (if applicable)",
            "Target population (if specific: children, elderly, pregnant women) — contraindications",
            "Net quantity",
            "Manufacture date and best before date",
            "Manufacturer name, address, and FSSAI licence number",
            "Batch number",
            "Country of origin",
            "MRP inclusive of taxes",
            "Vegetarian/Non-vegetarian symbol",
            "Storage conditions",
        ],
        "nutrition_declaration": {
            "mandatory_nutrients": ["Energy (kcal)", "Total Fat (g)", "Saturated Fat (g)", "Trans Fat (g)", "Total Carbohydrate (g)", "Total Sugars (g)", "Protein (g)", "Sodium (mg)", "All declared active nutrients with quantities"],
            "per_serving_required": True,
            "per_100g_required": True,
            "format": "Supplement facts table mandatory. Must show % NRV for each nutrient.",
            "nrv_reference": "FSS Nutraceuticals Regulations 2022 Schedule NRV Table",
            "upper_safe_level": "Nutrient quantities must not exceed Upper Tolerable Intake Levels (ULs) in Schedule",
            "botanical_declaration": "Botanical ingredients: declare plant species (Latin name), plant part used, and extraction ratio",
        },
        "allergen_rules": {
            "top_allergens": ["Same 12 allergens as packaged food regulations"],
            "declaration_method": "Bold in ingredient list plus separate 'Contains' statement",
            "gluten_free_claim": "If gluten-free claim made: <20 ppm gluten (test required)",
        },
        "weights_measures": {
            "net_quantity": "Express as number of tablets/capsules/sachets AND total weight",
            "serving_size": "Clearly state 'Per tablet', 'Per 2 capsules', etc.",
            "regulatory_basis": "Legal Metrology Rules 2011 apply",
        },
        "language_requirements": {
            "mandatory_language": "Hindi and English (both on principal display panel)",
            "warning_language": "All mandatory warnings must be in Hindi AND English",
        },
        "prohibited_claims": [
            "Disease claims ('treats', 'cures', 'prevents', 'manages' any disease)",
            "Drug-type pharmacological claims without CDSCO approval",
            "Exaggerated or unsubstantiated efficacy claims",
            "Claims implying product can replace prescribed medication",
            "'Doctor recommended' without specific named endorsement with documentation",
            "Claims of superiority over other listed/approved products",
        ],
        "claim_rules": {
            "structure_function_claims": "Permitted if scientifically substantiated. E.g., 'Supports immune function', 'Contributes to normal energy metabolism'",
            "nutrient_content_claims": "Per FSSAI Nutrition & Health Claims Regulations 2022",
            "botanical_claims": "Traditional use claims permitted if from recognized traditional systems (Ayurveda, Unani, Siddha) — cite classical text",
            "substantiation_required": "All claims require scientific substantiation to be available to FSSAI on request",
        },
        "special_requirements": [
            "Warning in red box: 'Not recommended for persons below 18 years of age' if applicable",
            "Pregnancy/lactation warning if relevant to product",
            "Allergen declaration prominent and in bold",
            "For protein supplements: amino acid profile declaration recommended",
            "For probiotic products: declare CFU count at end of shelf life (not manufacture)",
        ],
        "enforcement_notes": "FSSAI Nutraceuticals Regs 2022 fully enforced from 2024. Non-compliant products face recall and licence suspension. The FSSAI/CDSCO grey zone: products with disease claims or therapeutic doses are regulated as drugs under D&C Act."
    },

    # ── USA — PACKAGED FOOD ───────────────────────────────────────────────────
    {
        "jurisdiction": "usa",
        "product_type": "packaged_food",
        "regulatory_basis": "21 CFR Part 101 — Food Labeling; FSMA 2011; Nutrition Labeling and Education Act 1990",
        "competent_authority": "FDA (CFSAN)",
        "mandatory_fields": [
            "Statement of identity (product name)",
            "Net quantity of contents (bottom 30% of PDP)",
            "Nutrition Facts Panel (NFP) — updated 2020 format",
            "Ingredients list (descending order by weight)",
            "Allergen declaration (FALCPA + FASTER Act 2021)",
            "Name and place of business of manufacturer/packer/distributor",
            "Country of origin (for meat/poultry: USDA; for produce: PACA)",
            "Required on outer package if shipped in interstate commerce",
        ],
        "nutrition_declaration": {
            "mandatory_nutrients": ["Calories", "Total Fat (g)", "Saturated Fat (g)", "Trans Fat (g)", "Cholesterol (mg)", "Sodium (mg)", "Total Carbohydrate (g)", "Dietary Fiber (g)", "Total Sugars (g)", "Added Sugars (g)", "Protein (g)", "Vitamin D (mcg)", "Calcium (mg)", "Iron (mg)", "Potassium (mg)"],
            "per_serving_required": True,
            "per_100g_required": False,
            "format": "FDA 2020 Nutrition Facts Label. Calories in larger/bolder font. Added sugars mandatory since 2020. % Daily Value (%DV) based on 2000 cal/day reference.",
            "nrv_reference": "FDA Reference Daily Intakes (RDIs) and Daily Reference Values (DRVs) per 21 CFR 101.9",
            "serving_size_rule": "RACC (Reference Amount Customarily Consumed) mandatory as defined in 21 CFR 101.12",
            "added_sugar_required": True,
            "fibre_mandatory": True,
            "dual_column_required": "If package contains 2–3 servings and is typically consumed in one sitting: dual column required",
        },
        "allergen_rules": {
            "top_allergens": ["Milk", "Eggs", "Fish (with specific name, e.g., salmon)", "Shellfish (with specific name)", "Tree nuts (with specific name)", "Wheat", "Peanuts", "Soybeans", "Sesame (added by FASTER Act 2023)"],
            "declaration_method": "Must appear in ingredient list in plain language AND/OR in 'Contains: X, Y, Z' statement after ingredient list",
            "regulatory_basis": "FALCPA (Food Allergen Labeling and Consumer Protection Act 2004) + FASTER Act 2021 (sesame added)",
            "cross_contact_statement": "'May contain' or 'Produced in a facility...' statements are voluntary — not FDA-mandated",
        },
        "weights_measures": {
            "net_weight_position": "Lower 30% of principal display panel",
            "weight_units": "Both US customary (oz, fl oz, lb) AND metric (g, mL, kg) required",
            "regulatory_basis": "15 U.S.C. 1453; 21 CFR 101.7",
            "font_size_minimum": "Minimum 1/16 inch (1.6mm) for smallest packages",
            "area_based_size": "1/16 inch (packages <5 sq in PDP); 1/8 inch (5–25 sq in); 3/16 inch (25–100 sq in); 1/4 inch (>100 sq in)",
        },
        "language_requirements": {
            "mandatory_language": "English mandatory on all required label statements",
            "bilingual_allowed": "Spanish or other languages may be added but English must be equally prominent",
            "unicode_font": "Must be legible and conspicuous",
        },
        "prohibited_claims": [
            "Disease claims without FDA-approved health claim petition",
            "Claims implying product cures or treats a disease (drug claim — triggers pharmaceutical regulation)",
            "Misleading nutrient content claims",
            "'Zero trans fat' if saturated fat >1g/serving (misleading)",
            "Unauthorized structure/function claims without notification to FDA",
        ],
        "claim_rules": {
            "low_fat": "<3g fat per RACC and per 50g if RACC is ≤30g or ≤2 tbsp",
            "fat_free": "<0.5g fat per RACC and per 50g",
            "low_sodium": "≤140mg sodium per RACC",
            "low_calorie": "≤40 kcal per RACC and per 50g",
            "good_source_fibre": "2.5–4.9g per RACC (10–19% DV)",
            "excellent_source_fibre": "≥5g per RACC (≥20% DV)",
            "organic_usda": "USDA Organic certified: 95%+ organic ingredients; NOP-compliant",
            "natural_claim": "No formal FDA definition; FDA exercises enforcement discretion",
            "gluten_free": "< 20 ppm gluten per 21 CFR 101.91",
            "heart_healthy": "Authorized health claim — must meet specific total fat, saturated fat, cholesterol, and sodium criteria",
        },
        "special_requirements": [
            "Country of origin labeling (COOL) required for fish, shellfish, perishable agricultural commodities under USDA PACA",
            "Bioengineered (BE) food disclosure mandatory since January 2022 (USDA National Bioengineered Food Disclosure Standard)",
            "Juice products: percent juice declaration mandatory for beverages containing juice",
            "Sulfite declaration mandatory if ≥10 ppm total SO₂",
            "FD&C Yellow No. 5 (Tartrazine): must be declared by name in ingredient list",
            "Imitation foods: must be labelled 'imitation' unless nutritionally equivalent",
        ],
        "enforcement_notes": "FDA issues Warning Letters for labeling violations; serious violations (mislabeling causing health risk) can trigger Class I recall. FTC jurisdiction covers advertising claims (separate from label)."
    },

    # ── EU — PACKAGED FOOD ────────────────────────────────────────────────────
    {
        "jurisdiction": "eu",
        "product_type": "packaged_food",
        "regulatory_basis": "EU Regulation 1169/2011 (FIC) — Food Information to Consumers",
        "competent_authority": "EC DG SANTE + National Competent Authorities",
        "mandatory_fields": [
            "Name of food",
            "List of ingredients (with quantities for key ingredients — QUID)",
            "Any substance or product causing allergies or intolerances",
            "Quantity of certain ingredients or categories of ingredients (QUID)",
            "Net quantity",
            "Date of minimum durability ('Best before') or use-by date",
            "Storage conditions and/or conditions of use (where applicable)",
            "Name or business name and address of FBO",
            "Country of origin or place of provenance (for specific categories)",
            "Instructions for use (where appropriate)",
            "Alcoholic strength (for beverages >1.2% ABV)",
            "Nutrition declaration (mandatory for most prepacked foods since 2016)",
        ],
        "nutrition_declaration": {
            "mandatory_nutrients": ["Energy (kJ and kcal)", "Fat (g)", "Saturated fatty acids (g)", "Carbohydrate (g)", "Sugars (g)", "Protein (g)", "Salt (g) — NOT sodium"],
            "per_100g_required": True,
            "per_serving_required": False,
            "format": "Per 100g or 100mL mandatory. Per serving/portion may be added voluntarily. Salt = sodium × 2.5. Energy must be in both kJ and kcal. Minimum 3pt font (5mm²) for info box.",
            "nrv_reference": "EU Regulation 1169/2011 Annex XIII NRVs",
            "voluntary_nutrients": "Mono-unsaturates, polyunsaturates, polyols, starch, dietary fibre, vitamins and minerals may be added",
            "front_of_pack": "Member states may promote voluntary FOP schemes (Nutri-Score in France, DE, BE, NL, ES, PT; traffic light in UK — pre-Brexit)",
            "added_sugar_required": False,
        },
        "allergen_rules": {
            "top_allergens": ["Cereals containing gluten", "Crustaceans", "Eggs", "Fish", "Peanuts", "Soybeans", "Milk", "Nuts", "Celery", "Mustard", "Sesame seeds", "Sulphur dioxide and sulphites (>10mg/kg or 10mg/L)", "Lupin", "Molluscs"],
            "declaration_method": "In ingredient list with clear typographical emphasis (bold, italic, underline, contrasting colour). No separate 'Contains' statement required but recommended.",
            "regulatory_basis": "EU Regulation 1169/2011 Annex II — 14 allergens",
            "loose_food_allergen": "Allergen information must be provided for non-prepacked and loose foods (FIC Art 44)",
            "note": "EU has 14 allergens (vs 9 in USA); lupin and molluscs are EU-specific additions",
        },
        "weights_measures": {
            "net_weight_position": "Must be on label; same field of vision as product name where possible",
            "weight_units": "SI units (g, kg, mL, L) mandatory. EU Weights and Measures Directive 2014/31/EU.",
            "e_mark": "Tolerable negative error (TNE) system — 'e' mark indicates compliance with EU average fill system",
            "minimum_font_size": "Nutrition declaration: minimum 6pt font. Mandatory particulars: minimum 1.2mm x-height. If total surface <80cm²: min 0.9mm.",
            "regulatory_basis": "Directive 2007/45/EC (pre-packaged products)",
        },
        "language_requirements": {
            "mandatory_language": "Official language(s) of the Member State where sold",
            "multilingual_packaging": "Common across EU — single pack with multiple languages for pan-EU distribution",
            "minimum_requirements": "Mandatory information must be in at least one language understood by consumers in that member state",
        },
        "prohibited_claims": [
            "Health claims not on EU Register (Regulation 432/2012 + Commission Decisions)",
            "Claims suggesting food prevents, treats, or cures disease",
            "Medicinal claims on food",
            "Claims exploiting fear or suggesting slimming or body shaping",
            "References to individual doctors or health professionals recommending food",
            "Nutrition claims not listed in Annex of Regulation 1924/2006",
        ],
        "claim_rules": {
            "low_fat": "≤3g fat per 100g; liquids ≤1.5g per 100mL",
            "fat_free": "<0.5g fat per 100g/100mL",
            "low_sugar": "≤5g sugars per 100g; ≤2.5g per 100mL",
            "sugar_free": "<0.5g sugars per 100g/100mL",
            "low_sodium": "≤0.12g sodium per 100g",
            "source_of_fibre": "≥3g per 100g or ≥1.5g per 100 kcal",
            "high_fibre": "≥6g per 100g or ≥3g per 100 kcal",
            "high_in_vitamin": "≥30% NRV per 100g/100mL or per package if single portion",
            "source_of_protein": "≥12% of energy from protein",
            "reduced_calorie": "Energy reduction ≥30% vs reference product; specify the characteristic(s) reduced",
            "organic_eu": "EU Organic logo (Euroleaf) mandatory for EU-certified organic products — Regulation 2018/848",
            "health_claims": "Only EFSA-evaluated and Commission-authorised claims on Register permitted",
        },
        "special_requirements": [
            "E171 (Titanium Dioxide) banned as food colour since August 2022",
            "Palm oil must be declared by name (not 'vegetable oil') since 2014",
            "Refined oils from nuts and cereals containing gluten: must declare specific source",
            "Country of origin mandatory for: unprocessed meat (beef, pig, sheep, goat, poultry), fresh fruit and vegetables, honey, olive oil, wine, fish",
            "Batch lot marking required per Directive 2011/91/EU",
            "Frozen meat/fish that has been defrosted: must state 'defrosted'",
            "Imitation products (e.g. cheese analogue): must clearly state 'contains non-dairy fat'",
            "Nanomaterials: must be indicated as '[nano]' in ingredient list",
        ],
        "enforcement_notes": "Enforcement by national authorities (Trading Standards in UK [pre-Brexit], DGCCRF in France, BVL in Germany). EU Rapid Alert System (RASFF) for serious violations."
    },

    # ── INDIA — AYURVEDIC DRUG ────────────────────────────────────────────────
    {
        "jurisdiction": "india",
        "product_type": "ayurvedic_drug",
        "regulatory_basis": "Drugs & Cosmetics Act 1940 — Schedule T (ASU GMP); D&C Rules 1945 Rule 161",
        "competent_authority": "AYUSH Ministry + State Licensing Authorities (SLA)",
        "mandatory_fields": [
            "Brand name and generic name (Sanskrit/Hindi name of formulation)",
            "Ingredients with quantities: each ingredient listed with botanical name, Sanskrit name, and quantity per unit dose",
            "Net content / quantity (weight, volume, or number of units)",
            "Dosage: recommended dose and frequency",
            "Directions for use / method of use",
            "Contraindications and warnings",
            "Name of classical reference (if classical formulation) — e.g. 'As per Charaka Samhita'",
            "Shelf life / expiry date",
            "Manufacturing licence number",
            "Batch number",
            "Name and address of manufacturer",
            "MRP inclusive of taxes",
            "Vegetarian symbol (where applicable)",
            "Storage conditions",
        ],
        "nutrition_declaration": {
            "required": False,
            "notes": "Nutritional declaration not required for classical Ayurvedic drugs. For patent/proprietary Ayurvedic products with nutrient claims, FSSAI nutrition label rules may apply if borderline product."
        },
        "allergen_rules": {
            "required": False,
            "notes": "No formal allergen declaration mandate under D&C Act for Ayurvedic drugs. However, ingredients of common allergen origin (sesame, milk products, nuts in formulations) should be declared in ingredient list."
        },
        "weights_measures": {
            "net_quantity": "In SI units. For tablets: number of tablets + total weight. For syrups: volume in mL.",
            "regulatory_basis": "Legal Metrology Rules 2011 apply",
        },
        "language_requirements": {
            "mandatory_language": "Hindi and English (bilingual label mandatory). Sanskrit names of herbs encouraged but must have common/Latin name alongside.",
            "classical_references": "Classical texts may be referenced in original Sanskrit with English translation",
        },
        "prohibited_claims": [
            "Claims of cure for specific allopathic-defined diseases without substantiation",
            "Comparative claims over allopathic medicines",
            "Claims that the product has no side effects (absolute claims prohibited)",
            "Claims of aphrodisiac effects (regulated separately under AYUSH guidelines)",
            "Celebrity endorsement without AYUSH approval",
            "Magical/miraculous cure claims",
        ],
        "claim_rules": {
            "traditional_use": "Claims based on classical Ayurvedic texts are permitted if formulation matches text reference",
            "health_maintenance": "General health maintenance claims allowed ('promotes digestive health', 'supports immunity')",
            "disease_claims": "Specific disease treatment claims require additional clinical evidence and Ministry approval",
        },
        "special_requirements": [
            "For heavy-metal-containing formulations (Bhasmas): mandatory 'This product contains processed heavy metals as per classical Ayurvedic method' declaration",
            "Classical reference text and verse number must appear on label for classical preparations",
            "'Not recommended for use in pregnancy/lactation' warning if applicable",
            "For export: additional country-specific requirements may apply (e.g. TGA for Australia, Health Canada for Canada)",
            "AYUSH premium mark / certification mark (if applicable)",
        ],
        "enforcement_notes": "Enforced by State Drug Controllers (SDC) for manufacturing compliance. AYUSH Ministry for policy. Non-compliant products may be seized under D&C Act Section 27. Heavy metal content in Bhasmas is regulated but frequently contested."
    },

    # ── JAPAN — FOOD WITH FUNCTION CLAIMS (FFC) ───────────────────────────────
    {
        "jurisdiction": "japan",
        "product_type": "food_with_function_claims",
        "regulatory_basis": "Food Labeling Act 2015; Cabinet Office Ordinance on Food Labeling Standards (FLS) Art. 61",
        "competent_authority": "Consumer Affairs Agency (CAA)",
        "mandatory_fields": [
            "Product name",
            "Name and address of FBO",
            "Net contents",
            "Expiration date",
            "Storage method",
            "FFC notification number (provided by CAA after notification)",
            "Function claim statement (exactly as notified — must match CAA database)",
            "Disclaimer: 'This product has not been evaluated by the Secretary of Consumer Affairs for its safety and function'",
            "Disclaimer: 'This product is not intended to diagnose, treat, cure or prevent any disease'",
            "Target consumer statement (if applicable — e.g. not for children under X years)",
            "Intake method and amount",
            "Cautions against excessive consumption",
            "Ingredients list",
            "Nutritional components (functional ingredient must be declared with quantity)",
        ],
        "nutrition_declaration": {
            "mandatory_nutrients": ["Energy (kcal)", "Protein (g)", "Fat (g)", "Carbohydrate (g)", "Salt equivalent (g) — sodium × 2.54", "Functional ingredient with quantity"],
            "per_serving_required": True,
            "format": "Per serving (and per 100g/100mL recommended). Salt expressed as 'salt equivalent' not sodium. Energy in kcal only.",
            "nrv_reference": "Japan NRV per Food Labeling Standards Annex 9",
        },
        "allergen_rules": {
            "top_allergens": ["Shrimp", "Crab", "Wheat", "Buckwheat", "Egg", "Milk", "Peanuts", "Walnut (added 2023)", "Almond (added 2023)"],
            "recommended_allergens": "20 additional recommended declaration items (abalone, squid, salmon, etc.)",
            "declaration_method": "In ingredient list or separately. Mandatory 7 allergens must be present.",
            "regulatory_basis": "Food Labeling Standards — Cabinet Office Ordinance; amended 2023 (walnut, almond added as mandatory)",
        },
        "weights_measures": {
            "units": "Metric system (g, mL, L). No dual labeling requirement.",
            "serving_size": "Must match notified FFC serving size exactly",
        },
        "language_requirements": {
            "mandatory_language": "Japanese mandatory for all required label information",
            "english_allowed": "English may appear additionally but Japanese takes precedence",
        },
        "prohibited_claims": [
            "Disease name claims",
            "Any claim beyond the single notified function claim",
            "Medical device-type claims",
            "Claims not substantiated by the systematic literature review submitted",
        ],
        "claim_rules": {
            "ffc_claim": "Only the exact function claim approved/accepted in CAA notification database may be used",
            "scientific_basis": "Systematic review of published RCTs required; if no RCT, observational studies with expert opinion",
            "gut_health_updated_2024": "Meta-analysis now required for probiotic/prebiotic gut health claims following 2024 CAA guidance update",
        },
        "special_requirements": [
            "CAA notification must be submitted 60 days before launch and published on CAA website",
            "Functional ingredient must be in final product (not lost in processing)",
            "Post-market surveillance report required if consumer complaints arise",
            "Self-monitoring by FBO required — testing plan must be maintained",
        ],
        "enforcement_notes": "CAA conducts post-market monitoring of FFC products. Misleading claims: CAA issues public notice and requests correction. Serious violations: FSS Act penalties apply."
    },

    # ── AUSTRALIA — THERAPEUTIC GOODS (LISTED COMPLEMENTARY MEDICINE) ─────────
    {
        "jurisdiction": "australia",
        "product_type": "complementary_medicine",
        "regulatory_basis": "Therapeutic Goods Act 1989; Therapeutic Goods Order 92 (TGO 92) — Requirements for labels; TGO 93",
        "competent_authority": "TGA (Therapeutic Goods Administration)",
        "mandatory_fields": [
            "Product name (including 'listed' if Listed Medicine on ARTG)",
            "ARTG entry number (AUST L XXXXXXX — mandatory on label)",
            "Name and address of sponsor (Australian company)",
            "Ingredient list: each active and excipient ingredient by name",
            "Quantity of each active ingredient per dosage unit",
            "Directions for use",
            "Warnings and precautions",
            "Contraindications",
            "Net contents / number of units",
            "Batch/lot number",
            "Expiry date (month and year minimum: 'EXP MM/YYYY')",
            "Storage conditions",
            "Country of origin of active ingredient(s) if from single country",
        ],
        "nutrition_declaration": {
            "required": False,
            "notes": "Nutritional panel not required for listed medicines under TGO 92. If product is dual-regulated (food + medicine), food labeling rules may overlay."
        },
        "allergen_rules": {
            "top_allergens": ["Gluten (from wheat, rye, barley, oats)", "Eggs", "Fish", "Peanuts", "Cow's milk", "Sesame seeds", "Soy", "Shellfish (crustaceans)", "Tree nuts"],
            "declaration_method": "Declare in ingredient list. 'Contains [allergen]' statement recommended.",
            "regulatory_basis": "TGO 92 requires declaration of excipients with known action; FSANZ Code for food aspects",
        },
        "weights_measures": {
            "units": "SI units mandatory",
            "tablet_count": "Number of tablets/capsules must be stated",
            "regulatory_basis": "Trade Measurement Act 1999 (Cwlth); TGO 92",
        },
        "language_requirements": {
            "mandatory_language": "English",
            "bilingual_allowed": "Other languages may be added",
        },
        "prohibited_claims": [
            "Claims implying treatment/cure of a serious disease (requires Registered medicine, not Listed)",
            "Claims of clinical efficacy not supported by evidence",
            "Unacceptable representations under TGA Advertising Code",
            "Testimonials in therapeutic goods advertising (restricted)",
            "Health practitioner testimonials unless specific conditions met",
        ],
        "claim_rules": {
            "listed_medicine_claims": "General level health claims permitted. Must be 'traditional use' or 'systematic review' evidence level.",
            "high_level_claims": "High-level health claims require Registered medicine (not Listed). E.g. 'reduces risk of cardiovascular disease'.",
            "traditional_use": "Traditional use evidence acceptable for listed medicines — 30+ years documented use",
            "advertising_code": "TGA Advertising Code 2021 governs all therapeutic goods advertising. Pre-approval from TGA not required but self-regulation expected.",
        },
        "special_requirements": [
            "AUST L (or AUST R for registered) number must appear on primary label",
            "Sponsor must be an Australian entity responsible for the product",
            "Annual product review (APR) required for all sponsors",
            "Adverse event reporting mandatory to TGA for serious events",
            "Traditional Chinese Medicine herbs: must declare pinyin name, Latin name, and part used",
            "Ayurvedic products: if listed, must use permitted ingredients list and comply with heavy metal advisory",
        ],
        "enforcement_notes": "TGA monitors market compliance. Non-compliant products may be cancelled from ARTG and subject to recall. Criminal penalties apply for serious offences under TGA 1989."
    },
]


@router.get("/labeling-requirements", response_model=List[LabelingRequirementOut])
async def list_labeling(
    jurisdiction: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(LabelingRequirement).where(LabelingRequirement.is_active == True)  # noqa
    if jurisdiction:
        stmt = stmt.where(LabelingRequirement.jurisdiction == jurisdiction)
    if product_type:
        stmt = stmt.where(LabelingRequirement.product_type == product_type)
    result = await db.execute(stmt.order_by(LabelingRequirement.jurisdiction, LabelingRequirement.product_type))
    return result.scalars().all()


@router.post("/labeling-requirements/seed", include_in_schema=False)
async def seed_labeling(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import delete
    await db.execute(delete(LabelingRequirement))
    for item in LABELING_DATA:
        db.add(LabelingRequirement(**item))
    await db.commit()
    return {"seeded": len(LABELING_DATA)}
