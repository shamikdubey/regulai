"""
Licensing & Registration Navigator endpoint.
Per product type + jurisdiction: license type, authority, pathway steps,
fees, timelines, GMP requirements, renewal, prerequisites checklist.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, String, Text, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

from app.db.database import get_db, Base
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()


class LicensingPathway(Base):
    __tablename__ = "licensing_pathways"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_subtype: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license_type: Mapped[str] = mapped_column(String(200), nullable=False)
    competent_authority: Mapped[str] = mapped_column(String(150), nullable=False)
    application_portal: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    pathway_steps: Mapped[list] = mapped_column(JSON, nullable=False)
    prerequisites: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    documents_required: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    fees: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    typical_timeline_months: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fast_track_available: Mapped[bool] = mapped_column(Boolean, default=False)
    fast_track_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gmp_requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    renewal_period_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    renewal_requirements: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    post_approval_obligations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    reference_regulation: Mapped[str] = mapped_column(String(255), nullable=False)
    complexity: Mapped[str] = mapped_column(String(10), default="MEDIUM")  # LOW / MEDIUM / HIGH
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at = mapped_column(nullable=True)


class LicensingPathwayOut(BaseModel):
    id: uuid.UUID
    jurisdiction: str
    product_type: str
    product_subtype: Optional[str]
    license_type: str
    competent_authority: str
    application_portal: Optional[str]
    pathway_steps: list
    prerequisites: Optional[list]
    documents_required: Optional[list]
    fees: Optional[dict]
    typical_timeline_months: Optional[str]
    fast_track_available: bool
    fast_track_details: Optional[str]
    gmp_requirements: Optional[dict]
    renewal_period_years: Optional[int]
    renewal_requirements: Optional[list]
    post_approval_obligations: Optional[list]
    reference_regulation: str
    complexity: str
    notes: Optional[str]
    model_config = {"from_attributes": True}


LICENSING_DATA = [
    # ── INDIA — FSSAI FOOD BUSINESS OPERATOR ──────────────────────────────────
    {
        "jurisdiction": "india", "product_type": "food", "product_subtype": "food_business_operator",
        "license_type": "FSSAI Central Licence / State Licence / Basic Registration",
        "competent_authority": "FSSAI (Food Safety and Standards Authority of India)",
        "application_portal": "https://foscos.fssai.gov.in",
        "complexity": "MEDIUM",
        "pathway_steps": [
            "1. Determine category: Basic Registration (turnover <₹12 lakh/yr), State Licence (₹12L–₹20Cr/yr or specific operations), Central Licence (turnover >₹20Cr, importers, exporters, large manufacturers)",
            "2. Gather required documents (see Documents Required)",
            "3. Apply online via FOSCOS portal — fill Form A (registration) or Form B (licence)",
            "4. Pay application fee online",
            "5. Inspection by FSO (Food Safety Officer) within 30 days of application (for Licence)",
            "6. Comply with any deficiency notice within 15 days",
            "7. Receive FSSAI Licence/Registration certificate (14-digit number)",
            "8. Display licence at premises; print 14-digit number on all products"
        ],
        "prerequisites": [
            "Proof of business entity (partnership deed / MOA / Incorporation certificate)",
            "Food safety management plan / HACCP (for larger businesses)",
            "Proof of premises ownership / rental agreement",
            "NOC from local municipal body",
            "Water quality test report",
            "List of food categories / products to be manufactured"
        ],
        "documents_required": [
            "Form B application (for licence)",
            "Blueprint/layout of processing unit",
            "List of equipment and machinery",
            "Food safety management system document",
            "Name and address of proprietors/directors",
            "Identity and address proof of all partners/directors",
            "Analysis report of water to be used",
            "Recall plan",
            "For importers: IEC (Import Export Code) from DGFT"
        ],
        "fees": {
            "Basic Registration": "₹100/year",
            "State Licence": "₹2,000–₹5,000/year depending on category",
            "Central Licence": "₹7,500/year",
            "Importer Central Licence": "₹7,500/year",
            "Manufacturer (Medium/Large)": "₹7,500/year"
        },
        "typical_timeline_months": "0.5–2 months (registration 7–30 days; licence 30–60 days)",
        "fast_track_available": False,
        "gmp_requirements": {
            "standard": "Schedule 4 Food Safety Management System (FSMS)",
            "haccp": "HACCP implementation encouraged; mandatory for export-oriented units",
            "iso22000": "ISO 22000 accepted as equivalent to Schedule 4 FSMS",
            "notes": "GMP inspection by FSO before issuance of licence"
        },
        "renewal_period_years": 5,
        "renewal_requirements": ["Apply 30 days before expiry via FOSCOS", "No inspection required if no change in business; fee payment required"],
        "post_approval_obligations": [
            "Display FSSAI licence at premises",
            "Print FSSAI licence number on all labels",
            "Maintain records of raw material purchase, manufacturing, sales for 2 years",
            "Submit Annual Return (Form D2) by 31 May each year",
            "Report food safety incidents to FSSAI within 24 hours",
            "Comply with periodic FSO inspections"
        ],
        "reference_regulation": "FSS Act 2006; FSS (Licensing & Registration of FBOs) Regulations 2011",
        "notes": "India's FSSAI operates FOSCOS portal for all licence/registration applications. Processing time varies by state. Priority processing not formally offered but larger businesses may get faster inspector visits."
    },

    # ── INDIA — FSSAI NUTRACEUTICALS ─────────────────────────────────────────
    {
        "jurisdiction": "india", "product_type": "nutraceutical", "product_subtype": "health_supplement",
        "license_type": "FSSAI Central Licence (Manufacturer) — Health Supplements & Nutraceuticals",
        "competent_authority": "FSSAI",
        "application_portal": "https://foscos.fssai.gov.in",
        "complexity": "HIGH",
        "pathway_steps": [
            "1. Determine product category under FSS (Nutraceuticals) Regulations 2022 — health supplement / nutraceutical / functional food / probiotic / novel food",
            "2. Check if all ingredients are in positive list (Schedules I–IV of Nutraceuticals Regs) — non-listed ingredients require prior FSSAI approval",
            "3. Verify ingredient doses comply with Schedule limits",
            "4. Prepare product formulation, technical dossier, and safety substantiation",
            "5. If novel ingredient: submit Novel Food application to FSSAI Scientific Panel",
            "6. Apply for FSSAI Central Licence via FOSCOS (Form B, Category: Nutraceuticals)",
            "7. Submit product label design for pre-approval (recommended for nutraceuticals)",
            "8. Undergo GMP inspection (Schedule 4 FSMS minimum; pharma-grade GMP recommended)",
            "9. Receive Central Licence",
            "10. Launch product — all labels must comply with FSS Labelling & Nutraceuticals Regs"
        ],
        "prerequisites": [
            "All ingredients must be from FSSAI positive list or have prior approval",
            "Doses must not exceed Upper Tolerable Intake Levels in Schedule",
            "Manufacturing facility must meet Schedule 4 FSMS minimum",
            "Certificate of Analysis (CoA) for each ingredient",
            "Safety data / substantiation for claims",
            "Stability study data (at least accelerated stability)"
        ],
        "documents_required": [
            "Form B application (Central Licence)",
            "Product formulation with ingredient quantities",
            "Ingredient specifications and CoAs",
            "Manufacturing process flow diagram",
            "Label draft (Principal Display Panel and Information Panel)",
            "Claims substantiation documents",
            "Stability data report",
            "Safety assessment (toxicology summary for novel ingredients)",
            "GMP compliance certificate (if pharma-grade facility)"
        ],
        "fees": {
            "Central Licence (Manufacturer)": "₹7,500/year",
            "Novel Food Application": "₹50,000 (one-time evaluation fee)",
            "Product approval (if required)": "₹10,000–₹25,000"
        },
        "typical_timeline_months": "3–12 months (novel ingredients: 12–18 months)",
        "fast_track_available": False,
        "gmp_requirements": {
            "minimum": "Schedule 4 FSMS (FSSAI food GMP)",
            "recommended": "Schedule M pharma-grade GMP (especially for capsule/tablet dosage forms)",
            "iso": "ISO 22000 / FSSC 22000 accepted",
            "notes": "CDSCO may claim jurisdiction if product uses pharma-grade excipients or high doses"
        },
        "renewal_period_years": 5,
        "renewal_requirements": ["30 days before expiry", "No formulation changes without fresh approval"],
        "post_approval_obligations": [
            "Print FSSAI licence number on all labels",
            "Submit Annual Return by 31 May",
            "Report adverse events to FSSAI",
            "Maintain batch manufacturing records for 3 years",
            "Conduct periodic stability testing"
        ],
        "reference_regulation": "FSS (Health Supplements, Nutraceuticals…) Regulations 2022; FSS (Licensing & Registration) Regulations 2011",
        "notes": "CRITICAL: Products making therapeutic claims (disease treatment/prevention) fall under CDSCO regulation and require New Drug Application. The FSSAI/CDSCO grey zone is the single biggest compliance risk for nutraceutical manufacturers in India."
    },

    # ── INDIA — CDSCO MEDICAL DEVICES ────────────────────────────────────────
    {
        "jurisdiction": "india", "product_type": "medical_device", "product_subtype": "Class_B_C_D",
        "license_type": "CDSCO Import/Manufacturing Licence for Medical Devices (Form MD-5/MD-9)",
        "competent_authority": "CDSCO (Central Drugs Standard Control Organization) — DCGI",
        "application_portal": "https://sugam.cdsco.gov.in",
        "complexity": "HIGH",
        "pathway_steps": [
            "1. Classify device under MDR 2017 Schedule III (Class A, B, C, or D based on risk)",
            "2. Class A (low risk): Enrolment only via SUGAM — no quality review",
            "3. Class B/C/D: Obtain ISO 13485 certification from NABH-accredited CB",
            "4. Prepare Technical File / Design Dossier per MDR 2017 Schedule VII",
            "5. For Class C/D: Clinical data — reference agency (FDA/CE) approval accepted OR Indian clinical trial",
            "6. Apply on SUGAM portal — Form MD-14 (import) or Form MD-5 (manufacture)",
            "7. CDSCO review — Technical Expert Committee (TEC) review for Class C/D",
            "8. Reply to queries within 30 days",
            "9. Manufacturing facility inspection (for domestic manufacturers)",
            "10. Grant of licence — Form MD-9 (manufacture) or MD-15 (import)"
        ],
        "prerequisites": [
            "Device classified under MDR 2017 notified devices list",
            "ISO 13485 QMS certification (for Class B, C, D)",
            "EU CE Mark or US FDA clearance speeds review for Class C/D (not mandatory)",
            "Free Sale Certificate from country of origin (for imports)",
            "Clinical evidence: published literature, overseas approval data, or Indian clinical trial data"
        ],
        "documents_required": [
            "Form MD-14 (import) or MD-5 (manufacture) application",
            "Device description and intended use",
            "Technical file: risk management (ISO 14971), design verification & validation",
            "ISO 13485 certificate",
            "Performance/safety test reports from accredited labs",
            "Labeling (draft) compliant with MDR 2017 Schedule IX",
            "Post-market surveillance plan",
            "Shelf-life/stability data",
            "Free Sale Certificate (imports)"
        ],
        "fees": {
            "Class A enrolment": "₹500",
            "Class B (Import Licence)": "₹3,000",
            "Class C (Import Licence)": "₹5,000",
            "Class D (Import Licence)": "₹10,000",
            "Class B (Manufacturing Licence)": "₹1,500",
            "Class D (Manufacturing Licence)": "₹5,000"
        },
        "typical_timeline_months": "Class A: 1 month. Class B: 3–6 months. Class C: 6–12 months. Class D: 12–18 months.",
        "fast_track_available": True,
        "fast_track_details": "Priority review for devices with US FDA clearance / EU CE mark. Waivers available for devices already approved in reference countries under MDR 2017 Rule 24.",
        "gmp_requirements": {
            "standard": "ISO 13485:2016 — Quality Management Systems for Medical Devices",
            "certification_body": "NABH-accredited or internationally recognised CB (BSI, TÜV, SGS, Bureau Veritas)",
            "inspection": "CDSCO factory inspection for Class C/D domestic manufacturers",
            "schedule_m3": "Medical Device Rules 2017 Schedule M III prescribes GMP requirements for medical devices"
        },
        "renewal_period_years": 5,
        "renewal_requirements": ["Apply 6 months before expiry", "Submit renewal dossier with PSS (post-market surveillance) summary", "Fee payment"],
        "post_approval_obligations": [
            "Report serious incidents to CDSCO within 30 days (Vigilance reporting Form MD-27)",
            "Maintain complaint register",
            "Annual product quality review",
            "Unique Device Identifier (UDI) marking (phased implementation)",
            "Post-market clinical follow-up (PMCF) for Class C/D"
        ],
        "reference_regulation": "Medical Devices Rules 2017 (amended 2020); Drugs & Cosmetics Act 1940",
        "notes": "Software as Medical Device (SaMD): classified under MDR 2017 if it meets device definition. CDSCO has specific SaMD guidance aligning with IEC 62304. Digital health apps may require device licence."
    },

    # ── INDIA — AYUSH MANUFACTURING LICENCE ──────────────────────────────────
    {
        "jurisdiction": "india", "product_type": "ayurveda", "product_subtype": "ayurvedic_manufacturer",
        "license_type": "AYUSH Manufacturing Licence (Form 25-D / 26-D for ASU drugs)",
        "competent_authority": "State Licensing Authority (SLA) + Drugs Controller of State",
        "application_portal": "State Drug Controller portals (varies by state)",
        "complexity": "MEDIUM",
        "pathway_steps": [
            "1. Determine product type: Classical (as per official formulary) vs Patent/Proprietary",
            "2. Prepare site master file and manufacturing facility layout",
            "3. Appoint qualified person: Ayurvedic Pharmacist (D.Pharm Ayurveda) or qualified Ayurvedic practitioner",
            "4. Ensure Schedule T GMP compliance: separate manufacturing areas, QC lab, storage",
            "5. Apply to State Licensing Authority via Form 24-D (new licence) with prescribed fees",
            "6. Inspection by State Drug Inspector",
            "7. Comply with inspection deficiencies within 3 months",
            "8. Grant of Manufacturing Licence in Form 25-D",
            "9. For export: apply for AYUSH Export Certificate / Free Sale Certificate from AYUSH Ministry"
        ],
        "prerequisites": [
            "Qualified Ayurvedic Pharmacist on staff (D.Pharm Ayurveda / BAMS)",
            "Dedicated manufacturing premises meeting Schedule T specifications",
            "QC laboratory or arrangement with approved external lab",
            "List of formulations to be manufactured — classical or patent/proprietary",
            "For patent/proprietary: formula composition, processing, and safety data"
        ],
        "documents_required": [
            "Form 24-D application",
            "Site plan and layout of manufacturing unit",
            "List of equipment",
            "Qualified person appointment letter and qualification proof",
            "Raw material storage plan",
            "Finished product storage plan",
            "Quality control SOPs",
            "List of intended products with formulations"
        ],
        "fees": {
            "Application fee (per category)": "₹1,000–₹5,000 (varies by state)",
            "Annual licence fee": "₹500–₹2,000 (varies by state and number of formulations)"
        },
        "typical_timeline_months": "3–9 months depending on state",
        "fast_track_available": False,
        "gmp_requirements": {
            "standard": "Schedule T of D&C Rules 1945 (GMP for ASU Drugs)",
            "key_requirements": "Dedicated aseptic zones, raw material authentication by botanist/pharmacognosist, batch manufacturing records",
            "heavy_metals": "Bhasma/mineral formulations: special GMP and testing protocols for heavy metal processing",
            "iso_equivalent": "WHO GMP for herbal medicines accepted as guidance"
        },
        "renewal_period_years": 5,
        "renewal_requirements": ["Apply to SLA before expiry", "GMP re-inspection may be required", "No change in qualified person without intimation"],
        "post_approval_obligations": [
            "Maintain batch manufacturing records for 3 years",
            "Submit annual GMP compliance certificate",
            "Report adverse drug reactions to Pharmacovigilance Programme of India (PvPI)",
            "For classical formulations: maintain reference to classical text",
            "For export: obtain Free Sale Certificate from AYUSH Ministry for each consignment country"
        ],
        "reference_regulation": "Drugs & Cosmetics Act 1940 — Chapter IV A (ASU drugs); D&C Rules 1945 Rule 157–170",
        "notes": "State licensing creates significant variation in processing times. Maharashtra, Gujarat, Himachal Pradesh (major Ayurvedic manufacturing states) generally have more streamlined processes. Classical formulations have easier approval pathway than patent/proprietary."
    },

    # ── USA — FDA DIETARY SUPPLEMENT ─────────────────────────────────────────
    {
        "jurisdiction": "usa", "product_type": "nutraceutical", "product_subtype": "dietary_supplement",
        "license_type": "No Pre-Market Approval — Facility Registration + cGMP Compliance + New Dietary Ingredient (NDI) Notification if required",
        "competent_authority": "FDA — Center for Food Safety and Applied Nutrition (CFSAN)",
        "application_portal": "https://www.accessdata.fda.gov/scripts/fdcc/?set=FoodFacilities",
        "complexity": "MEDIUM",
        "pathway_steps": [
            "1. Determine if product qualifies as dietary supplement under DSHEA (not a conventional food, not a drug, not an OTC)",
            "2. Check if any ingredient is a New Dietary Ingredient (NDI) — marketed after 15 October 1994",
            "3. If NDI: file NDI Notification with FDA at least 75 days before marketing",
            "4. Register manufacturing facility with FDA via Food Facility Registration System (every 2 years)",
            "5. Ensure cGMP compliance — 21 CFR Part 111 (full compliance for all supplements)",
            "6. Prepare Supplement Facts panel (per 21 CFR 101.36)",
            "7. If making structure/function claims: notify FDA within 30 days of first marketing",
            "8. Launch product — no FDA pre-approval required",
            "9. Maintain serious adverse event reporting (AER) system"
        ],
        "prerequisites": [
            "FDA facility registration (mandatory for manufacturers, packers, distributors with US facility)",
            "NDI notification if using post-1994 ingredient not GRAS or not covered by prior article of commerce",
            "cGMP compliance — 21 CFR Part 111",
            "Quality records, batch records, specifications on file",
            "Identity testing of each incoming dietary ingredient"
        ],
        "documents_required": [
            "FDA Facility Registration (online, no fee)",
            "NDI Notification (if applicable) — detailed safety dossier",
            "Structure/Function Claim Notification (30-day notification to FDA)",
            "Internal quality documentation (not submitted to FDA but must be available for inspection)",
            "Adverse event reporting records"
        ],
        "fees": {
            "Facility Registration": "Free",
            "NDI Notification": "Free to file (FDA internal review)",
            "DUNS Number": "Free",
            "User Fee (if drug status claimed)": "N/A for supplements"
        },
        "typical_timeline_months": "0–3 months (no pre-approval needed; NDI review takes ~75 days)",
        "fast_track_available": True,
        "fast_track_details": "No pre-approval needed — DSHEA allows market entry without FDA review if ingredients are pre-1994 or GRAS. NDI notification is 75-day waiting period only.",
        "gmp_requirements": {
            "standard": "21 CFR Part 111 — Current Good Manufacturing Practice in Manufacturing, Packaging, Labeling, or Holding Operations for Dietary Supplements",
            "effective_date": "Phased implementation 2008–2010; all companies covered since 2010",
            "key_elements": "Identity testing, batch records, specifications, laboratory controls, consumer complaint records, returned product records",
            "third_party_cert": "NSF International, USP Verified, Informed Sport voluntary certification programs enhance credibility"
        },
        "renewal_period_years": 2,
        "renewal_requirements": ["FDA Facility Re-registration every 2 years (October-December window)"],
        "post_approval_obligations": [
            "Mandatory Serious Adverse Event Reporting (SAER) to FDA within 15 business days",
            "Maintain records for 1 year (2 years for components with shelf life >1 year)",
            "Voluntary FDA Reportable Food Registry for food safety events",
            "Comply with FDA warning letters promptly",
            "Import alerts: foreign supplements may be subject to Import Alert 54-15 (automatic detention)"
        ],
        "reference_regulation": "DSHEA 1994 (Dietary Supplement Health and Education Act); 21 CFR Part 111 (cGMP); 21 CFR 190 (NDI); FSMA 2011",
        "notes": "The USA has the most permissive pre-market environment for supplements globally. However, FTC regulates advertising separately with strict substantiation requirements. FDA enforcement is aggressive post-market — warning letters, import alerts, and criminal prosecution for adulterated products."
    },

    # ── USA — FDA 510(k) MEDICAL DEVICE ──────────────────────────────────────
    {
        "jurisdiction": "usa", "product_type": "medical_device", "product_subtype": "Class_II_510k",
        "license_type": "510(k) Premarket Notification — Substantial Equivalence Clearance",
        "competent_authority": "FDA — Center for Devices and Radiological Health (CDRH)",
        "application_portal": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm (eSTAR system)",
        "complexity": "HIGH",
        "pathway_steps": [
            "1. Classify device using FDA product code database and determine if Class I exempt, Class II (510k), or Class III (PMA)",
            "2. Identify predicate device(s) — cleared or approved device with same intended use and technological characteristics",
            "3. Prepare 510(k) submission: traditional, abbreviated, or special 510(k)",
            "4. Conduct performance testing per applicable Special Controls and FDA guidance",
            "5. Submit eSTAR 510(k) via FDA portal with required sections",
            "6. FDA acceptance review (15 days)",
            "7. Substantive review: FDA may issue Additional Information (AI) request — respond within 90 days",
            "8. Receive 510(k) Clearance letter (SE — Substantially Equivalent determination)",
            "9. Register establishment with FDA (annual registration + listing)",
            "10. Implement QSR/QMSR (Quality System Regulation) compliance"
        ],
        "prerequisites": [
            "Predicate device identified (previously cleared 510(k) or pre-SMDA 1976 device)",
            "Performance testing per recognized voluntary consensus standards (VCOS)",
            "Quality System (ISO 13485 or 21 CFR Part 820 QSR)",
            "Biocompatibility per ISO 10993 if patient contact device",
            "Software validation per FDA guidance (if SaMD)",
            "Clinical data if performance cannot be demonstrated by bench testing"
        ],
        "documents_required": [
            "eSTAR 510(k) form (all required sections including device description, substantial equivalence, performance testing)",
            "Performance testing reports",
            "Biocompatibility data (ISO 10993)",
            "Sterilization validation (if sterile device)",
            "Electrical safety (IEC 60601) for electro-medical devices",
            "Software documentation (if device contains software)",
            "Proposed labeling",
            "510(k) Summary or 510(k) Statement"
        ],
        "fees": {
            "Standard 510(k) Fee (FY2024)": "$25,170 (large entities); $6,293 (small business)",
            "Annual Establishment Registration": "$5,672 (FY2024)",
            "De Novo Request": "$28,052 (large); $7,013 (small)"
        },
        "typical_timeline_months": "3–12 months (FDA goal: 90 days from acceptance; often 6–9 months in practice)",
        "fast_track_available": True,
        "fast_track_details": "Breakthrough Device Designation (BDD) for devices treating serious conditions — interactive review, priority review, senior FDA staff. Pre-Submission (Q-Sub) meetings recommended before submission to align with FDA on testing approach.",
        "gmp_requirements": {
            "standard": "21 CFR Part 820 Quality System Regulation (being updated to align with ISO 13485 under QMSR Final Rule 2024)",
            "iso13485": "ISO 13485:2016 now being adopted as basis for US QSR via QMSR",
            "inspection": "FDA Establishment Inspection (EI) after clearance and periodically",
            "notes": "Design controls, CAPA, complaint handling, MDR reporting all mandatory"
        },
        "renewal_period_years": 1,
        "renewal_requirements": ["Annual FDA Establishment Registration and Device Listing (October–December)", "Annual fee payment"],
        "post_approval_obligations": [
            "Medical Device Reporting (MDR) — serious injuries within 30 days, deaths within 30 days (or 5 days if urgency)",
            "Maintain Device History Records (DHR) for each production run",
            "Complaint handling and investigation",
            "Post-market surveillance per FDA guidance",
            "Recalls: notify FDA within 3 days for Class I recall (serious health hazard)"
        ],
        "reference_regulation": "Food Drug and Cosmetic Act Section 510(k); 21 CFR Part 807; 21 CFR Part 820 (QSR)",
        "notes": "De Novo pathway available if no predicate exists and device is novel Class II risk. PMA required for Class III devices. Software as Medical Device (SaMD) subject to FDA Digital Health Center of Excellence guidance."
    },

    # ── EU — FOOD SUPPLEMENT NOTIFICATION ────────────────────────────────────
    {
        "jurisdiction": "eu", "product_type": "nutraceutical", "product_subtype": "food_supplement",
        "license_type": "Food Supplement — Member State Notification (no EU-level pre-approval)",
        "competent_authority": "National competent authority of each Member State (e.g. ANSES in France, BVL in Germany, FSA in UK [pre-Brexit])",
        "application_portal": "Varies by member state — most have national notification portals",
        "complexity": "MEDIUM",
        "pathway_steps": [
            "1. Verify all ingredients are permitted under EU Directive 2002/46/EC (vitamins & minerals) or national positive lists",
            "2. Verify health claims if any — only EU Authorised Health Claims Register (Reg 432/2012) claims permitted",
            "3. Ensure label compliance with EU Regulation 1169/2011 (FIC) and Directive 2002/46/EC",
            "4. Submit notification to competent authority of first Member State of sale (usually before or at launch)",
            "5. Notification typically just requires label copy and sometimes compositional declaration",
            "6. No pre-market scientific evaluation by EFSA required for standard vitamins/minerals",
            "7. If novel ingredient: Novel Food application to EFSA required (EU Regulation 2015/2283) — significant process",
            "8. Launch in notified Member State",
            "9. For each additional EU country: separate notification may be required"
        ],
        "prerequisites": [
            "All ingredients on permitted list (vitamins, minerals per Directive 2002/46/EC Annex I/II)",
            "Doses within safe upper levels per SCF/EFSA opinions",
            "Label compliant with FIC Regulation 1169/2011",
            "Health claims only from EU Authorised Register",
            "Novel foods screened against EU Novel Food Catalogue — if novel: full EFSA assessment required"
        ],
        "documents_required": [
            "Label copy (PDP and information panel)",
            "Compositional declaration (ingredient list with quantities)",
            "Notification form (country-specific)",
            "Some countries require: CoA, specification sheets, manufacturing facility details"
        ],
        "fees": {
            "France (ANSES)": "Nominal administrative fee",
            "Germany": "No fee for basic notification",
            "Italy": "€50–300 per product",
            "Netherlands": "Low fee via Dutch NVWA portal",
            "Novel Food Application": "No direct EU fee but EFSA assessment costs significant time (18–36 months)"
        },
        "typical_timeline_months": "0.5–2 months (standard vitamins/minerals). Novel Food: 18–36 months.",
        "fast_track_available": False,
        "fast_track_details": "No fast-track for EU food supplements. Novel Food traditional use notification slightly faster than full Novel Food authorisation.",
        "gmp_requirements": {
            "standard": "EU GMP for food supplements — EC Regulation 852/2004 (Hygiene Regulation) and national GMP guidelines",
            "haccp": "HACCP mandatory for all food business operators per EC 852/2004",
            "iso": "ISO 22000 / FSSC 22000 widely used",
            "notes": "No mandatory pharmaceutical GMP but best practice is to follow ISO 22000 + pharmaceutical-grade QC for supplements"
        },
        "renewal_period_years": None,
        "renewal_requirements": ["No fixed renewal — update notification if formulation or label changes"],
        "post_approval_obligations": [
            "Food business operator responsible for safety (EC 178/2002 Article 19)",
            "Rapid Alert System (RASFF) notifications for unsafe products",
            "Comply with market surveillance by national authorities",
            "EFSA Novel Food authorisation includes post-market monitoring plan"
        ],
        "reference_regulation": "EU Directive 2002/46/EC (Food Supplements); EU Regulation 1169/2011 (FIC); EU Regulation 1924/2006 (Health Claims); EU Regulation 2015/2283 (Novel Foods)",
        "notes": "The EU food supplement market is highly fragmented — different member states have different positive lists for botanicals. A product legal in Germany may be illegal in France. Coordination through the European Food Supplement Association (EHPM) helps."
    },

    # ── AUSTRALIA — TGA LISTED COMPLEMENTARY MEDICINE ────────────────────────
    {
        "jurisdiction": "australia", "product_type": "nutraceutical", "product_subtype": "listed_complementary_medicine",
        "license_type": "ARTG Listing — Listed Medicine (AUST L)",
        "competent_authority": "TGA (Therapeutic Goods Administration)",
        "application_portal": "https://www.tga.gov.au/resources/resource/guidance/electronic-listing-facility",
        "complexity": "LOW",
        "pathway_steps": [
            "1. Verify product meets 'Listed medicine' eligibility: low-risk, permitted ingredients only, general level health claims only",
            "2. Check all active ingredients against TGA Permitted Ingredients Database",
            "3. Ensure doses comply with TGA's maximum permitted daily doses",
            "4. Prepare label compliant with TGO 92 and TGO 93",
            "5. Self-assess against all relevant TGA requirements (no TGA pre-evaluation for Listed)",
            "6. Submit Electronic Listing Facility (ELF) application via TGA portal — self-certification",
            "7. Pay annual ARTG listing fee",
            "8. Receive ARTG number (AUST L XXXXXXX) within 48–72 hours (automated system)",
            "9. Print AUST L number on all labels before supply",
            "10. TGA conducts post-market compliance monitoring — random desktop and physical audits"
        ],
        "prerequisites": [
            "Sponsor must be Australian company (or foreign company with Australian agent)",
            "All active ingredients from TGA Permitted Ingredients for Listed Medicines database",
            "No excluded substances",
            "Claims are general level only (not high-level health claims)",
            "Manufacturer must hold TGA Manufacturing Licence (or foreign manufacturer on TGA Approved Overseas Manufacturers list)"
        ],
        "documents_required": [
            "ELF application (online)",
            "Self-certification that all requirements are met",
            "Manufacturing evidence (TGA manufacturing licence or overseas approval)",
            "No formal dossier submitted — but must be available for TGA audit"
        ],
        "fees": {
            "ARTG Application Fee": "AUD $720 (approx, subject to annual adjustment)",
            "Annual ARTG Listing Fee": "AUD $1,000–$2,000 depending on product type",
            "Sponsor Fees": "Additional annual sponsor fees apply"
        },
        "typical_timeline_months": "0.1 months (2–5 business days for automated listing if all requirements met)",
        "fast_track_available": True,
        "fast_track_details": "Listed medicines are one of the fastest market entry pathways in the world — AUST L issued within days if ELF criteria met. This is the fastest pathway among all 10 jurisdictions for compliant supplements.",
        "gmp_requirements": {
            "standard": "TGA GMP — Code of GMP (Australian Code of GMP for Human Blood and Blood Components, Human Tissues and Human Cellular Therapy Products NOT applicable; Australian Code of GMP for Medicinal Products — PIC/S PE 009)",
            "overseas": "Foreign manufacturers must be on TGA Approved Overseas Manufacturers list — equivalence to PIC/S GMP required",
            "verification": "TGA can conduct GMP clearance review and overseas site inspection"
        },
        "renewal_period_years": 1,
        "renewal_requirements": ["Annual ARTG renewal via TGA portal", "Annual fee payment", "Confirm no changes to ARTG entry or notify TGA of variations"],
        "post_approval_obligations": [
            "Annual self-assessment against TGA requirements",
            "Respond to TGA audits (desktop or physical) within required timeframe",
            "Adverse event reporting to TGA (mandatory for serious adverse events)",
            "Comply with TGA advertising code",
            "Report any product defects or safety issues immediately"
        ],
        "reference_regulation": "Therapeutic Goods Act 1989; Therapeutic Goods Regulations 1990; TGO 92, TGO 93; TGA Advertising Code 2021",
        "notes": "Australia's Listed medicine pathway is the most efficient for compliant supplements globally. Registered medicines (AUST R) require full TGA evaluation — 12–18 months — for higher-risk products or high-level claims."
    },

    # ── CANADA — NATURAL HEALTH PRODUCTS (NPN) ───────────────────────────────
    {
        "jurisdiction": "canada", "product_type": "nutraceutical", "product_subtype": "natural_health_product",
        "license_type": "Product Licence (Natural Product Number — NPN or Homeopathic Medicine Number — DIN-HM)",
        "competent_authority": "Health Canada — Natural and Non-prescription Health Products Directorate (NNHPD)",
        "application_portal": "https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription/applications-submissions/product-licensing/electronic-submissions.html (eNHP portal since 2024)",
        "complexity": "LOW",
        "pathway_steps": [
            "1. Determine if product is an NHP (vitamin, mineral, herb, homeopathic, probiotic, essential fatty acid, or traditional medicine)",
            "2. Check Health Canada's Licensed Natural Health Products Database — if formulation already licensed, use NNHPD Class II application (simpler)",
            "3. Determine evidence class: Traditional Use (30+ years documented use) or Modern (clinical evidence)",
            "4. Prepare Product Licence Application (PLA) using eNHP portal",
            "5. Submit PLA with supporting evidence of safety and efficacy",
            "6. Health Canada review (Class I: ~90 days; Class II: ~60 days; Class III: ~180 days)",
            "7. Respond to Health Canada questions within 90 days",
            "8. Receive NPN or DIN-HM",
            "9. Print NPN on label before sale",
            "10. Notify Health Canada of any formulation or label changes"
        ],
        "prerequisites": [
            "All ingredients meet NHP Ingredient Database requirements",
            "Evidence of safety and efficacy at the proposed dose (traditional use or clinical)",
            "Site Licence for manufacturer (or Attestation of GMP compliance for foreign manufacturers)",
            "Label draft compliant with NHP Regulations"
        ],
        "documents_required": [
            "Product Licence Application (eNHP portal)",
            "Ingredient evidence (traditional use attestations, published literature, or clinical data)",
            "Label draft",
            "Site licence (for Canadian manufacturers)",
            "Attestation of GMP compliance (for foreign manufacturers)"
        ],
        "fees": {
            "Product Licence Application": "Free (no application fee under NHPR)",
            "Annual Product Licence Fee": "Free",
            "Site Licence (per site)": "CAD $1,000–$3,000 depending on activities"
        },
        "typical_timeline_months": "3–12 months depending on evidence class (Class I traditional use: ~3 months; Class III: 6–12 months)",
        "fast_track_available": True,
        "fast_track_details": "Class II applications for licensed formulations (e.g. single-vitamin supplements) review in ~60 days. Traditional use evidence accepted — no clinical trials required for most NHPs.",
        "gmp_requirements": {
            "standard": "Good Manufacturing Practices for NHPs (per NHP Regulations Part 3)",
            "site_licence": "Site licence required for all Canadian manufacturers, packagers, importers, and labellers",
            "foreign_mfr": "Foreign manufacturers must attest to GMP equivalence; Health Canada may conduct overseas inspections",
            "notes": "Canadian NHP GMP is less stringent than pharmaceutical GMP — food-grade plus additional requirements for identity testing"
        },
        "renewal_period_years": None,
        "renewal_requirements": ["No fixed renewal period — licence valid until surrendered or suspended", "Annual Site Licence renewal for manufacturers"],
        "post_approval_obligations": [
            "Report serious adverse reactions to Health Canada (mandatory — CiHI form)",
            "Maintain quality and complaint records",
            "Notify Health Canada of label or formulation changes before implementation",
            "Comply with Health Canada Market Surveillance",
            "Respond to Health Canada risk assessments or safety alerts"
        ],
        "reference_regulation": "Natural Health Products Regulations SOR/2003-196; Food and Drugs Act R.S.C. 1985",
        "notes": "Canada's NHPR is unique globally — Ayurvedic, TCM, and homeopathic products can all receive an NPN based on traditional use evidence without clinical trials. This makes Canada one of the most accessible markets for traditional medicine products."
    },

    # ── SINGAPORE — HSA HEALTH SUPPLEMENT NOTIFICATION ───────────────────────
    {
        "jurisdiction": "singapore", "product_type": "nutraceutical", "product_subtype": "health_supplement",
        "license_type": "Health Supplement — Compliance-Based (No Pre-Market Approval Required)",
        "competent_authority": "HSA (Health Sciences Authority) — Complementary Health Products Branch",
        "application_portal": "https://www.hsa.gov.sg/consumer-safety/health-products/health-supplements",
        "complexity": "LOW",
        "pathway_steps": [
            "1. Verify product meets health supplement definition under Health Products Act (HPA)",
            "2. Check all ingredients against HSA's list of permitted ingredients and excluded substances",
            "3. Verify doses comply with HSA's permitted maximum doses",
            "4. Ensure no scheduled poison, controlled drug, or potent substance",
            "5. Ensure no medicinal claims — health supplements cannot claim to treat disease",
            "6. Prepare label compliant with HSA labelling requirements",
            "7. Ensure product is manufactured under GMP conditions",
            "8. Launch product without prior HSA notification or approval",
            "9. Post-market: HSA conducts market surveillance, sampling, and testing"
        ],
        "prerequisites": [
            "Ingredients from permitted list only",
            "No excluded/prohibited substances",
            "GMP-manufactured (self-declaration)",
            "Label compliant with HSA requirements",
            "Company registered in Singapore (sole proprietorship, company, or partnership)"
        ],
        "documents_required": [
            "No documents submitted to HSA pre-market",
            "Must maintain internally: CoA for ingredients, GMP evidence, formulation records, batch records",
            "Available for HSA audit on request"
        ],
        "fees": {"Pre-market": "None", "Post-market audit": "No fee (random inspection by HSA)"},
        "typical_timeline_months": "0 months (immediate market entry if compliant)",
        "fast_track_available": True,
        "fast_track_details": "Singapore is the fastest market for health supplement launch in Asia — no notification, no pre-approval. Compliance-based system with strong post-market enforcement.",
        "gmp_requirements": {
            "standard": "Health Sciences Authority GMP Guidelines for Manufacturers of Health Supplements",
            "self_declaration": "Company self-declares GMP compliance",
            "iso22000": "ISO 22000 or FSSC 22000 recommended",
            "overseas_mfr": "Foreign manufacturers should hold ISO 22000 / HACCP certification"
        },
        "renewal_period_years": None,
        "renewal_requirements": ["No renewal — compliance-based ongoing"],
        "post_approval_obligations": [
            "Respond to HSA enquiries and provide product samples for testing if requested",
            "Report adverse events to HSA",
            "Comply with HSA recall notices",
            "Update label if required by HSA",
            "For therapeutic products (different from health supplements): separate HPA registration required"
        ],
        "reference_regulation": "Health Products Act 2007; Health Products (Health Supplements) Regulations 2010",
        "notes": "Singapore makes a clear distinction between health supplements (compliance-based) and therapeutic products (pre-market registration required). Products crossing the line — making disease claims or using scheduled substances — are treated as unregistered therapeutic goods, which is a serious offence."
    },
]


@router.get("/licensing-pathways", response_model=List[LicensingPathwayOut])
async def list_pathways(
    jurisdiction: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    complexity: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(LicensingPathway).where(LicensingPathway.is_active == True)  # noqa
    if jurisdiction:
        stmt = stmt.where(LicensingPathway.jurisdiction == jurisdiction)
    if product_type:
        stmt = stmt.where(LicensingPathway.product_type == product_type)
    if complexity:
        stmt = stmt.where(LicensingPathway.complexity == complexity)
    result = await db.execute(stmt.order_by(LicensingPathway.jurisdiction, LicensingPathway.product_type))
    return result.scalars().all()


@router.post("/licensing-pathways/seed", include_in_schema=False)
async def seed_pathways(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import delete
    await db.execute(delete(LicensingPathway))
    for item in LICENSING_DATA:
        db.add(LicensingPathway(**item))
    await db.commit()
    return {"seeded": len(LICENSING_DATA)}
