import uuid, secrets, hashlib
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector
from app.db.database import Base


class RegulatoryBody(Base):
    __tablename__ = "regulatory_bodies"
    id:               Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acronym:          Mapped[str]            = mapped_column(String(20), nullable=False, index=True)
    name:             Mapped[str]            = mapped_column(String(255), nullable=False)
    jurisdiction:     Mapped[str]            = mapped_column(String(100), nullable=False, index=True)
    domains:          Mapped[List[str]]      = mapped_column(ARRAY(String), nullable=False)
    description:      Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    website:          Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    established_year: Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    is_active:        Mapped[bool]           = mapped_column(Boolean, default=True)
    tier:             Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    region_id:        Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    metadata_:        Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at:       Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())
    updated_at:       Mapped[datetime]       = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Regulation(Base):
    __tablename__ = "regulations"
    id:                 Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:               Mapped[str]            = mapped_column(String(500), nullable=False, index=True)
    short_name:         Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    jurisdiction:       Mapped[str]            = mapped_column(String(100), nullable=False, index=True)
    domain:             Mapped[str]            = mapped_column(String(50), nullable=False, index=True)
    year:               Mapped[Optional[str]]  = mapped_column(String(20), nullable=True)
    status:             Mapped[str]            = mapped_column(String(50), default="active")
    description:        Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    source_url:         Mapped[Optional[str]]  = mapped_column(String(500), nullable=True)
    regulatory_body_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("regulatory_bodies.id"), nullable=True)
    metadata_:          Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at:         Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())
    updated_at:         Mapped[datetime]       = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    regulatory_body: Mapped[Optional["RegulatoryBody"]] = relationship("RegulatoryBody")
    chunks:          Mapped[List["RegulationChunk"]]    = relationship("RegulationChunk", back_populates="regulation")


