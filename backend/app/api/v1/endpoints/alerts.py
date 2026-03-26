"""
Regulatory Change Alerts endpoint.
Tracks and surfaces recent/upcoming regulatory changes per jurisdiction + domain.
In production this is fed by a weekly scraper pipeline. 
Here we provide the schema + a seeded alert set + the subscription management API.
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.db.database import get_db, Base
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()


# ── Model ─────────────────────────────────────────────────────────────────────

class RegulatoryAlert(Base):
    __tablename__ = "regulatory_alerts"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)   # NEW / AMENDED / UPCOMING / ENFORCEMENT
    severity: Mapped[str] = mapped_column(String(20), default="medium")    # high / medium / low
    effective_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    regulatory_body: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    jurisdictions: Mapped[list] = mapped_column(JSON, default=list)
    domains: Mapped[list] = mapped_column(JSON, default=list)
    severity_threshold: Mapped[str] = mapped_column(String(20), default="medium")
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── Schemas ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: UUID
    title: str
    summary: str
    jurisdiction: str
    domain: str
    change_type: str
    severity: str
    effective_date: Optional[str]
    source_url: Optional[str]
    regulatory_body: Optional[str]
    action_required: Optional[str]
    tags: Optional[list]
    published_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    jurisdictions: List[str] = []
    domains: List[str] = []
    severity_threshold: str = "medium"
    email_enabled: bool = True


# ── Seeded alerts (production feeds from scraper pipeline) ────────────────────

SEED_ALERTS = [
    {"title": "FSSAI: New Nutraceuticals & Health Supplements Regulations Fully Enforced",
     "summary": "FSSAI's FSS (Health Supplements, Nutraceuticals…) Regulations 2022 are now being actively enforced. Products without compliant labeling, including updated ingredient disclosures and revised claim language, face recall action. Companies must audit all existing labels against Schedule requirements.",
     "jurisdiction": "india", "domain": "nutra", "change_type": "ENFORCEMENT",
     "severity": "high", "effective_date": "2024-01-01", "regulatory_body": "FSSAI",
     "action_required": "Audit all nutraceutical labels against FSS (Nutraceuticals) Regulations 2022 Schedule I-IV. Update ingredient lists and claims language. Re-register non-compliant products.",
     "source_url": "https://fssai.gov.in", "tags": ["labeling", "nutraceuticals", "enforcement"]},

    {"title": "CDSCO: Medical Devices (Amendment) Rules 2024 — Expanded Device Scope",
     "summary": "CDSCO has expanded the list of notified medical devices bringing several previously unregulated categories under Class A or B registration. Affected categories include certain wellness wearables, digital health apps meeting SaMD criteria, and imported diagnostic kits.",
     "jurisdiction": "india", "domain": "device", "change_type": "AMENDED",
     "severity": "high", "effective_date": "2024-06-01", "regulatory_body": "CDSCO",
     "action_required": "Check whether your device category is newly notified. If so, apply for Class A/B registration via SUGAM portal before the 12-month grace period expires.",
     "source_url": "https://cdsco.gov.in", "tags": ["medical-devices", "SaMD", "wearables"]},

    {"title": "EU MDR: Transition Deadline Extended for Legacy Devices (2025)",
     "summary": "The European Commission has extended the MDR transition deadline for certain legacy Class IIb and III devices under strict conditions. Devices must have a valid MDD certificate and a signed Notified Body contract by 26 May 2024 to qualify for the extension to 2026-2027.",
     "jurisdiction": "eu", "domain": "device", "change_type": "AMENDED",
     "severity": "high", "effective_date": "2024-05-26", "regulatory_body": "EC / Notified Bodies",
     "action_required": "Verify your device's eligibility for the extension. If eligible, ensure NB contract is signed and Annex IX/X audit scheduled. If not eligible, accelerate MDR conformity assessment immediately.",
     "source_url": "https://ec.europa.eu/health/md_topics-art_35_en", "tags": ["MDR", "transition", "legacy-devices"]},

    {"title": "FDA: Final Rule on Laboratory Developed Tests (LDTs) — IVD Reclassification",
     "summary": "FDA issued a final rule bringing laboratory developed tests (LDTs) under full FDA oversight as in vitro diagnostics. This ends the longstanding enforcement discretion policy. Labs have 4 years to comply with applicable premarket review requirements.",
     "jurisdiction": "usa", "domain": "device", "change_type": "NEW",
     "severity": "high", "effective_date": "2024-05-06", "regulatory_body": "FDA/CDRH",
     "action_required": "Inventory all LDTs. Determine classification (Class I/II/III). Begin 510(k) or PMA preparation for Class II/III LDTs. Phase 1 compliance (GMPs) due within 1 year.",
     "source_url": "https://www.fda.gov/medical-devices/vitro-diagnostics/laboratory-developed-tests", "tags": ["LDT", "IVD", "FDA", "reclassification"]},

    {"title": "AYUSH: Draft Guidelines for Ayurvedic Classical Medicines Export Certification",
     "summary": "Ministry of AYUSH released draft guidelines for a unified export certification framework for classical Ayurvedic medicines. The framework proposes a single-window clearance integrating CDSCO import permit requirements of destination countries with AYUSH quality certification.",
     "jurisdiction": "india", "domain": "ayurveda", "change_type": "UPCOMING",
     "severity": "medium", "effective_date": "2025-Q1 (expected)", "regulatory_body": "AYUSH Ministry",
     "action_required": "Submit comments during public consultation period. Begin preparing documentation for unified certification. Engage with AYUSH Export Promotion Council.",
     "source_url": "https://ayush.gov.in", "tags": ["export", "classical-medicines", "certification"]},

    {"title": "Japan: FFC System — Updated Substantiation Requirements for Gut Health Claims",
     "summary": "Consumer Affairs Agency (CAA) revised substantiation standards for gut microbiome-related health claims under the Food with Function Claims (FFC) system. New guidance requires meta-analysis level evidence for probiotic strain-specific claims, affecting hundreds of existing notifications.",
     "jurisdiction": "japan", "domain": "nutra", "change_type": "AMENDED",
     "severity": "medium", "effective_date": "2024-04-01", "regulatory_body": "CAA Japan",
     "action_required": "Review all existing FFC notifications containing probiotic/gut health claims. Assess whether supporting evidence meets new meta-analysis standard. File amendments or withdraw non-compliant claims.",
     "source_url": "https://www.caa.go.jp", "tags": ["FFC", "probiotics", "gut-health", "claims"]},

    {"title": "Health Canada: NHPR Modernization — Digital NPN Application Portal Launch",
     "summary": "Health Canada launched the modernized Natural Health Products online application portal (eNHP) replacing the legacy NNHPD system. All new NPN applications must be submitted via eNHP from Q2 2024. Legacy applications in progress must be migrated.",
     "jurisdiction": "canada", "domain": "nutra", "change_type": "NEW",
     "severity": "medium", "effective_date": "2024-04-01", "regulatory_body": "Health Canada",
     "action_required": "Register on the new eNHP portal. Migrate any in-progress applications before the legacy system is retired. Update your submission workflow.",
     "source_url": "https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription.html",
     "tags": ["NPN", "NHPR", "digital", "portal"]},

    {"title": "NMPA China: Compulsory Clinical Trial Waiver Pathways Expanded for Imported Devices",
     "summary": "NMPA expanded the clinical trial waiver pathway for imported Class III medical devices approved by reference regulatory authorities (FDA, EU MDR, PMDA). Devices meeting specific criteria can now substitute foreign clinical data with a bridging study or even waive clinical data entirely.",
     "jurisdiction": "china", "domain": "device", "change_type": "AMENDED",
     "severity": "medium", "effective_date": "2024-01-01", "regulatory_body": "NMPA",
     "action_required": "Assess your Class III device against the new waiver criteria. If eligible, prepare bridging study protocol or waiver application to reduce China registration timeline by 12-18 months.",
     "source_url": "https://www.nmpa.gov.cn", "tags": ["NMPA", "clinical-waiver", "Class-III", "import"]},

    {"title": "MHRA UK: Innovative Licensing and Access Pathway (ILAP) — Updated Criteria",
     "summary": "MHRA updated ILAP eligibility criteria to include combination products and advanced therapy medicinal products (ATMPs). The pathway now offers a target approval timeline of 150 days for eligible products, with rolling review options.",
     "jurisdiction": "uk", "domain": "pharma", "change_type": "AMENDED",
     "severity": "low", "effective_date": "2024-03-01", "regulatory_body": "MHRA",
     "action_required": "Assess whether your product qualifies for ILAP. If launching an ATMP or combination product in the UK, file an Innovation Passport application as the first step.",
     "source_url": "https://www.gov.uk/guidance/innovative-licensing-and-access-pathway", "tags": ["ILAP", "ATMP", "UK", "fast-track"]},

    {"title": "ANVISA Brazil: RDC 786 — New Framework for Functional Ingredients in Food Supplements",
     "summary": "ANVISA published RDC 786/2023 introducing a new positive list for functional ingredients permitted in food supplements (suplementos alimentares). The list expands permitted botanicals, sets maximum daily doses, and introduces bioavailability requirements for mineral supplements.",
     "jurisdiction": "brazil", "domain": "nutra", "change_type": "NEW",
     "severity": "medium", "effective_date": "2024-06-01", "regulatory_body": "ANVISA",
     "action_required": "Cross-reference your supplement formulations against the new positive list. Products with non-listed ingredients must be reformulated or seek ANVISA authorization before the 18-month transition period ends.",
     "source_url": "https://www.gov.br/anvisa", "tags": ["ANVISA", "functional-ingredients", "supplements", "RDC-786"]},
]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[AlertOut])
async def get_alerts(
    jurisdiction: Optional[str] = None,
    domain: Optional[str] = None,
    severity: Optional[str] = None,
    change_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(RegulatoryAlert).where(RegulatoryAlert.is_active == True)  # noqa
    if jurisdiction:
        stmt = stmt.where(RegulatoryAlert.jurisdiction == jurisdiction)
    if domain:
        stmt = stmt.where(RegulatoryAlert.domain == domain)
    if severity:
        stmt = stmt.where(RegulatoryAlert.severity == severity)
    if change_type:
        stmt = stmt.where(RegulatoryAlert.change_type == change_type)
    stmt = stmt.order_by(RegulatoryAlert.published_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/alerts/seed", include_in_schema=False)
async def seed_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed the sample alerts — idempotent."""
    from sqlalchemy import delete
    await db.execute(delete(RegulatoryAlert))
    for a in SEED_ALERTS:
        db.add(RegulatoryAlert(**a))
    await db.commit()
    return {"seeded": len(SEED_ALERTS)}


@router.post("/alerts/subscribe")
async def subscribe(
    data: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Upsert subscription
    result = await db.execute(
        select(AlertSubscription).where(
            AlertSubscription.user_id == user.id,
            AlertSubscription.tenant_id == user.tenant_id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.jurisdictions = data.jurisdictions
        sub.domains = data.domains
        sub.severity_threshold = data.severity_threshold
        sub.email_enabled = data.email_enabled
    else:
        sub = AlertSubscription(
            tenant_id=user.tenant_id,
            user_id=user.id,
            **data.model_dump(),
        )
        db.add(sub)
    await db.commit()
    return {"status": "subscribed"}


@router.get("/alerts/subscription")
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertSubscription).where(AlertSubscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return {"jurisdictions": [], "domains": [], "severity_threshold": "medium", "email_enabled": True}
    return {
        "jurisdictions": sub.jurisdictions,
        "domains": sub.domains,
        "severity_threshold": sub.severity_threshold,
        "email_enabled": sub.email_enabled,
    }
