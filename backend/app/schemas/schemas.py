from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator


# ─── Query ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    jurisdiction: Optional[str] = None
    domain: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v) > 2000:
            raise ValueError("Query too long (max 2000 chars)")
        return v.strip()


class Citation(BaseModel):
    regulation: str
    section: Optional[str] = None
    jurisdiction: str
    year: Optional[str] = None
    relevance: str


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    citations: List[Citation] = []
    confidence: float = 0.0
    caveats: List[str] = []
    next_steps: List[str] = []
    regulatory_bodies: List[str] = []
    sources_used: int = 0
    latency_ms: int = 0


# ─── Regulatory Bodies ────────────────────────────────────────────────────────

class RegulatoryBodyOut(BaseModel):
    id: UUID
    acronym: str
    name: str
    jurisdiction: str
    domains: List[str]
    description: Optional[str]
    website: Optional[str]
    established_year: Optional[int]
    is_active: bool

    model_config = {"from_attributes": True}


class RegulationOut(BaseModel):
    id: UUID
    name: str
    short_name: Optional[str]
    jurisdiction: str
    domain: str
    year: Optional[str]
    status: str
    description: Optional[str]
    source_url: Optional[str]

    model_config = {"from_attributes": True}


# ─── Documents ────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: UUID
    filename: str
    file_size_bytes: int
    mime_type: str
    jurisdiction: Optional[str]
    domain: Optional[str]
    processing_status: str
    chunk_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: UUID
    query: str
    jurisdiction: Optional[str]
    domain: Optional[str]
    confidence: Optional[float]
    latency_ms: Optional[int]
    sources_used: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Tenant ───────────────────────────────────────────────────────────────────

class TenantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    allowed_jurisdictions: List[str]
    allowed_domains: List[str]
    query_limit_per_day: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantCreate(BaseModel):
    name: str
    slug: str
    auth0_org_id: Optional[str] = None
    allowed_jurisdictions: List[str] = []
    allowed_domains: List[str] = []
    query_limit_per_day: int = 500


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    db: str
    redis: str
