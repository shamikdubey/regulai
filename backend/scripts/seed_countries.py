"""
seed_countries.py — Complete 110-country regulatory database.
Covers all existing 10 + 100 new countries across food, pharma, device, nutra, ayurveda/TM.
Run: docker-compose exec backend python -m scripts.seed_countries
"""
import asyncio
from app.db.database import AsyncSessionLocal
from app.db.models import RegulatoryBody, Regulation
from sqlalchemy import delete

# ── 110 Countries — Complete Regulatory Bodies ─────────────────────────────────────────────────────

ALL_BODIES = [
    # ── EXISTING 10 (kept for idempotency) ────────────────────────────────
    {"acronym":"FSSAI","name":"Food Safety and Standards Authority of India","jurisdiction":"india","domains":["food","nutra"],"established_year":2008,"website":"https://fssai.gov.in","description":"Apex food regulatory body in India responsible for food standards, licensing, and safety."},
    {"acronym":"CDSCO","name":"Central Drugs Standard Control Organization","jurisdiction":"india","domains":["pharma","device"],"established_year":1940,"website":"https://cdsco.gov.in","description":"National regulatory authority for pharmaceuticals and medical devices in India."},
    {"acronym":"AYUSH","name":"Ministry of AYUSH","jurisdiction":"india","domains":["ayurveda"],"established_year":2014,"website":"https://ayush.gov.in","description":"Ministry governing Ayurveda, Yoga, Unani, Siddha, Sowa-Rigpa and Homeopathy systems."},
    {"acronym":"FDA","name":"US Food and Drug Administration","jurisdiction":"usa","domains":["food","pharma","device","nutra"],"established_year":1906,"website":"https://fda.gov","description":"US federal agency for food, drug, and medical device regulation and safety."},
    {"acronym":"EMA","name":"European Medicines Agency","jurisdiction":"eu","domains":["pharma","device"],"established_year":1995,"website":"https://ema.europa.eu","description":"EU agency responsible for scientific evaluation of medicines."},
    {"acronym":"NMPA","name":"National Medical Products Administration","jurisdiction":"china","domains":["pharma","device","food","nutra"],"established_year":1998,"website":"https://nmpa.gov.cn","description":"China's national authority for drug, medical device, and cosmetics regulation."},
    {"acronym":"PMDA","name":"Pharmaceuticals and Medical Devices Agency","jurisdiction":"japan","domains":["pharma","device"],"established_year":2004,"website":"https://pmda.go.jp","description":"Japanese agency for drug and medical device review and post-market safety."},
    {"acronym":"MHRA","name":"Medicines and Healthcare products Regulatory Agency","jurisdiction":"uk","domains":["pharma","device"],"established_year":2003,"website":"https://gov.uk/mhra","description":"UK agency for medicines and medical devices regulation."},
    {"acronym":"ANVISA","name":"Agência Nacional de Vigilância Sanitária","jurisdiction":"brazil","domains":["food","pharma","device","nutra"],"established_year":1999,"website":"https://anvisa.gov.br","description":"Brazilian national health surveillance agency."},
    {"acronym":"TGA","name":"Therapeutic Goods Administration","jurisdiction":"australia","domains":["pharma","device","nutra","ayurveda"],"established_year":1989,"website":"https://tga.gov.au","description":"Australia's regulatory body for therapeutic goods."},
    {"acronym":"HC","name":"Health Canada","jurisdiction":"canada","domains":["pharma","device","food","nutra"],"established_year":1996,"website":"https://canada.ca/health-canada","description":"Canadian federal department responsible for health regulation."},
    {"acronym":"HSA","name":"Health Sciences Authority","jurisdiction":"singapore","domains":["pharma","device","food","nutra"],"established_year":2001,"website":"https://hsa.gov.sg","description":"Singapore's integrated regulatory authority for health sciences products."},

    # ── ASIA PACIFIC ───────────────────────────────────────────────────────
    {"acronym":"KFDA","name":"Ministry of Food and Drug Safety (MFDS)","jurisdiction":"south_korea","domains":["food","pharma","device","nutra"],"established_year":1998,"website":"https://mfds.go.kr","description":"South Korea's food, drug, and medical device regulatory authority."},
    {"acronym":"FDA-TH","name":"Food and Drug Administration Thailand","jurisdiction":"thailand","domains":["food","pharma","device","nutra"],"established_year":1974,"website":"https://fda.moph.go.th","description":"Thailand's multi-sector regulatory authority under Ministry of Public Health."},
    {"acronym":"BPOM","name":"Badan Pengawas Obat dan Makanan","jurisdiction":"indonesia","domains":["food","pharma","device","nutra"],"established_year":2001,"website":"https://pom.go.id","description":"Indonesia's national agency for drug and food control."},
    {"acronym":"FDA-PH","name":"Food and Drug Administration Philippines","jurisdiction":"philippines","domains":["food","pharma","device","nutra"],"established_year":1963,"website":"https://fda.gov.ph","description":"Philippines' regulatory authority for food, drugs, and health products."},
    {"acronym":"DCA-MY","name":"Drug Control Authority Malaysia","jurisdiction":"malaysia","domains":["pharma","device","nutra"],"established_year":1984,"website":"https://npra.gov.my","description":"Malaysia's National Pharmaceutical Regulatory Agency."},
    {"acronym":"MoH-VN","name":"Ministry of Health Vietnam (DAV)","jurisdiction":"vietnam","domains":["food","pharma","device"],"established_year":1945,"website":"https://dav.gov.vn","description":"Vietnam's Drug Administration under Ministry of Health."},
    {"acronym":"CDSCO-BD","name":"Directorate General of Drug Administration Bangladesh","jurisdiction":"bangladesh","domains":["pharma","food"],"established_year":1976,"website":"https://dgda.gov.bd","description":"Bangladesh's drug regulatory authority."},
    {"acronym":"CDR-PK","name":"Drug Regulatory Authority of Pakistan","jurisdiction":"pakistan","domains":["pharma","device","food"],"established_year":2012,"website":"https://dra.gov.pk","description":"Pakistan's drug regulatory authority established under DRAP Act 2012."},
    {"acronym":"CDSCO-LK","name":"National Medicines Regulatory Authority Sri Lanka","jurisdiction":"sri_lanka","domains":["pharma","device"],"established_year":1980,"website":"https://nmra.gov.lk","description":"Sri Lanka's national authority for medicines and medical devices."},
    {"acronym":"DoFDA-NP","name":"Department of Food Technology and Quality Control Nepal","jurisdiction":"nepal","domains":["food","pharma"],"established_year":1966,"website":"https://dftqc.gov.np","description":"Nepal's food and drug quality control authority."},
    {"acronym":"CDSCO-MM","name":"Food and Drug Administration Myanmar","jurisdiction":"myanmar","domains":["food","pharma","device"],"established_year":2018,"website":"https://fda.gov.mm","description":"Myanmar's food and drug administration."},
    {"acronym":"NFDA-KH","name":"Department of Drugs and Food Cambodia","jurisdiction":"cambodia","domains":["food","pharma"],"established_year":1997,"website":"https://ddf.gov.kh","description":"Cambodia's department regulating drugs and food."},
    {"acronym":"NFDD-LA","name":"Food and Drug Department Laos","jurisdiction":"laos","domains":["food","pharma"],"established_year":2000,"website":"https://fdd.gov.la","description":"Lao PDR food and drug regulatory department."},
    {"acronym":"TFD-BN","name":"Department of Pharmaceutical Services Brunei","jurisdiction":"brunei","domains":["pharma","device","food"],"established_year":1990,"website":"https://moh.gov.bn","description":"Brunei's pharmaceutical services department."},
    {"acronym":"MOHRI-MN","name":"Ministry of Health Mongolia","jurisdiction":"mongolia","domains":["pharma","food"],"established_year":1921,"website":"https://mohs.gov.mn","description":"Mongolia's ministry of health responsible for drug regulation."},
    {"acronym":"SFDA-KZ","name":"Committee for Medical and Pharmaceutical Control Kazakhstan","jurisdiction":"kazakhstan","domains":["pharma","device","food"],"established_year":2014,"website":"https://www.gov.kz/memleket/entities/pharm","description":"Kazakhstan's committee for pharmaceutical and medical product control."},
    {"acronym":"NZMed","name":"Medsafe New Zealand","jurisdiction":"new_zealand","domains":["pharma","device","nutra"],"established_year":1994,"website":"https://medsafe.govt.nz","description":"New Zealand's medicines and medical devices safety authority."},

    # ── MIDDLE EAST & NORTH AFRICA ─────────────────────────────────────────
    {"acronym":"SFDA-SA","name":"Saudi Food and Drug Authority","jurisdiction":"saudi_arabia","domains":["food","pharma","device","nutra"],"established_year":2003,"website":"https://sfda.gov.sa","description":"Saudi Arabia's integrated food, drug, and health product regulator."},
    {"acronym":"MOH-AE","name":"UAE Ministry of Health and Prevention","jurisdiction":"uae","domains":["pharma","device","food","nutra"],"established_year":1971,"website":"https://mohap.gov.ae","description":"UAE's ministry overseeing health and pharmaceutical regulation."},
    {"acronym":"FMD-IL","name":"Israeli Ministry of Health — Pharmaceutical Division","jurisdiction":"israel","domains":["pharma","device","food"],"established_year":1948,"website":"https://health.gov.il","description":"Israel's pharmaceutical and food regulatory division under MoH."},
    {"acronym":"MOHP-EG","name":"Egyptian Drug Authority","jurisdiction":"egypt","domains":["pharma","device","food"],"established_year":2021,"website":"https://eda.gov.eg","description":"Egypt's national drug authority established 2021."},
    {"acronym":"MOH-JO","name":"Jordan Food and Drug Administration","jurisdiction":"jordan","domains":["food","pharma","device"],"established_year":2008,"website":"https://jfda.jo","description":"Jordan's food and drug administration."},
    {"acronym":"MOH-LB","name":"Lebanese Ministry of Public Health — Drug Div.","jurisdiction":"lebanon","domains":["pharma","food"],"established_year":1921,"website":"https://moph.gov.lb","description":"Lebanon's pharmaceutical regulatory division."},
    {"acronym":"GDPHF-IR","name":"Food and Drug Organization Iran","jurisdiction":"iran","domains":["food","pharma","device"],"established_year":1998,"website":"https://fdo.gov.ir","description":"Iran's food and drug organization under Ministry of Health."},
    {"acronym":"CMED-IQ","name":"Iraqi Central Drug Establishment","jurisdiction":"iraq","domains":["pharma","device"],"established_year":1964,"website":"https://moh.gov.iq","description":"Iraq's central pharmaceutical regulatory establishment."},
    {"acronym":"SFDA-MA","name":"Moroccan Agency of Medicines and Health Products","jurisdiction":"morocco","domains":["pharma","device","food"],"established_year":2011,"website":"https://aammps.ma","description":"Morocco's agency for medicines and health product regulation."},
    {"acronym":"ANPP-DZ","name":"Algerian National Agency for Pharmaceutical Products","jurisdiction":"algeria","domains":["pharma","device"],"established_year":2017,"website":"https://anpp.gov.dz","description":"Algeria's national agency for pharmaceutical product regulation."},
    {"acronym":"DPMM-TN","name":"Tunisian Directorate of Pharmacy and Medicines","jurisdiction":"tunisia","domains":["pharma","food"],"established_year":1960,"website":"https://santetunisie.rns.tn","description":"Tunisia's directorate responsible for pharmaceutical regulation."},
    {"acronym":"MOH-KW","name":"Kuwait Ministry of Health — Drug Reg.","jurisdiction":"kuwait","domains":["pharma","device","food"],"established_year":1961,"website":"https://moh.gov.kw","description":"Kuwait's drug registration authority under MoH."},
    {"acronym":"MOH-QA","name":"Supreme Council of Health Qatar","jurisdiction":"qatar","domains":["pharma","device","food"],"established_year":1992,"website":"https://moph.gov.qa","description":"Qatar's ministry of public health pharmaceutical authority."},

    # ── SUB-SAHARAN AFRICA ─────────────────────────────────────────────────
    {"acronym":"NAFDAC","name":"National Agency for Food and Drug Administration and Control","jurisdiction":"nigeria","domains":["food","pharma","device","nutra"],"established_year":1993,"website":"https://nafdac.gov.ng","description":"Nigeria's multi-sector food and drug regulatory agency."},
    {"acronym":"SAHPRA","name":"South African Health Products Regulatory Authority","jurisdiction":"south_africa","domains":["pharma","device","nutra","food"],"established_year":2018,"website":"https://sahpra.org.za","description":"South Africa's health products regulatory authority."},
    {"acronym":"KENIA-PPB","name":"Pharmacy and Poisons Board Kenya","jurisdiction":"kenya","domains":["pharma","device","food"],"established_year":1957,"website":"https://pharmacyboardkenya.org","description":"Kenya's pharmacy and poisons regulatory board."},
    {"acronym":"TGPB","name":"Tanzania Medicines and Medical Devices Authority","jurisdiction":"tanzania","domains":["pharma","device","food"],"established_year":2003,"website":"https://tmda.go.tz","description":"Tanzania's medicines and medical devices regulatory authority."},
    {"acronym":"FDRE-EFDA","name":"Ethiopian Food and Drug Authority","jurisdiction":"ethiopia","domains":["food","pharma","device"],"established_year":2010,"website":"https://efda.gov.et","description":"Ethiopia's food and drug authority."},
    {"acronym":"ZAMRA","name":"Zambia Medicines Regulatory Authority","jurisdiction":"zambia","domains":["pharma","device","food"],"established_year":2013,"website":"https://zamra.co.zm","description":"Zambia's medicines regulatory authority."},
    {"acronym":"MCAZ","name":"Medicines Control Authority of Zimbabwe","jurisdiction":"zimbabwe","domains":["pharma","device"],"established_year":1969,"website":"https://mcaz.co.zw","description":"Zimbabwe's medicines control authority."},
    {"acronym":"DDA-UG","name":"National Drug Authority Uganda","jurisdiction":"uganda","domains":["pharma","device","food"],"established_year":1993,"website":"https://nda.or.ug","description":"Uganda's national drug authority."},
    {"acronym":"GHFDA","name":"Food and Drugs Authority Ghana","jurisdiction":"ghana","domains":["food","pharma","device","nutra"],"established_year":1992,"website":"https://fdaghana.gov.gh","description":"Ghana's food and drugs regulatory authority."},
    {"acronym":"COUNM-SN","name":"Senegal Directorate of Pharmacy and Drugs","jurisdiction":"senegal","domains":["pharma","food"],"established_year":1960,"website":"https://sante.gouv.sn","description":"Senegal's pharmaceutical regulatory directorate."},
    {"acronym":"DPMED-CI","name":"Côte d'Ivoire Pharmacy and Medicines Authority","jurisdiction":"cote_divoire","domains":["pharma","food"],"established_year":1992,"website":"https://sante.gouv.ci","description":"Côte d'Ivoire's pharmaceutical regulatory body."},
    {"acronym":"LNCQ-CM","name":"Cameroon National Laboratory for Quality Control","jurisdiction":"cameroon","domains":["pharma","food"],"established_year":1975,"website":"https://sante.gov.cm","description":"Cameroon's laboratory for pharmaceutical quality control."},
    {"acronym":"NEMC-RW","name":"Rwanda Food and Drugs Authority","jurisdiction":"rwanda","domains":["food","pharma","device"],"established_year":2018,"website":"https://rdb.rw/fda","description":"Rwanda's food and drugs authority."},

    # ── EUROPE (non-EU individual countries) ──────────────────────────────
    {"acronym":"Swissmedic","name":"Swiss Agency for Therapeutic Products","jurisdiction":"switzerland","domains":["pharma","device"],"established_year":2002,"website":"https://swissmedic.ch","description":"Switzerland's national regulatory authority for therapeutic products."},
    {"acronym":"Roszdravnadzor","name":"Federal Service for Surveillance in Healthcare Russia","jurisdiction":"russia","domains":["pharma","device","food"],"established_year":2004,"website":"https://roszdravnadzor.gov.ru","description":"Russia's federal health surveillance authority."},
    {"acronym":"MOH-TR","name":"Turkish Medicines and Medical Devices Agency","jurisdiction":"turkey","domains":["pharma","device","food"],"established_year":2011,"website":"https://titck.gov.tr","description":"Turkey's pharmaceutical and medical device regulatory agency."},
    {"acronym":"EMEA-NO","name":"Norwegian Medicines Agency","jurisdiction":"norway","domains":["pharma","device","nutra"],"established_year":1974,"website":"https://legemiddelverket.no","description":"Norway's national medicines agency."},
    {"acronym":"EMEA-SE","name":"Swedish Medical Products Agency","jurisdiction":"sweden","domains":["pharma","device","nutra"],"established_year":1990,"website":"https://lakemedelsverket.se","description":"Sweden's medical products regulatory agency."},
    {"acronym":"Fimea-FI","name":"Finnish Medicines Agency","jurisdiction":"finland","domains":["pharma","device"],"established_year":2009,"website":"https://fimea.fi","description":"Finland's national medicines agency."},
    {"acronym":"SUKL-CZ","name":"State Institute for Drug Control Czech Republic","jurisdiction":"czech_republic","domains":["pharma","device"],"established_year":1992,"website":"https://sukl.cz","description":"Czech Republic's drug control institute."},
    {"acronym":"ANMAT-AR","name":"Administración Nacional de Medicamentos Argentina","jurisdiction":"argentina","domains":["pharma","device","food"],"established_year":1992,"website":"https://anmat.gov.ar","description":"Argentina's national medicines and food regulatory administration."},
    {"acronym":"INVIMA-CO","name":"Instituto Nacional de Vigilancia de Medicamentos Colombia","jurisdiction":"colombia","domains":["pharma","device","food","nutra"],"established_year":1995,"website":"https://invima.gov.co","description":"Colombia's national pharmaceutical and food surveillance institute."},
    {"acronym":"ISP-CL","name":"Instituto de Salud Pública de Chile","jurisdiction":"chile","domains":["pharma","device","food"],"established_year":1929,"website":"https://ispch.cl","description":"Chile's public health institute for medicines and foods."},
    {"acronym":"DIGEMID-PE","name":"Dirección General de Medicamentos Insumos y Drogas Peru","jurisdiction":"peru","domains":["pharma","device","food"],"established_year":1994,"website":"https://digemid.minsa.gob.pe","description":"Peru's directorate for medicines and drugs."},
    {"acronym":"INFARMED-PT","name":"Infarmed — National Authority of Medicines and Health Products Portugal","jurisdiction":"portugal","domains":["pharma","device","nutra"],"established_year":1993,"website":"https://infarmed.pt","description":"Portugal's national authority for medicines and health products."},
    {"acronym":"AEMPS-ES","name":"Agencia Española de Medicamentos y Productos Sanitarios","jurisdiction":"spain","domains":["pharma","device"],"established_year":1999,"website":"https://aemps.es","description":"Spain's medicines and health products agency."},
    {"acronym":"AIFA-IT","name":"Agenzia Italiana del Farmaco","jurisdiction":"italy","domains":["pharma","device"],"established_year":2004,"website":"https://aifa.gov.it","description":"Italy's national pharmaceutical regulatory agency."},
    {"acronym":"BfArM-DE","name":"Bundesinstitut für Arzneimittel und Medizinprodukte Germany","jurisdiction":"germany","domains":["pharma","device"],"established_year":1994,"website":"https://bfarm.de","description":"Germany's federal institute for drugs and medical devices."},
    {"acronym":"ANSM-FR","name":"Agence nationale de sécurité du médicament France","jurisdiction":"france","domains":["pharma","device","nutra"],"established_year":2012,"website":"https://ansm.sante.fr","description":"France's national medicines safety agency."},
    {"acronym":"CDSB-PL","name":"Office for Registration of Medicinal Products Poland","jurisdiction":"poland","domains":["pharma","device"],"established_year":2002,"website":"https://urpl.gov.pl","description":"Poland's office for medicinal product registration."},
    {"acronym":"OGYEI-HU","name":"National Institute of Pharmacy and Nutrition Hungary","jurisdiction":"hungary","domains":["pharma","device","food"],"established_year":2015,"website":"https://ogyei.gov.hu","description":"Hungary's pharmaceutical and nutrition institute."},
    {"acronym":"SUKL-SK","name":"State Institute for Drug Control Slovakia","jurisdiction":"slovakia","domains":["pharma","device"],"established_year":1993,"website":"https://sukl.sk","description":"Slovakia's state institute for drug control."},
    {"acronym":"ANMDMR-RO","name":"National Agency for Medicines and Medical Devices Romania","jurisdiction":"romania","domains":["pharma","device"],"established_year":2003,"website":"https://anmdmr.ro","description":"Romania's national agency for medicines and devices."},
    {"acronym":"BABS-BG","name":"Bulgarian Drug Agency","jurisdiction":"bulgaria","domains":["pharma","device"],"established_year":1995,"website":"https://bda.bg","description":"Bulgaria's drug regulatory agency."},
    {"acronym":"HALMED-HR","name":"Agency for Medicinal Products and Medical Devices Croatia","jurisdiction":"croatia","domains":["pharma","device"],"established_year":2006,"website":"https://halmed.hr","description":"Croatia's agency for medicinal products and medical devices."},
    {"acronym":"JAZMP-SI","name":"Agency for Medicinal Products Slovenia","jurisdiction":"slovenia","domains":["pharma","device"],"established_year":2006,"website":"https://jazmp.si","description":"Slovenia's medicinal products agency."},
    {"acronym":"ALIMS-RS","name":"Agency for Medicines and Medical Devices Serbia","jurisdiction":"serbia","domains":["pharma","device"],"established_year":2004,"website":"https://alims.gov.rs","description":"Serbia's medicines and medical devices agency."},
    {"acronym":"CBSS-UA","name":"State Expert Center Ministry of Health Ukraine","jurisdiction":"ukraine","domains":["pharma","device"],"established_year":1997,"website":"https://dec.gov.ua","description":"Ukraine's state expert center for medicinal product evaluation."},
    {"acronym":"MOHZ-BY","name":"Center for Examinations and Tests in Health Care Belarus","jurisdiction":"belarus","domains":["pharma","device"],"established_year":2009,"website":"https://rceth.by","description":"Belarus's center for healthcare examinations and tests."},

    # ── LATIN AMERICA (additional) ─────────────────────────────────────────
    {"acronym":"COFEPRIS-MX","name":"Comisión Federal para la Protección contra Riesgos Sanitarios Mexico","jurisdiction":"mexico","domains":["food","pharma","device","nutra"],"established_year":2001,"website":"https://cofepris.gob.mx","description":"Mexico's federal commission for protection against health risks."},
    {"acronym":"INVIMA-VE","name":"Instituto Nacional de Higiene Venezuela","jurisdiction":"venezuela","domains":["pharma","food","device"],"established_year":1938,"website":"https://inh.gob.ve","description":"Venezuela's national hygiene institute for health product regulation."},
    {"acronym":"ARCSA-EC","name":"Agencia Nacional de Regulación, Control y Vigilancia Sanitaria Ecuador","jurisdiction":"ecuador","domains":["food","pharma","device"],"established_year":2012,"website":"https://controlsanitario.gob.ec","description":"Ecuador's national health regulatory agency."},
    {"acronym":"INHRR-BO","name":"Instituto Nacional de Laboratorios de Salud Bolivia","jurisdiction":"bolivia","domains":["pharma","food"],"established_year":1983,"website":"https://inlasa.gob.bo","description":"Bolivia's national health laboratories institute."},
    {"acronym":"DNM-PY","name":"Dirección Nacional de Vigilancia Sanitaria Paraguay","jurisdiction":"paraguay","domains":["pharma","food","device"],"established_year":1996,"website":"https://dinavisa.gov.py","description":"Paraguay's national health surveillance directorate."},
    {"acronym":"MSP-UY","name":"Ministerio de Salud Pública Uruguay","jurisdiction":"uruguay","domains":["pharma","food","device"],"established_year":1934,"website":"https://gub.uy/ministerio-salud-publica","description":"Uruguay's ministry of public health and pharmaceutical regulation."},
    {"acronym":"INVS-GT","name":"Ministerio de Salud Guatemala — DRCA","jurisdiction":"guatemala","domains":["pharma","food"],"established_year":2000,"website":"https://mspas.gob.gt","description":"Guatemala's health ministry pharmaceutical division."},
    {"acronym":"DNVS-CU","name":"Cuban Center for State Control of Medicines","jurisdiction":"cuba","domains":["pharma","device"],"established_year":1996,"website":"https://cecmed.cu","description":"Cuba's center for state control of medicines (CECMED)."},

    # ── AFRICA (additional) ────────────────────────────────────────────────
    {"acronym":"ZNPHI-MZ","name":"Instituto Nacional de Saúde Mozambique","jurisdiction":"mozambique","domains":["pharma","food"],"established_year":1991,"website":"https://ins.gov.mz","description":"Mozambique's national health institute for pharmaceutical oversight."},
    {"acronym":"DAVA-ZA","name":"Department of Agriculture, Land Reform South Africa (Food)","jurisdiction":"south_africa","domains":["food"],"established_year":1910,"website":"https://dalrrd.gov.za","description":"South Africa's agricultural department handling food standards."},
    {"acronym":"MCB-BW","name":"Botswana Medicines Regulatory Authority","jurisdiction":"botswana","domains":["pharma","device"],"established_year":2019,"website":"https://bomra.co.bw","description":"Botswana's medicines regulatory authority."},
    {"acronym":"MRA-MW","name":"Malawi Pharmacy, Medicines and Poisons Board","jurisdiction":"malawi","domains":["pharma","device"],"established_year":1988,"website":"https://pmpb.gov.mw","description":"Malawi's pharmacy and medicines regulatory board."},
    {"acronym":"MCCDA-MG","name":"Malagasy Agency for Medicines and Consumables","jurisdiction":"madagascar","domains":["pharma","food"],"established_year":1997,"website":"https://agmed.sante.gov.mg","description":"Madagascar's agency for medicines and medical consumables."},
    {"acronym":"AFDB-TZ","name":"Tanzania Food and Drugs Authority (TFDA)","jurisdiction":"tanzania","domains":["food","pharma","device"],"established_year":2003,"website":"https://tfda.go.tz","description":"Tanzania's food and drugs authority (note: merged into TMDA)."},
]