class RegulationChunk(Base):
    __tablename__ = "regulation_chunks"
    id:            Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False)
    tenant_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    chunk_index:   Mapped[int]            = mapped_column(Integer, nullable=False)
    section:       Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    content:       Mapped[str]            = mapped_column(Text, nullable=False)
    embedding:     Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    token_count:   Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    metadata_:     Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at:    Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())
    regulation: Mapped["Regulation"] = relationship("Regulation", back_populates="chunks")
    __table_args__ = (
        Index("ix_chunks_embedding", "embedding", postgresql_using="hnsw",
              postgresql_with={"m": 16, "ef_construction": 64},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class Tenant(Base):
    __tablename__ = "tenants"
    id:                    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:                  Mapped[str]            = mapped_column(String(255), nullable=False)
    slug:                  Mapped[str]            = mapped_column(String(100), unique=True, nullable=False, index=True)
    auth0_org_id:          Mapped[Optional[str]]  = mapped_column(String(100), unique=True, nullable=True)
    license_key:           Mapped[str]            = mapped_column(String(255), unique=True, nullable=False)
    is_active:             Mapped[bool]           = mapped_column(Boolean, default=True)
    allowed_jurisdictions: Mapped[List[str]]      = mapped_column(ARRAY(String), nullable=False, default=list)
    allowed_domains:       Mapped[List[str]]      = mapped_column(ARRAY(String), nullable=False, default=list)
    settings:              Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    query_limit_per_day:   Mapped[int]            = mapped_column(Integer, default=500)
    created_at:            Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())
    updated_at:            Mapped[datetime]       = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    users:          Mapped[List["User"]]         = relationship("User", back_populates="tenant")
    api_keys:       Mapped[List["ApiKey"]]       = relationship("ApiKey", back_populates="tenant")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    id:                  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    auth0_user_id:       Mapped[str]            = mapped_column(String(255), unique=True, nullable=False, index=True)
    email:               Mapped[str]            = mapped_column(String(255), nullable=False, index=True)
    full_name:           Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    role:                Mapped[str]            = mapped_column(String(50), default="user")
    is_active:           Mapped[bool]           = mapped_column(Boolean, default=True)
    password_hash:       Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    email_verified:      Mapped[bool]           = mapped_column(Boolean, default=False, server_default="false")
    mfa_enabled:         Mapped[bool]           = mapped_column(Boolean, default=False, server_default="false")
    mfa_secret:          Mapped[Optional[str]]  = mapped_column(String(64), nullable=True)
    failed_login_count:  Mapped[int]            = mapped_column(Integer, default=0, server_default="0")
    locked_until:        Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login:          Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_:           Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at:          Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())
    tenant:         Mapped["Tenant"]              = relationship("Tenant", back_populates="users")
    refresh_tokens: Mapped[List["RefreshToken"]]  = relationship("RefreshToken", back_populates="user")
    api_keys:       Mapped[List["ApiKey"]]        = relationship("ApiKey", back_populates="created_by_user", foreign_keys="ApiKey.created_by")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    token_hash:   Mapped[str]            = mapped_column(String(128), nullable=False, unique=True)
    family:       Mapped[str]            = mapped_column(String(64), nullable=False)
    is_revoked:   Mapped[bool]           = mapped_column(Boolean, default=False)
    device_hint:  Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    ip_address:   Mapped[Optional[str]]  = mapped_column(String(64), nullable=True)
    expires_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user:   Mapped["User"]   = relationship("User", back_populates="refresh_tokens")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="refresh_tokens")
    @staticmethod
    def hash_token(raw: str) -> str: return hashlib.sha256(raw.encode()).hexdigest()
    @staticmethod
    def generate() -> str: return secrets.token_urlsafe(64)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    created_by:   Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name:         Mapped[str]            = mapped_column(String(255), nullable=False)
    prefix:       Mapped[str]            = mapped_column(String(12), nullable=False)
    key_hash:     Mapped[str]            = mapped_column(String(128), nullable=False, unique=True)
    scopes:       Mapped[List[str]]      = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    is_active:    Mapped[bool]           = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant:           Mapped["Tenant"]        = relationship("Tenant", back_populates="api_keys")
    created_by_user:  Mapped[Optional["User"]] = relationship("User", back_populates="api_keys", foreign_keys=[created_by])
    @staticmethod
    def generate_key(env: str = "live") -> tuple[str, str, str]:
        raw = secrets.token_urlsafe(48)
        prefix = f"rkai_{env}_{raw[:8]}"
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        return f"rkai_{env}_{raw}", prefix, key_hash


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str]      = mapped_column(String(128), nullable=False, unique=True)
    is_used:    Mapped[bool]     = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str]      = mapped_column(String(128), nullable=False, unique=True)
    is_used:    Mapped[bool]     = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QueryLog(Base):
    __tablename__ = "query_logs"
    id:                  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id:             Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    api_key_id:          Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    query:               Mapped[str]            = mapped_column(Text, nullable=False)
    jurisdiction:        Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    domain:              Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    response:            Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    citations:           Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    confidence:          Mapped[Optional[float]]= mapped_column(Float, nullable=True)
    retrieved_chunk_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    latency_ms:          Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    hmac_signature:      Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    created_at:          Mapped[datetime]       = mapped_column(DateTime, server_default=func.now(), index=True)
    __table_args__ = (Index("ix_query_logs_tenant_created", "tenant_id", "created_at"),)


class Document(Base):
    __tablename__ = "documents"
    id:                Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    uploaded_by:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename:          Mapped[str]            = mapped_column(String(500), nullable=False)
    file_path:         Mapped[str]            = mapped_column(String(1000), nullable=False)
    file_size_bytes:   Mapped[int]            = mapped_column(Integer, nullable=False)
    mime_type:         Mapped[str]            = mapped_column(String(100), nullable=False)
    jurisdiction:      Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    domain:            Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    processing_status: Mapped[str]            = mapped_column(String(50), default="pending")
    chunk_count:       Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    metadata_:         Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at:        Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())
