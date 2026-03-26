"""
Seed script — populates all regulatory bodies and regulations for all 10 jurisdictions.
Run: python -m scripts.seed_data
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import AsyncSessionLocal, init_db
from app.db.models import RegulatoryBody, Regulation

BODIES = [
    # ── INDIA ─────────────────────────────────────────────────────────────────
    {"acronym": "FSSAI", "name": "Food Safety and Standards Authority of India",
     "jurisdiction": "india", "domains": ["food", "nutra"], "established_year": 2006,
     "website": "fssai.gov.in",
     "description": "Apex food regulatory body under FSS Act 2006. Regulates food businesses, licensing (FLRS), health supplements, nutraceuticals, functional foods, novel foods, and food imports."},
    {"acronym": "CDSCO", "name": "Central Drugs Standard Control Organization",
     "jurisdiction": "india", "domains": ["pharma", "device"], "established_year": 1940,
     "website": "cdsco.gov.in",
     "description": "National regulatory authority for drugs, cosmetics, medical devices (Class A-D under MDR 2017), and clinical trials. Headed by DCGI. Operates SUGAM portal for e-applications."},
    {"acronym": "AYUSH", "name": "Ministry of Ayurveda, Yoga & Naturopathy, Unani, Siddha & Homeopathy",
     "jurisdiction": "india", "domains": ["ayurveda", "nutra"], "established_year": 2014,
     "website": "ayush.gov.in",
     "description": "Governs Ayurvedic, Unani, Siddha, and Homeopathic medicines. Issues manufacturing licenses, enforces ASU&H Drug quality standards, supports traditional medicine R&D and exports."},
    {"acronym": "DCGI", "name": "Drug Controller General of India",
     "jurisdiction": "india", "domains": ["pharma", "device"], "established_year": 1940,
     "website": "cdsco.gov.in",
     "description": "Key official within CDSCO responsible for approving manufacturing of biologics, vaccines, blood products, rDNA drugs, new drugs, and specific medical devices including Class C and D."},
    {"acronym": "BIS", "name": "Bureau of Indian Standards",
     "jurisdiction": "india", "domains": ["food", "device"], "established_year": 1946,
     "website": "bis.gov.in",
     "description": "National standards body setting quality specifications for food products, medical devices, and packaging. Manages ISI mark, hallmarking, and conformity assessment schemes."},

    # ── USA ───────────────────────────────────────────────────────────────────
    {"acronym": "FDA", "name": "Food and Drug Administration",
     "jurisdiction": "usa", "domains": ["food", "pharma", "device", "nutra"], "established_year": 1906,
     "website": "fda.gov",
     "description": "Primary US regulator for foods, drugs, biologics, medical devices, dietary supplements, cosmetics, and veterinary products under FD&C Act. Operates CDER, CDRH, CFSAN, and CBER centers."},
    {"acronym": "USDA-FSIS", "name": "USDA Food Safety and Inspection Service",
     "jurisdiction": "usa", "domains": ["food"], "established_year": 1862,
     "website": "fsis.usda.gov",
     "description": "Ensures the safety of meat, poultry, and egg products. Mandatory continuous inspection of slaughter facilities. Manages HACCP requirements for meat processing."},
    {"acronym": "FTC", "name": "Federal Trade Commission",
     "jurisdiction": "usa", "domains": ["food", "nutra"], "established_year": 1914,
     "website": "ftc.gov",
     "description": "Regulates health and efficacy claims in advertising for foods, supplements, and medical devices. Works alongside FDA for false or deceptive claims enforcement."},
    {"acronym": "NIH-ODS", "name": "NIH Office of Dietary Supplements",
     "jurisdiction": "usa", "domains": ["nutra"], "established_year": 1994,
     "website": "ods.od.nih.gov",
     "description": "Research and policy office within NIH for dietary supplements. Maintains DSLD ingredient database, funds safety research, and informs FDA supplement policy."},

    # ── EU ────────────────────────────────────────────────────────────────────
    {"acronym": "EMA", "name": "European Medicines Agency",
     "jurisdiction": "eu", "domains": ["pharma"], "established_year": 1995,
     "website": "ema.europa.eu",
     "description": "Centralized EU drug approval for innovative medicines, rare disease drugs (orphan), and advanced therapy medicinal products (ATMPs). Issues positive opinions; EC grants marketing authorization."},
    {"acronym": "EFSA", "name": "European Food Safety Authority",
     "jurisdiction": "eu", "domains": ["food", "nutra"], "established_year": 2002,
     "website": "efsa.europa.eu",
     "description": "Independent scientific risk assessment for food and feed safety. Evaluates health claim dossiers under EC Reg 1924/2006, approves food additives, sets ADI/TDI values."},
    {"acronym": "EC-DG-SANTE", "name": "European Commission DG Health and Food Safety",
     "jurisdiction": "eu", "domains": ["food", "pharma", "device", "nutra"], "established_year": 1999,
     "website": "ec.europa.eu/health",
     "description": "Sets EU food and pharmaceutical legislation. Oversees national competent authorities, manages EU food law framework, REACH for cosmetics, and coordinates EMA/EFSA."},
    {"acronym": "NB-MED", "name": "EU Notified Bodies for Medical Devices",
     "jurisdiction": "eu", "domains": ["device"], "established_year": 2017,
     "website": "ec.europa.eu/health/md_notifiedbodies",
     "description": "Designated organizations (BSI, TÜV, etc.) that assess conformity of Class IIa, IIb, III devices under EU MDR 2017/745. Critical bottleneck — limited NB capacity post-MDR transition."},

    # ── CHINA ─────────────────────────────────────────────────────────────────
    {"acronym": "NMPA", "name": "National Medical Products Administration",
     "jurisdiction": "china", "domains": ["pharma", "device", "food", "nutra"], "established_year": 1998,
     "website": "nmpa.gov.cn",
     "description": "China's primary regulator for drugs, medical devices, cosmetics, and health foods (BlueCap). Reorganized from CFDA in 2018. Operates online registration portals and conducts GMP inspections."},
    {"acronym": "NHSA", "name": "National Health Commission",
     "jurisdiction": "china", "domains": ["pharma"], "established_year": 2018,
     "website": "nhc.gov.cn",
     "description": "Sets public health policy, clinical standards, hospital regulations. Manages national essential medicines list and coordinates with NMPA on pharmaceutical policy and clinical trial oversight."},
    {"acronym": "SAMR", "name": "State Administration for Market Regulation",
     "jurisdiction": "china", "domains": ["food", "nutra"], "established_year": 2018,
     "website": "samr.gov.cn",
     "description": "Regulates food safety post-production, advertising claims, and market competition. Oversees China GB food safety standards jointly with NHC. Handles consumer complaints for health foods."},

    # ── JAPAN ─────────────────────────────────────────────────────────────────
    {"acronym": "PMDA", "name": "Pharmaceuticals and Medical Devices Agency",
     "jurisdiction": "japan", "domains": ["pharma", "device"], "established_year": 2004,
     "website": "pmda.go.jp",
     "description": "Reviews and approves drugs, medical devices, and regenerative medicine products. Conducts GMP inspections, pharmacovigilance, and post-market safety surveillance for MHLW."},
    {"acronym": "MHLW", "name": "Ministry of Health, Labour and Welfare",
     "jurisdiction": "japan", "domains": ["pharma", "food", "nutra"], "established_year": 2001,
     "website": "mhlw.go.jp",
     "description": "Sets pharmaceutical and food policy, issues marketing authorizations based on PMDA review. Oversees FOSHU/FFC functional food systems and food labeling standards."},
    {"acronym": "FSCJ", "name": "Food Safety Commission of Japan",
     "jurisdiction": "japan", "domains": ["food", "nutra"], "established_year": 2003,
     "website": "fsc.go.jp",
     "description": "Independent risk assessment for food safety. Evaluates food additives, pesticide residues, GMO foods, and FOSHU ingredient safety for MHLW."},

    # ── UK ────────────────────────────────────────────────────────────────────
    {"acronym": "MHRA", "name": "Medicines and Healthcare products Regulatory Agency",
     "jurisdiction": "uk", "domains": ["pharma", "device"], "established_year": 2003,
     "website": "mhra.gov.uk",
     "description": "Post-Brexit UK regulator for medicines, medical devices, clinical trials, and blood products. Operates independent UKCA marking (≠ EU CE mark since 2025). Introduced ILAP fast-track pathway."},
    {"acronym": "FSA-UK", "name": "Food Standards Agency",
     "jurisdiction": "uk", "domains": ["food", "nutra"], "established_year": 2000,
     "website": "food.gov.uk",
     "description": "Regulates food safety and labeling in England, Wales, and Northern Ireland. Manages novel foods authorization (including CBD as of 2023) and food supplement regulation post-Brexit."},
    {"acronym": "NICE", "name": "National Institute for Health and Care Excellence",
     "jurisdiction": "uk", "domains": ["pharma", "device"], "established_year": 1999,
     "website": "nice.org.uk",
     "description": "Health technology assessment for NHS. NICE guidance determines which medicines and devices are reimbursed in the UK — critical for market access strategy alongside MHRA approval."},

    # ── BRAZIL ────────────────────────────────────────────────────────────────
    {"acronym": "ANVISA", "name": "Agência Nacional de Vigilância Sanitária",
     "jurisdiction": "brazil", "domains": ["food", "pharma", "device", "nutra"], "established_year": 1999,
     "website": "gov.br/anvisa",
     "description": "Brazil's integrated health surveillance authority covering drugs, foods, medical devices, cosmetics, and blood products. Linked to Ministry of Health. Operates DATAVISA registration portal."},
    {"acronym": "MAPA-BR", "name": "Ministry of Agriculture, Livestock and Food Supply",
     "jurisdiction": "brazil", "domains": ["food"], "established_year": 1906,
     "website": "gov.br/agricultura",
     "description": "Regulates animal-origin foods, agrochemicals, animal feed, and fertilizers. Co-regulates food safety with ANVISA for meat, dairy, and animal products."},

    # ── AUSTRALIA ─────────────────────────────────────────────────────────────
    {"acronym": "TGA", "name": "Therapeutic Goods Administration",
     "jurisdiction": "australia", "domains": ["pharma", "device", "nutra", "ayurveda"], "established_year": 1991,
     "website": "tga.gov.au",
     "description": "Primary AU regulator for therapeutic goods including prescription/OTC medicines, biologics, medical devices, complementary medicines (including Ayurvedic/TCM), and blood products via ARTG."},
    {"acronym": "FSANZ", "name": "Food Standards Australia New Zealand",
     "jurisdiction": "australia", "domains": ["food", "nutra"], "established_year": 1991,
     "website": "foodstandards.gov.au",
     "description": "Joint AU-NZ body setting food standards (Australia New Zealand Food Standards Code). Covers food additives, labeling, novel foods (including lab-grown meat), fortification, and GMO foods."},

    # ── CANADA ────────────────────────────────────────────────────────────────
    {"acronym": "HC", "name": "Health Canada",
     "jurisdiction": "canada", "domains": ["pharma", "device", "food", "nutra", "ayurveda"], "established_year": 1919,
     "website": "canada.ca/health-canada",
     "description": "Federal department for drugs (NOC pathway), medical devices (MDL), food safety, natural health products (NPN under NHPR), and pesticides. Ayurvedic products can be licensed as NHPs."},
    {"acronym": "CFIA-CA", "name": "Canadian Food Inspection Agency",
     "jurisdiction": "canada", "domains": ["food"], "established_year": 1997,
     "website": "inspection.gc.ca",
     "description": "Enforces food labeling, food fraud, and import/export standards. Works with Health Canada on food safety policy under Safe Food for Canadians Act."},
    {"acronym": "PHAC", "name": "Public Health Agency of Canada",
     "jurisdiction": "canada", "domains": ["pharma", "food"], "established_year": 2004,
     "website": "phac-aspc.gc.ca",
     "description": "Manages public health emergencies, infectious disease surveillance, and coordinates with Health Canada on post-market drug and food safety monitoring."},

    # ── SINGAPORE ─────────────────────────────────────────────────────────────
    {"acronym": "HSA", "name": "Health Sciences Authority",
     "jurisdiction": "singapore", "domains": ["pharma", "device", "food", "nutra"], "established_year": 2001,
     "website": "hsa.gov.sg",
     "description": "Integrated Singapore regulator for therapeutic products, health supplements, medical devices, clinical trials, blood/organ safety, and cosmetics. Known for efficient, risk-based approvals."},
    {"acronym": "SFA", "name": "Singapore Food Agency",
     "jurisdiction": "singapore", "domains": ["food"], "established_year": 2019,
     "website": "sfa.gov.sg",
     "description": "Regulates food safety and food businesses including imports. Oversees novel food authorization (first globally to approve lab-grown meat in 2020), food additives, and food labeling."},
]

REGULATIONS = [
    # ── INDIA ─────────────────────────────────────────────────────────────────
    {"name": "Food Safety and Standards Act", "short_name": "FSS Act", "jurisdiction": "india",
     "domain": "food", "year": "2006", "status": "active",
     "description": "Primary Indian food law. Establishes FSSAI, sets standards for food safety, hygiene, licensing (FLRS), labeling, and import/export of food products."},
    {"name": "FSS (Health Supplements, Nutraceuticals, Special Dietary Uses, Functional Foods, Novel Foods and Organic Foods) Regulations",
     "short_name": "FSS Nutraceuticals Regs", "jurisdiction": "india", "domain": "nutra", "year": "2022",
     "status": "active",
     "description": "Defines and regulates nutraceuticals, health supplements, functional foods, probiotics, novel foods and organic foods under FSSAI. Sets ingredient limits, labeling, and claim restrictions."},
    {"name": "Drugs and Cosmetics Act", "short_name": "D&C Act", "jurisdiction": "india",
     "domain": "pharma", "year": "1940", "status": "active",
     "description": "Foundation of Indian pharmaceutical law. Covers import, manufacture, distribution, and sale of drugs and cosmetics. Schedules H, H1, X control prescription drugs."},
    {"name": "Medical Devices Rules", "short_name": "MDR 2017", "jurisdiction": "india",
     "domain": "device", "year": "2017", "status": "active",
     "description": "Establishes Class A-D medical device classification. Requires registration with CDSCO, QMS per ISO 13485, clinical data for Class C/D. Amended in 2020 to expand scope."},
    {"name": "New Drugs and Clinical Trials Rules", "short_name": "NDCT Rules", "jurisdiction": "india",
     "domain": "pharma", "year": "2019", "status": "active",
     "description": "Governs approval of new drugs, biologicals, and clinical trials in India. Introduces accelerated approval for rare diseases and waiver of local trials for drugs approved in reference countries."},
    {"name": "Drugs and Magic Remedies (Objectionable Advertisements) Act", "jurisdiction": "india",
     "domain": "pharma", "year": "1954", "status": "active",
     "description": "Prohibits misleading advertisements for drugs claiming to cure specified diseases. Applicable to Ayurvedic, nutraceutical, and pharmaceutical product promotions."},
    {"name": "Ayurvedic, Siddha and Unani Drugs Technical Advisory Board Rules",
     "short_name": "ASU Drugs Rules", "jurisdiction": "india", "domain": "ayurveda", "year": "2016",
     "status": "active",
     "description": "Governs manufacturing, quality standards, licensing, and Good Manufacturing Practices for Ayurvedic, Siddha, and Unani drug manufacturers. Part of Drugs & Cosmetics Act Schedule."},

    # ── USA ───────────────────────────────────────────────────────────────────
    {"name": "Federal Food, Drug, and Cosmetic Act (21 CFR)", "short_name": "FD&C Act",
     "jurisdiction": "usa", "domain": "pharma", "year": "1938", "status": "active",
     "description": "Core US law for drugs, devices, and food. Over 200 CFR parts. Key parts: 210/211 (drug GMP), 312 (IND), 314 (NDA), 600-680 (biologics), 820 (device QSR)."},
    {"name": "Dietary Supplement Health and Education Act", "short_name": "DSHEA",
     "jurisdiction": "usa", "domain": "nutra", "year": "1994", "status": "active",
     "description": "Defines dietary supplements as a food category. No pre-market approval required. Allows structure/function claims. Requires adverse event reporting (AER). GMP under 21 CFR Part 111."},
    {"name": "Food Safety Modernization Act", "short_name": "FSMA",
     "jurisdiction": "usa", "domain": "food", "year": "2011", "status": "active",
     "description": "Shifts FDA food safety from reactive to preventive. Covers: Preventive Controls for Human Food (21 CFR 117), Produce Safety Rule, FSVP for foreign suppliers, Sanitary Transportation."},
    {"name": "510(k) Premarket Notification / PMA Pathway", "jurisdiction": "usa",
     "domain": "device", "year": "1976", "status": "active",
     "description": "Class I/II devices cleared via 510(k) (substantial equivalence). Class III require PMA (pre-market approval) with clinical data. De Novo for novel low-to-moderate risk devices."},
    {"name": "21 CFR Part 111 — Current Good Manufacturing Practice for Dietary Supplements",
     "jurisdiction": "usa", "domain": "nutra", "year": "2007", "status": "active",
     "description": "Mandatory GMP requirements for dietary supplement manufacturers. Covers facility, personnel, production, laboratory operations, and record-keeping."},

    # ── EU ────────────────────────────────────────────────────────────────────
    {"name": "EC Regulation 178/2002 — General Food Law", "jurisdiction": "eu",
     "domain": "food", "year": "2002", "status": "active",
     "description": "Principles and requirements of EU food law. Establishes EFSA, defines food safety, farm-to-fork traceability, rapid alert system (RASFF), and precautionary principle."},
    {"name": "EC Regulation 1924/2006 — Nutrition and Health Claims", "jurisdiction": "eu",
     "domain": "nutra", "year": "2006", "status": "active",
     "description": "Restricts nutrition and health claims on food labels and advertising. Only EFSA-approved claims (Article 13/14) permitted. Botanical claims under Article 13(1) remain transitional."},
    {"name": "EU MDR 2017/745 — Medical Devices Regulation", "jurisdiction": "eu",
     "domain": "device", "year": "2017", "status": "active",
     "description": "Replaced MDD 93/42/EEC. Class I-III device framework with EUDAMED database, UDI system, stricter clinical evaluation, and post-market surveillance. Software as Medical Device under Rule 11."},
    {"name": "EU IVDR 2017/746 — In Vitro Diagnostics Regulation", "jurisdiction": "eu",
     "domain": "device", "year": "2017", "status": "active",
     "description": "Replaced IVDD 98/79/EC. Four class system (A-D) for IVDs with stricter performance evaluation and notified body involvement for most devices."},
    {"name": "EudraLex Volume 4 — EU GMP Guidelines", "jurisdiction": "eu",
     "domain": "pharma", "year": "1971", "status": "active",
     "description": "Good Manufacturing Practice guidelines for medicinal products. Annexes 1-20 cover sterile products, biologics, APIs, clinical trials, computerized systems, and more."},
    {"name": "Directive 2004/24/EC — Traditional Herbal Medicinal Products",
     "short_name": "THMPD", "jurisdiction": "eu", "domain": "ayurveda", "year": "2004",
     "status": "active",
     "description": "Simplified registration for traditional herbal products with 30+ years use (15+ in EU). Relevant for Ayurvedic products marketed with traditional use claims in EU member states."},

    # ── CHINA ─────────────────────────────────────────────────────────────────
    {"name": "Drug Administration Law", "short_name": "DAL", "jurisdiction": "china",
     "domain": "pharma", "year": "2019", "status": "active",
     "description": "Revised 2019 law with stricter liability, Marketing Authorization Holder (MAH) system, online drug sales regulation, and accelerated pathways for breakthrough therapies."},
    {"name": "National Food Safety Standards (GB Standards)", "jurisdiction": "china",
     "domain": "food", "year": "2015", "status": "active",
     "description": "Mandatory national standards covering food composition (GB 2760 additives, GB 2761 mycotoxins, GB 2762 contaminants) and labeling (GB 7718, GB 28050 nutrition labels)."},
    {"name": "Health Food Registration and Filing Regulations (BlueCap)",
     "jurisdiction": "china", "domain": "nutra", "year": "2016", "status": "active",
     "description": "Dual-track system: Registration (required for novel or imported health foods, 12-18 months) and Filing (domestic vitamins/minerals, faster). All imported health foods require NMPA registration."},
    {"name": "Traditional Chinese Medicine Law", "short_name": "TCM Law",
     "jurisdiction": "china", "domain": "ayurveda", "year": "2017", "status": "active",
     "description": "First dedicated TCM law. Provides IP protection for ancient prescriptions, simplified registration route for classical TCM prescriptions, and promotes TCM internationally."},
    {"name": "Regulations on the Supervision and Administration of Medical Devices",
     "jurisdiction": "china", "domain": "device", "year": "2021", "status": "active",
     "description": "Class I-III device registration with NMPA. Domestic Class I = filing, Class II/III = registration. Imported devices require NMPA registration regardless of class."},

    # ── JAPAN ─────────────────────────────────────────────────────────────────
    {"name": "Act on Securing Quality, Efficacy and Safety of Products Including Pharmaceuticals and Medical Devices",
     "short_name": "PMD Act", "jurisdiction": "japan", "domain": "pharma", "year": "2014", "status": "active",
     "description": "Replaced Pharmaceutical Affairs Law. Added regenerative medicine products as a new category. Introduces conditional/time-limited approvals for regenerative medicine products."},
    {"name": "Foods for Specified Health Uses System", "short_name": "FOSHU",
     "jurisdiction": "japan", "domain": "nutra", "year": "1991", "status": "active",
     "description": "Individual product approval system with specific health claims. Each product requires MHLW approval with clinical evidence. ~1,500 approved products. 2-3 year approval process."},
    {"name": "Food with Function Claims System", "short_name": "FFC",
     "jurisdiction": "japan", "domain": "nutra", "year": "2015", "status": "active",
     "description": "60-day notification-based system using RCT or systematic review evidence. Faster than FOSHU. Claim must be on specific ingredient (not whole food). Over 6,000 notified products."},
    {"name": "Food Labeling Act", "jurisdiction": "japan",
     "domain": "food", "year": "2015", "status": "active",
     "description": "Unified food labeling law incorporating FOSHU, FFC, nutrient content claims, and allergen labeling. Managed by Consumer Affairs Agency (CAA) and MHLW."},

    # ── UK ────────────────────────────────────────────────────────────────────
    {"name": "Human Medicines Regulations 2012 (as amended)", "jurisdiction": "uk",
     "domain": "pharma", "year": "2012", "status": "active",
     "description": "Post-Brexit UK pharmaceutical framework adapted from EU directives. Introduced Innovative Licensing and Access Pathway (ILAP) in 2021 for faster innovative medicine approval."},
    {"name": "UK Medical Devices Regulations 2002 (as amended)", "short_name": "UK MDR",
     "jurisdiction": "uk", "domain": "device", "year": "2002", "status": "active",
     "description": "Transitional UKCA marking framework. CE mark accepted until 2025 for most devices. Separate UK and EU submissions required post-Brexit. MHRA consulting on new UK MDR framework."},
    {"name": "UK Novel Food Regulations", "jurisdiction": "uk",
     "domain": "nutra", "year": "2018", "status": "active",
     "description": "FSA-managed authorization for novel food ingredients. Includes CBD (authorized as novel food 2023), certain insects, lab-grown meat, and algae-derived ingredients."},

    # ── BRAZIL ────────────────────────────────────────────────────────────────
    {"name": "RDC 240/2018 — Medical Devices Registration", "short_name": "RDC 240",
     "jurisdiction": "brazil", "domain": "device", "year": "2018", "status": "active",
     "description": "ANVISA Class I-IV device registration aligned with GHTF/IMDRF principles. Recognized CE or FDA approval can expedite registration under priority review program."},
    {"name": "RDC 272/2019 — Food Supplements", "short_name": "RDC 272",
     "jurisdiction": "brazil", "domain": "nutra", "year": "2019", "status": "active",
     "description": "Defines and regulates food supplements (vitamins, minerals, botanicals, amino acids). Separate from health claims foods. Notified to ANVISA, not pre-approved."},
    {"name": "RDC 204/2017 — Drug Registration", "jurisdiction": "brazil",
     "domain": "pharma", "year": "2017", "status": "active",
     "description": "ANVISA drug registration requirements covering new drugs, generics, similar, and biological products. Two tracks: registration (12-36 months) and priority review."},

    # ── AUSTRALIA ─────────────────────────────────────────────────────────────
    {"name": "Therapeutic Goods Act 1989", "short_name": "TG Act",
     "jurisdiction": "australia", "domain": "pharma", "year": "1989", "status": "active",
     "description": "Primary law for therapeutic goods in Australia. Establishes ARTG (Australian Register of Therapeutic Goods), TGA powers, recall mechanisms, and advertising standards."},
    {"name": "Australia New Zealand Food Standards Code", "short_name": "FSANZ Code",
     "jurisdiction": "australia", "domain": "food", "year": "2000", "status": "active",
     "description": "Comprehensive food standards covering composition, labeling, contaminants, permitted additives, and novel foods for Australia and New Zealand."},
    {"name": "Therapeutic Goods (Complementary Medicines) Reforms", "jurisdiction": "australia",
     "domain": "nutra", "year": "2018", "status": "active",
     "description": "Listed CMs (lower evidence, self-assessed) vs Registered CMs (TGA-evaluated). Evidence levels 1-4 for claims. Listed medicines can reach market in weeks after notification."},

    # ── CANADA ────────────────────────────────────────────────────────────────
    {"name": "Food and Drugs Act (Canada)", "short_name": "FDA-CA",
     "jurisdiction": "canada", "domain": "pharma", "year": "1985", "status": "active",
     "description": "Core Canadian law for drugs (NOC pathway), devices (MDL), and food safety. Multiple regulations flow from this Act including NHPR and MDR."},
    {"name": "Natural Health Products Regulations", "short_name": "NHPR",
     "jurisdiction": "canada", "domain": "nutra", "year": "2004", "status": "active",
     "description": "Licenses natural health products (vitamins, minerals, herbs, homeopathics, TCM, Ayurveda) with NPN or DIN-HM numbers. Traditional use evidence accepted — no clinical trials required for most."},
    {"name": "Medical Devices Regulations SOR/98-282", "jurisdiction": "canada",
     "domain": "device", "year": "1998", "status": "active",
     "description": "Class I-IV device framework. Class II-IV require Medical Device License (MDL) from Health Canada. Mandatory problem reporting and device tracking requirements."},
    {"name": "Safe Food for Canadians Regulations", "short_name": "SFCR",
     "jurisdiction": "canada", "domain": "food", "year": "2019", "status": "active",
     "description": "Preventive controls, licensing, and traceability requirements for food businesses. Aligns with FSMA principles. Managed by CFIA."},

    # ── SINGAPORE ─────────────────────────────────────────────────────────────
    {"name": "Health Products Act", "jurisdiction": "singapore",
     "domain": "pharma", "year": "2007", "status": "active",
     "description": "Comprehensive law for therapeutic products, health supplements, medical devices, and cosmetics. Risk-proportionate framework with streamlined approval pathways."},
    {"name": "Health Products (Therapeutic Products) Regulations", "jurisdiction": "singapore",
     "domain": "pharma", "year": "2016", "status": "active",
     "description": "Registration, import, manufacture, and supply of therapeutic products. References foreign reference agency approvals (FDA, EMA, TGA) for expedited local review."},
    {"name": "Singapore Food Safety Standards", "jurisdiction": "singapore",
     "domain": "food", "year": "2020", "status": "active",
     "description": "Mandatory food safety standards under Sale of Food Act. Includes novel food framework (first approved lab-grown meat globally in 2020), food additives, and labeling requirements."},
    {"name": "Health Supplements Notification Framework", "jurisdiction": "singapore",
     "domain": "nutra", "year": "2011", "status": "active",
     "description": "Compliance-based system — no pre-market approval if ingredients comply with permitted list and claims rules. Among the fastest supplement launch pathways in Asia."},
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Clear existing
        from sqlalchemy import delete
        await db.execute(delete(Regulation))
        await db.execute(delete(RegulatoryBody))
        await db.commit()

        # Insert bodies
        body_objs = []
        for b in BODIES:
            obj = RegulatoryBody(**b)
            db.add(obj)
            body_objs.append(obj)
        await db.commit()
        print(f"✅ Seeded {len(body_objs)} regulatory bodies")

        # Insert regulations
        reg_objs = []
        for r in REGULATIONS:
            obj = Regulation(**r)
            db.add(obj)
            reg_objs.append(obj)
        await db.commit()
        print(f"✅ Seeded {len(reg_objs)} regulations")
        print("🎉 Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
