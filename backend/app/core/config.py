"""
Application Configuration
==========================
Pydantic Settings with environment-specific validation.

Production checklist:
  ✓ ENVIRONMENT=production
  ✓ SECRET_KEY = 64+ random chars  (openssl rand -hex 32)
  ✓ CORS_ORIGINS = exact frontend domain(s) — NO wildcard
  ✓ DATABASE_URL = RDS connection string (via Secrets Manager)
  ✓ REDIS_URL = ElastiCache URL
  ✓ AUTH0_DOMAIN + AUTH0_API_AUDIENCE configured
  ✓ ANTHROPIC_API_KEY / OPENAI_API_KEY from Secrets Manager
  ✓ AWS_S3_BUCKET set for document storage
  ✓ SENTRY_DSN for error tracking
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── App
    APP_NAME: str = "RegulAI"
    VERSION: str = "4.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"

    # ── Database
    DATABASE_URL: str = "postgresql+asyncpg://regulai:regulai_secret@localhost:5432/regulai"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_STATEMENT_TIMEOUT_MS: int = 30000

    # ── Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # ── AI / LLM
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM: str = "claude"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    OPENAI_MODEL: str = "gpt-4o"
    MAX_TOKENS: int = 2048
    RAG_TOP_K: int = 5
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3

    # ── Auth
    AUTH0_DOMAIN: str = ""
    AUTH0_API_AUDIENCE: str = ""
    AUTH0_CLIENT_ID: str = ""
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── CORS  — NEVER use * in production
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ── AWS / Storage
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = ""
    AWS_S3_BUCKET_PREFIX: str = "documents"
    SECRETS_MANAGER_SECRET_NAME: str = ""
    SECRETS_MANAGER_ARN: str = ""
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Monitoring
    SENTRY_DSN: str = ""
    OTEL_ENDPOINT: str = ""

    # ── Security
    BCRYPT_ROUNDS: int = 12
    API_KEY_LENGTH: int = 48
    BOOTSTRAP_DISABLED: bool = False

    # ── Feature flags
    ENABLE_STREAMING: bool = True
    ENABLE_CELERY: bool = False
    ENABLE_BILLING: bool = False

    # ── Rate limiting (requests per window)
    RATE_LIMIT_DEFAULT: str = "200/minute"
    RATE_LIMIT_AI_ENDPOINTS: str = "30/minute"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        if self.is_production:
            errors = []
            if self.SECRET_KEY in ("", "change-me-in-production"):
                errors.append("SECRET_KEY must be a strong random value")
            if "*" in self.CORS_ORIGINS:
                errors.append("CORS_ORIGINS must not contain '*' in production")
            if errors:
                raise ValueError(f"Production config errors: {'; '.join(errors)}")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def show_docs(self) -> bool:
        return not self.is_production

    @property
    def use_s3(self) -> bool:
        return bool(self.AWS_S3_BUCKET)

    def get_s3_document_key(self, tenant_id: str, document_id: str, filename: str) -> str:
        """
        Tenant-scoped S3 key — ensures zero cross-tenant document access.
        Format: documents/{tenant_id}/{document_id}/{filename}
        """
        import re
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        return f"{self.AWS_S3_BUCKET_PREFIX}/{tenant_id}/{document_id}/{safe_filename}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
