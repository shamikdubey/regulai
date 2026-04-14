"""
Filing Wizard — Feature ported from Reguard into RegulAI
  POST   /filing-wizard/projects
  GET    /filing-wizard/projects
  GET    /filing-wizard/projects/{id}
  PUT    /filing-wizard/projects/{id}
  POST   /filing-wizard/projects/{id}/checklist/generate
  GET    /filing-wizard/templates
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user

router = APIRouter()

class ProjectCreate(BaseModel):
    product_name: str
    country: str
    domain: str
    device_class: Optional[str] = None
    food_category: Optional[str] = None

    @field_validator("product_name")
    @classmethod
    def name_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("product_name must not be blank")
        return v

    @field_validator("domain")
    @classmethod
    def domain_valid(cls, v):
        allowed = ("FOOD", "MEDICAL_DEVICE", "PHARMA", "NUTRACEUTICAL", "TRADITIONAL")
        if v not in allowed:
            raise ValueError(f"domain must be one of: {', '.join(allowed)}")
        return v

    @field_validator("country")
    @classmethod
    def country_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("country must not be blank")
        return v

class ProjectUpdate(BaseModel):
    status: Optional[str] = None
    progress_pct: Optional[int] = None

class ChecklistGenerateRequest(BaseModel):
    additional_context: Optional[str] = ""

@router.post("/filing-wizard/projects", status_code=201)
async def create_project(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: ProjectCreate = ...,
):
    project_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO filing_projects
            (id, tenant_id, user_id, product_name, country, domain, device_class, food_category, status, progress_pct)
        VALUES
            (:id, :tenant_id, :user_id, :product_name, :country, :domain, :device_class, :food_category, 'planning', 0)
    """), {
        "id": project_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
        "product_name": body.product_name,
        "country": body.country,
        "domain": body.domain,
        "device_class": body.device_class,
        "food_category": body.food_category,
    })
    await db.commit()
    return {
        "id": project_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
        "product_name": body.product_name,
        "country": body.country,
        "domain": body.domain,
        "device_class": body.device_class,
        "food_category": body.food_category,
        "status": "planning",
        "progress_pct": 0,
        "checklist": [],
    }

@router.get("/filing-wizard/projects")
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    domain: Optional[str] = None,
    status: Optional[str] = None,
):
    query = "SELECT * FROM filing_projects WHERE tenant_id = :tenant_id"
    params = {"tenant_id": str(user.tenant_id)}
    if domain:
        query += " AND domain = :domain"
        params["domain"] = domain
    if status:
        query += " AND status = :status"
        params["status"] = status
    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [dict(r) for r in rows]

@router.get("/filing-wizard/projects/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT * FROM filing_projects
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(project_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return {**dict(row), "checklist": []}

@router.put("/filing-wizard/projects/{project_id}")
async def update_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: ProjectUpdate = ...,
):
    result = await db.execute(text("""
        SELECT id FROM filing_projects
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(project_id), "tenant_id": str(user.tenant_id)})
    if not result.first():
        raise HTTPException(status_code=404, detail="Project not found")
    if body.status:
        await db.execute(text(
            "UPDATE filing_projects SET status = :status WHERE id = :id"
        ), {"status": body.status, "id": str(project_id)})
    if body.progress_pct is not None:
        await db.execute(text(
            "UPDATE filing_projects SET progress_pct = :pct WHERE id = :id"
        ), {"pct": body.progress_pct, "id": str(project_id)})
    await db.commit()
    return {"status": "updated"}

@router.post("/filing-wizard/projects/{project_id}/checklist/generate")
async def generate_checklist(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    body: ChecklistGenerateRequest = ...,
):
    result = await db.execute(text("""
        SELECT * FROM filing_projects
        WHERE id = :id AND tenant_id = :tenant_id
    """), {"id": str(project_id), "tenant_id": str(user.tenant_id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    domain = row.get("domain", "FOOD")

    DOMAIN_CHECKLISTS: dict[str, list[str]] = {
        "FOOD": [
            "Register with FSSAI/FDA/local food authority",
            "Prepare product formulation and ingredient list per CODEX/FSSAI standards",
            "Commission nutritional analysis from accredited lab",
            "Prepare label complying with local labeling regulations",
            "Obtain GMP certificate for manufacturing facility",
            "Submit product approval application with fee",
            "Arrange for product sample testing per local standards",
            "Obtain import/export licenses if applicable",
        ],
        "MEDICAL_DEVICE": [
            "Classify device under local MDR (e.g. India MDR 2017, EU MDR 2017/745, US 21 CFR 820)",
            "Prepare technical documentation / Design Dossier",
            "Commission biocompatibility testing per ISO 10993",
            "Obtain CE marking / 510(k) clearance / CDSCO registration as applicable",
            "Implement and document Quality Management System per ISO 13485",
            "Prepare IFU (Instructions for Use) compliant with local regulations",
            "Register manufacturing site with regulatory authority",
            "Submit market authorization application with device master file",
        ],
        "PHARMA": [
            "Confirm regulatory pathway (NDA/ANDA/NDA per ICH guidelines)",
            "Prepare CTD (Common Technical Document) Modules 1-5",
            "Commission stability studies per ICH Q1A/Q1B",
            "Prepare Drug Master File (DMF) for API",
            "Obtain GMP certification from competent authority",
            "Submit clinical data package (if required) per ICH E6",
            "Prepare SmPC / Package Insert per local requirements",
            "Apply for market authorization with complete dossier and fee payment",
        ],
        "NUTRACEUTICAL": [
            "Classify product under applicable category (DSHEA/EFSA Novel Food/FSSAI Health Supplement)",
            "Commission safety assessment and toxicology review",
            "Prepare product specification sheet with CoA from accredited lab",
            "Verify all ingredients are on approved positive lists (FSSAI Schedule, EFSA list)",
            "Prepare label with claims compliant with DSHEA/EFSA claim regulations",
            "Submit pre-market notification or approval application as required",
            "Obtain GMP certification for nutraceutical manufacturing",
            "Arrange for shelf-life and stability data",
        ],
        "TRADITIONAL": [
            "Classify product under applicable act (Drugs & Cosmetics Act / WHO Traditional Medicine guidelines)",
            "Prepare classical reference from recognized pharmacopeia (API, Ayurvedic Pharmacopeia of India)",
            "Commission standardization and quality control studies",
            "Prepare manufacturing SOP compliant with GMP for ASU drugs",
            "Obtain license from State Licensing Authority under Schedule T",
            "Prepare patient information leaflet with traditional use evidence",
            "Commission heavy metal and pesticide residue testing per pharmacopeia limits",
            "Submit product registration with complete Ayurvedic/traditional medicine dossier",
        ],
    }

    checklist_tasks = DOMAIN_CHECKLISTS.get(domain, DOMAIN_CHECKLISTS["FOOD"])

    return {
        "status": "complete",
        "message": "Checklist generated",
        "items": [
            {
                "id": str(uuid.uuid4()),
                "task": task,
                "completed": False,
                "status": "pending",
            }
            for task in checklist_tasks
        ],
    }

@router.get("/filing-wizard/templates")
async def list_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    domain: Optional[str] = None,
):
    query = "SELECT * FROM filing_templates"
    params = {}
    if domain:
        query += " WHERE domain = :domain"
        params["domain"] = domain
    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [dict(r) for r in rows]