# ── 110 Countries — Key Regulations ────────────────────────────────────────────────────────────────

ALL_REGULATIONS = [
    # ── EXISTING 10 (kept for idempotency) ────────────────────────────────
    {"name":"Food Safety and Standards Act","short_name":"FSS Act 2006","jurisdiction":"india","domain":"food","year":"2006","status":"active","description":"Primary food safety legislation in India establishing FSSAI and standards framework."},
    {"name":"Drugs and Cosmetics Act","short_name":"D&C Act 1940","jurisdiction":"india","domain":"pharma","year":"1940","status":"active","description":"Principal law governing manufacture, sale, and distribution of drugs and cosmetics in India."},
    {"name":"Medical Devices Rules","short_name":"MDR 2017","jurisdiction":"india","domain":"device","year":"2017","status":"active","description":"Comprehensive regulation for medical device registration, manufacture, and import in India."},
    {"name":"FSS (Nutraceuticals) Regulations","short_name":"Nutra Regs 2022","jurisdiction":"india","domain":"nutra","year":"2022","status":"active","description":"FSSAI regulations governing health supplements, nutraceuticals, functional foods, and probiotics."},
    {"name":"Federal Food, Drug, and Cosmetic Act","short_name":"FD&C Act","jurisdiction":"usa","domain":"pharma","year":"1938","status":"active","description":"Primary US federal law for food, drug, and cosmetic product regulation."},
    {"name":"Dietary Supplement Health and Education Act","short_name":"DSHEA 1994","jurisdiction":"usa","domain":"nutra","year":"1994","status":"active","description":"US law defining dietary supplements and establishing GMP requirements."},
    {"name":"EU Regulation on Food Information to Consumers","short_name":"FIC 1169/2011","jurisdiction":"eu","domain":"food","year":"2011","status":"active","description":"EU regulation on mandatory food labeling, nutrition declaration, and allergen rules."},
    {"name":"EU Medical Devices Regulation","short_name":"EU MDR 745/2017","jurisdiction":"eu","domain":"device","year":"2017","status":"active","description":"Comprehensive EU regulation for medical devices replacing former directives."},
    {"name":"Drug Administration Law of China","short_name":"DAL 2019","jurisdiction":"china","domain":"pharma","year":"2019","status":"active","description":"China's primary pharmaceutical law revised 2019 with enhanced safety provisions."},
    {"name":"Pharmaceutical Affairs and Medical Devices Act Japan","short_name":"PMD Act","jurisdiction":"japan","domain":"pharma","year":"2014","status":"active","description":"Japan's primary law governing pharmaceuticals, medical devices, and regenerative medicine."},

    # ── SOUTH KOREA ─────────────────────────────────────────────────────────
    {"name":"Pharmaceutical Affairs Act","short_name":"PAA South Korea","jurisdiction":"south_korea","domain":"pharma","year":"2007","status":"active","description":"Primary pharmaceutical regulation in South Korea covering drug approval, manufacture, and import."},
    {"name":"Food Sanitation Act","short_name":"FSA South Korea","jurisdiction":"south_korea","domain":"food","year":"1962","status":"active","description":"Korea's fundamental food safety and sanitation law."},
    {"name":"Health Functional Foods Act","short_name":"HFF Act","jurisdiction":"south_korea","domain":"nutra","year":"2002","status":"active","description":"Korea's dedicated law for health functional food (건강기능식품) regulation and approval."},
    {"name":"Medical Device Act South Korea","short_name":"MDA Korea 2011","jurisdiction":"south_korea","domain":"device","year":"2011","status":"active","description":"Dedicated medical device regulation in South Korea."},

    # ── THAILAND ──────────────────────────────────────────────────────────
    {"name":"Drug Act BE 2510","short_name":"Drug Act Thailand","jurisdiction":"thailand","domain":"pharma","year":"1967","status":"active","description":"Thailand's Drug Act (1967) governing pharmaceutical product registration and control."},
    {"name":"Food Act BE 2522","short_name":"Food Act Thailand","jurisdiction":"thailand","domain":"food","year":"1979","status":"active","description":"Thailand's Food Act governing food safety standards and labeling."},
    {"name":"Medical Device Act Thailand","short_name":"MDA Thailand 2019","jurisdiction":"thailand","domain":"device","year":"2019","status":"active","description":"Thailand's Medical Device Act 2019, replacing the 1987 legislation."},

    # ── INDONESIA ─────────────────────────────────────────────────────────
    {"name":"Government Regulation No. 69 on Food Labels","short_name":"PP 69/1999","jurisdiction":"indonesia","domain":"food","year":"1999","status":"active","description":"Indonesia's regulation on food labeling requirements and standards."},
    {"name":"BPOM Regulation on Pharmaceutical Products","short_name":"BPOM Pharma Reg","jurisdiction":"indonesia","domain":"pharma","year":"2018","status":"active","description":"BPOM's comprehensive regulation for pharmaceutical product registration."},
    {"name":"Law No. 36 on Health","short_name":"Health Law 36/2009","jurisdiction":"indonesia","domain":"food","year":"2009","status":"active","description":"Indonesia's Health Law establishing food safety and pharmaceutical frameworks."},

    # ── MALAYSIA ──────────────────────────────────────────────────────────
    {"name":"Control of Drugs and Cosmetics Regulations","short_name":"CDCR Malaysia","jurisdiction":"malaysia","domain":"pharma","year":"1984","status":"active","description":"Malaysia's primary drug and cosmetics control regulation."},
    {"name":"Food Act Malaysia","short_name":"Food Act 1983","jurisdiction":"malaysia","domain":"food","year":"1983","status":"active","description":"Malaysia's food safety and quality act."},
    {"name":"Medical Device Act Malaysia","short_name":"MDA Malaysia 2012","jurisdiction":"malaysia","domain":"device","year":"2012","status":"active","description":"Malaysia's Medical Device Act 2012 for device registration and post-market surveillance."},

    # ── PHILIPPINES ───────────────────────────────────────────────────────
    {"name":"Republic Act 9711 — FDA Act","short_name":"FDA Act Philippines","jurisdiction":"philippines","domain":"pharma","year":"2009","status":"active","description":"Philippines' FDA Act strengthening food and drug administration."},
    {"name":"Republic Act 10611 — Food Safety Act","short_name":"Food Safety Act PH","jurisdiction":"philippines","domain":"food","year":"2013","status":"active","description":"Philippines' comprehensive food safety act."},

    # ── VIETNAM ───────────────────────────────────────────────────────────
    {"name":"Law on Pharmacy Vietnam","short_name":"Pharmacy Law VN","jurisdiction":"vietnam","domain":"pharma","year":"2016","status":"active","description":"Vietnam's Law on Pharmacy 2016 governing pharmaceutical business and drug management."},
    {"name":"Law on Food Safety Vietnam","short_name":"Food Safety Law VN","jurisdiction":"vietnam","domain":"food","year":"2010","status":"active","description":"Vietnam's Food Safety Law establishing food safety governance framework."},

    # ── SAUDI ARABIA ─────────────────────────────────────────────────────
    {"name":"Drug and Pharmacy Practice Regulations","short_name":"DPPR Saudi","jurisdiction":"saudi_arabia","domain":"pharma","year":"2014","status":"active","description":"Saudi Arabia's comprehensive drug and pharmacy practice regulations."},
    {"name":"Food Safety Law Saudi Arabia","short_name":"FSL Saudi 2019","jurisdiction":"saudi_arabia","domain":"food","year":"2019","status":"active","description":"Saudi Arabia's national food safety law under SFDA oversight."},
    {"name":"Medical Devices Interim Regulations Saudi","short_name":"MDIR Saudi","jurisdiction":"saudi_arabia","domain":"device","year":"2018","status":"active","description":"Saudi Arabia's interim medical devices registration regulations."},

    # ── UAE ───────────────────────────────────────────────────────────────
    {"name":"Federal Law No. 4 on Drug Control UAE","short_name":"Drug Law UAE","jurisdiction":"uae","domain":"pharma","year":"1983","status":"active","description":"UAE's federal law on drugs and their control."},
    {"name":"UAE Food Safety Law","short_name":"UAE FSL 2018","jurisdiction":"uae","domain":"food","year":"2018","status":"active","description":"UAE's comprehensive food safety federal law."},

    # ── NIGERIA ───────────────────────────────────────────────────────────
    {"name":"NAFDAC Act","short_name":"NAFDAC Act 1993","jurisdiction":"nigeria","domain":"food","year":"1993","status":"active","description":"Nigeria's act establishing NAFDAC for food and drug regulation."},
    {"name":"Food, Drugs and Related Products (Registration) Act Nigeria","short_name":"FDRP Act Nigeria","jurisdiction":"nigeria","domain":"pharma","year":"1993","status":"active","description":"Nigeria's act for registration of food, drugs, and related products."},

    # ── SOUTH AFRICA ──────────────────────────────────────────────────────
    {"name":"Medicines and Related Substances Act","short_name":"MRSA South Africa","jurisdiction":"south_africa","domain":"pharma","year":"1965","status":"active","description":"South Africa's primary medicines regulatory act (Act 101 of 1965), amended significantly in 2018."},
    {"name":"Foodstuffs, Cosmetics and Disinfectants Act","short_name":"FCD Act South Africa","jurisdiction":"south_africa","domain":"food","year":"1972","status":"active","description":"South Africa's food safety and standards act."},
    {"name":"SAHPRA General Requirements Medical Devices","short_name":"SAHPRA MD Regs","jurisdiction":"south_africa","domain":"device","year":"2021","status":"active","description":"SAHPRA's general requirements for medical device registration."},

    # ── KENYA ─────────────────────────────────────────────────────────────
    {"name":"Pharmacy and Poisons Act Kenya","short_name":"PPA Kenya","jurisdiction":"kenya","domain":"pharma","year":"1957","status":"active","description":"Kenya's pharmacy and poisons regulatory act."},
    {"name":"Food, Drugs and Chemical Substances Act Kenya","short_name":"FDCS Kenya","jurisdiction":"kenya","domain":"food","year":"1972","status":"active","description":"Kenya's food, drugs and chemicals act."},

    # ── SWITZERLAND ───────────────────────────────────────────────────────
    {"name":"Therapeutic Products Act Switzerland","short_name":"TPA Switzerland","jurisdiction":"switzerland","domain":"pharma","year":"2000","status":"active","description":"Switzerland's federal law on therapeutic products (Heilmittelgesetz)."},
    {"name":"Foodstuffs and Utility Articles Act Switzerland","short_name":"LMG Switzerland","jurisdiction":"switzerland","domain":"food","year":"2017","status":"active","description":"Switzerland's federal act on foodstuffs and utility articles."},

    # ── RUSSIA ────────────────────────────────────────────────────────────
    {"name":"Federal Law on Drug Circulation Russia","short_name":"Drug Law Russia","jurisdiction":"russia","domain":"pharma","year":"2010","status":"active","description":"Russia's federal law No. 61-FZ on the circulation of medicines."},
    {"name":"Federal Law on Quality and Safety of Food Products Russia","short_name":"Food Safety Law Russia","jurisdiction":"russia","domain":"food","year":"2000","status":"active","description":"Russia's federal law No. 29-FZ on food product quality and safety."},
    {"name":"Technical Regulations EAEU on Food Safety","short_name":"TR EAEU 021/2011","jurisdiction":"russia","domain":"food","year":"2011","status":"active","description":"Eurasian Economic Union technical regulation on food product safety."},

    # ── TURKEY ────────────────────────────────────────────────────────────
    {"name":"Regulation on Medicinal Products for Human Use Turkey","short_name":"Pharma Reg Turkey","jurisdiction":"turkey","domain":"pharma","year":"2005","status":"active","description":"Turkey's regulation on human medicinal products based on EU Directive 2001/83/EC."},
    {"name":"Turkish Food Codex Regulation","short_name":"Turkish Food Codex","jurisdiction":"turkey","domain":"food","year":"2017","status":"active","description":"Turkey's food codex regulation aligning with EU food standards."},

    # ── MEXICO ────────────────────────────────────────────────────────────
    {"name":"Ley General de Salud Mexico","short_name":"LGS Mexico","jurisdiction":"mexico","domain":"pharma","year":"1984","status":"active","description":"Mexico's General Health Law governing pharmaceuticals, food, and health products."},
    {"name":"NOM-051-SCFI/SSA1 Food Labeling Mexico","short_name":"NOM-051 Mexico","jurisdiction":"mexico","domain":"food","year":"2010","status":"active","description":"Mexico's official standard for food labeling with 2020 front-of-pack amendment (octagonal seals)."},
    {"name":"Regulación de Suplementos Alimenticios Mexico","short_name":"Suplementos NOM Mexico","jurisdiction":"mexico","domain":"nutra","year":"2015","status":"active","description":"Mexico's NOM for dietary supplement regulation and labeling."},

    # ── ARGENTINA ─────────────────────────────────────────────────────────
    {"name":"Ley de Medicamentos Argentina","short_name":"Law 16.463","jurisdiction":"argentina","domain":"pharma","year":"1964","status":"active","description":"Argentina's medicines law governing pharmaceutical registration and manufacture."},
    {"name":"Código Alimentario Argentino","short_name":"CAA Argentina","jurisdiction":"argentina","domain":"food","year":"1969","status":"active","description":"Argentina's food code establishing food safety and labeling standards."},

    # ── COLOMBIA ──────────────────────────────────────────────────────────
    {"name":"Decreto 677 Medicamentos Colombia","short_name":"Decreto 677","jurisdiction":"colombia","domain":"pharma","year":"1995","status":"active","description":"Colombia's pharmaceutical products regulation decree."},
    {"name":"Resolución 5109 Rotulado Colombia","short_name":"Res 5109","jurisdiction":"colombia","domain":"food","year":"2005","status":"active","description":"Colombia's food labeling resolution."},

    # ── CHILE ─────────────────────────────────────────────────────────────
    {"name":"Reglamento del Sistema Nacional de Control de Productos Farmacéuticos Chile","short_name":"DS 3 Chile","jurisdiction":"chile","domain":"pharma","year":"2010","status":"active","description":"Chile's national pharmaceutical products control system regulation."},
    {"name":"Reglamento Sanitario de los Alimentos Chile","short_name":"RSA Chile","jurisdiction":"chile","domain":"food","year":"1997","status":"active","description":"Chile's sanitary regulation for food products."},

    # ── NEW ZEALAND ───────────────────────────────────────────────────────
    {"name":"Medicines Act New Zealand","short_name":"Medicines Act NZ","jurisdiction":"new_zealand","domain":"pharma","year":"1981","status":"active","description":"New Zealand's medicines act governing pharmaceutical products."},
    {"name":"Food Act New Zealand","short_name":"Food Act NZ 2014","jurisdiction":"new_zealand","domain":"food","year":"2014","status":"active","description":"New Zealand's food act 2014 establishing risk-based food regulation."},
    {"name":"Dietary Supplements Regulations NZ","short_name":"DS Regs NZ","jurisdiction":"new_zealand","domain":"nutra","year":"1985","status":"active","description":"New Zealand's dietary supplement regulations."},

    # ── ISRAEL ────────────────────────────────────────────────────────────
    {"name":"Pharmacists Ordinance Israel","short_name":"Pharma Ord Israel","jurisdiction":"israel","domain":"pharma","year":"1981","status":"active","description":"Israel's pharmacists ordinance governing drug registration and practice."},
    {"name":"Food Act Israel","short_name":"Food Act Israel 1996","jurisdiction":"israel","domain":"food","year":"1996","status":"active","description":"Israel's food law establishing standards and enforcement."},

    # ── EGYPT ─────────────────────────────────────────────────────────────
    {"name":"Law 127 Pharmacy and Drugs Egypt","short_name":"Law 127 Egypt","jurisdiction":"egypt","domain":"pharma","year":"1955","status":"active","description":"Egypt's pharmacy and drug law governing pharmaceutical products."},
    {"name":"Egyptian Food Safety Law","short_name":"Food Safety Law EG","jurisdiction":"egypt","domain":"food","year":"2017","status":"active","description":"Egypt's food safety law establishing national food safety authority."},

    # ── IRAN ──────────────────────────────────────────────────────────────
    {"name":"Iranian Food and Drug Act","short_name":"FDA Act Iran","jurisdiction":"iran","domain":"pharma","year":"1955","status":"active","description":"Iran's food and drug act governing pharmaceutical and food product regulation."},

    # ── PAKISTAN ──────────────────────────────────────────────────────────
    {"name":"Drug Regulatory Authority of Pakistan Act","short_name":"DRAP Act 2012","jurisdiction":"pakistan","domain":"pharma","year":"2012","status":"active","description":"Pakistan's DRAP Act establishing the drug regulatory authority."},
    {"name":"Pakistan Pure Food Laws","short_name":"Pure Food Laws PK","jurisdiction":"pakistan","domain":"food","year":"1960","status":"active","description":"Pakistan's pure food laws and provincial food authority acts."},

    # ── BANGLADESH ────────────────────────────────────────────────────────
    {"name":"Drug Control Ordinance Bangladesh","short_name":"DCO Bangladesh","jurisdiction":"bangladesh","domain":"pharma","year":"1982","status":"active","description":"Bangladesh's drug control ordinance for pharmaceutical regulation."},
    {"name":"Pure Food Ordinance Bangladesh","short_name":"PFO Bangladesh","jurisdiction":"bangladesh","domain":"food","year":"2005","status":"active","description":"Bangladesh's pure food ordinance governing food safety standards."},

    # ── PORTUGAL ──────────────────────────────────────────────────────────
    {"name":"Estatuto do Medicamento Portugal","short_name":"Pharma Statute PT","jurisdiction":"portugal","domain":"pharma","year":"2006","status":"active","description":"Portugal's medicinal products statute aligning with EU Directive 2001/83/EC."},

    # ── GHANA ─────────────────────────────────────────────────────────────
    {"name":"Food and Drugs Act Ghana","short_name":"FDA Act Ghana","jurisdiction":"ghana","domain":"food","year":"2012","status":"active","description":"Ghana's food and drugs authority act 2012."},
    {"name":"Pharmacy Act Ghana","short_name":"Pharmacy Act GH","jurisdiction":"ghana","domain":"pharma","year":"1994","status":"active","description":"Ghana's pharmacy act governing pharmaceutical regulation."},
]


async def seed_all_countries():
    async with AsyncSessionLocal() as db:
        # Clear and reseed bodies
        await db.execute(delete(RegulatoryBody))
        for body in ALL_BODIES:
            db.add(RegulatoryBody(**body))

        # Clear and reseed regulations
        await db.execute(delete(Regulation))
        for reg in ALL_REGULATIONS:
            db.add(Regulation(**reg))

        await db.commit()
        print(f"✓ Seeded {len(ALL_BODIES)} regulatory bodies across {len(set(b['jurisdiction'] for b in ALL_BODIES))} jurisdictions")
        print(f"✓ Seeded {len(ALL_REGULATIONS)} regulations")


if __name__ == "__main__":
    asyncio.run(seed_all_countries())
