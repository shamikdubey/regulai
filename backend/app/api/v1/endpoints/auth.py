"""
Auth API — Phase 1
==================
POST /auth/token           — email+password → access + refresh token
POST /auth/refresh         — rotate refresh token → new access + refresh
POST /auth/logout          — revoke current refresh token
POST /auth/logout-all      — revoke all sessions (logout everywhere)
GET  /auth/me              — current user profile
POST /auth/register        — bootstrap first admin user (disabled in prod)
POST /auth/invite          — admin invites a new user
POST /auth/forgot-password — request password reset email
POST /auth/reset-password  — consume reset token, set new password
GET  /auth/sessions        — list active sessions for current user
DELETE /auth/sessions/{id} — revoke a specific session

GET    /auth/api-keys      — list API keys for tenant
POST   /auth/api-keys      — create new API key
DELETE /auth/api-keys/{id} — revoke an API key
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
import bcrypt as _bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.config import get_settings
from app.services.email import send_invite_email, send_password_reset_email, send_welcome_email
from app.db.database import get_db
from app.db.models import User, Tenant, RefreshToken, ApiKey, PasswordResetToken
from app.schemas.schemas import UserOut
from app.services.auth_service import (
    get_current_user, require_admin,
    create_access_token, create_refresh_token, rotate_refresh_token,
    revoke_all_user_sessions, record_failed_login, check_locked,
    clear_failed_logins, authenticate_api_key,
)

router = APIRouter()
settings = get_settings()
class _PwdCtx:
    """Thin bcrypt wrapper matching passlib interface used in this file."""
    @staticmethod
    def hash(secret: str) -> str:
        return _bcrypt.hashpw(
            secret.encode("utf-8"),
            _bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        ).decode("utf-8")

    @staticmethod
    def verify(secret: str, hashed: str) -> bool:
        try:
            return _bcrypt.checkpw(secret.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def dummy_verify() -> None:
        """Constant-time dummy to prevent user enumeration timing attacks."""
        try:
            _bcrypt.checkpw(b"dummy", _bcrypt.hashpw(b"dummy", _bcrypt.gensalt(4)))
        except Exception:
            pass

pwd_ctx = _PwdCtx()


# ── Schemas ──────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int    # seconds until access token expires

class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_name: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain an uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit")
        return v

class InviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "user"
    temporary_password: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: List[str] = ["query:read"]
    expires_days: Optional[int] = None

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool

class NewApiKeyResponse(ApiKeyResponse):
    key: str   # Raw key — shown ONCE


# ── Helper ────────────────────────────────────────────────────────────────────

def _client_hint(request: Request) -> str:
    ua = request.headers.get("User-Agent", "")[:100]
    return ua

def _client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/auth/token", response_model=TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Exchange email + password for access + refresh token pair."""
    email = form.username.strip().lower()

    # Find user — bypass RLS for auth
    result = await db.execute(
        select(User).where(User.auth0_user_id == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Constant-time rejection to prevent user enumeration
        pwd_ctx.dummy_verify()
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    await check_locked(user)

    # Verify password — check both new password_hash column and legacy metadata_
    stored_hash = user.password_hash or (user.metadata_ or {}).get("password_hash", "")
    if not stored_hash or not pwd_ctx.verify(form.password, stored_hash):
        await record_failed_login(db, user)
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Migrate legacy hash if needed
    if not user.password_hash and (user.metadata_ or {}).get("password_hash"):
        user.password_hash = stored_hash

    await clear_failed_logins(db, user)

    access = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        role=user.role,
    )
    refresh_raw = await create_refresh_token(
        db, user,
        device_hint=_client_hint(request),
        ip_address=_client_ip(request),
    )
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rotate a refresh token. Issues new access + refresh token pair."""
    user, access, refresh_raw = await rotate_refresh_token(
        db, body.refresh_token, ip_address=_client_ip(request)
    )
    await db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/auth/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the provided refresh token (single device logout)."""
    token_hash = RefreshToken.hash_token(body.refresh_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(is_revoked=True)
    )
    await db.commit()


@router.post("/auth/logout-all", status_code=204)
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke ALL refresh tokens for the current user (logout everywhere)."""
    count = await revoke_all_user_sessions(db, str(user.id))
    await db.commit()
    return {"revoked": count}


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "email_verified": user.email_verified,
        "mfa_enabled": user.mfa_enabled,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat(),
    }


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/auth/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active refresh token sessions for the current user."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now,
        ).order_by(RefreshToken.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "device": s.device_hint or "Unknown device",
            "ip": s.ip_address,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        }
        for s in sessions
    ]


@router.delete("/auth/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session (remote logout from one device)."""
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == uuid.UUID(session_id),
            RefreshToken.user_id == user.id,
        )
        .values(is_revoked=True)
    )
    await db.commit()


# ── Registration & invitation ─────────────────────────────────────────────────

@router.post("/auth/register", status_code=201)
async def register_admin(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Bootstrap the first admin user + tenant.
    Disabled after first user exists, and in production when BOOTSTRAP_DISABLED=true.
    """
    if settings.BOOTSTRAP_DISABLED:
        raise HTTPException(403, "Bootstrap registration is disabled")

    # Only allow if no users exist yet
    existing = await db.execute(select(User).limit(1))
    if existing.first():
        raise HTTPException(400, "Admin already exists. Use /auth/invite to add users.")

    tenant = Tenant(
        name=body.tenant_name,
        slug=body.tenant_name.lower().replace(" ", "-")[:50],
        license_key=secrets.token_urlsafe(32),
        allowed_jurisdictions=[],
        allowed_domains=[],
    )
    db.add(tenant)
    await db.flush()

    password_hash = pwd_ctx.hash(body.password)
    user = User(
        tenant_id=tenant.id,
        auth0_user_id=body.email.lower(),
        email=body.email.lower(),
        full_name=body.full_name,
        role="admin",
        password_hash=password_hash,
        email_verified=True,
    )
    db.add(user)
    await db.commit()

    return {
        "message": "Admin user created successfully",
        "email": body.email,
        "tenant": body.tenant_name,
        "next_step": "Sign in at /api/v1/auth/token",
    }


@router.post("/auth/invite", status_code=201)
async def invite_user(
    body: InviteRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin invites a new user to their tenant."""
    existing = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    if existing.first():
        raise HTTPException(400, f"User with email {body.email} already exists")

    temp_password = body.temporary_password or secrets.token_urlsafe(12)
    password_hash = pwd_ctx.hash(temp_password)

    user = User(
        tenant_id=admin.tenant_id,
        auth0_user_id=body.email.lower(),
        email=body.email.lower(),
        full_name=body.full_name,
        role=body.role,
        password_hash=password_hash,
        email_verified=False,
    )
    db.add(user)
    await db.commit()

    # Send invitation email (best-effort - don't fail if email fails)
    try:
        await send_invite_email(
            email=body.email,
            full_name=body.full_name,
            tenant_name=str(admin.tenant_id),
            temporary_password=temp_password,
            invited_by=admin.email,
        )
    except Exception:
        pass  # Email failure should not block user creation

    return {
        "message": "User invited successfully",
        "email": body.email,
        "temporary_password": temp_password,
        "note": "Share the temporary password securely. User should change it on first login.",
    }


# ── Password reset ────────────────────────────────────────────────────────────

@router.post("/auth/forgot-password", status_code=202)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset. Always returns 202 to prevent user enumeration.
    In production, send the token via email. For now, returns it in the response
    (remove this for real email integration in Phase 5).
    """
    result = await db.execute(
        select(User).where(User.email == body.email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    # Always return 202 even if user not found
    if not user:
        return {"message": "If that email exists, a reset link has been sent"}

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(prt)
    await db.commit()

    # Send password reset email
    try:
        await send_password_reset_email(
            email=user.email,
            full_name=user.full_name or user.email,
            reset_token=raw_token,
        )
    except Exception:
        pass  # Email failure should not leak whether user exists

    response = {"message": "If that email exists, a reset link has been sent"}
    if settings.is_development:
        response["debug_token"] = raw_token  # Show token in dev for testing

    return response


@router.post("/auth/reset-password", status_code=200)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Consume a password reset token and set a new password."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > now,
        )
    )
    prt = result.scalar_one_or_none()
    if not prt:
        raise HTTPException(400, "Invalid or expired reset token")

    user_result = await db.execute(select(User).where(User.id == prt.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    user.password_hash = pwd_ctx.hash(body.new_password)
    user.failed_login_count = 0
    user.locked_until = None
    prt.is_used = True

    # Revoke all existing sessions on password change
    await revoke_all_user_sessions(db, str(user.id))
    await db.commit()

    return {"message": "Password updated successfully. Please sign in with your new password."}


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/auth/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current tenant."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.tenant_id == user.tenant_id, ApiKey.is_active == True)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=str(k.id), name=k.name, prefix=k.prefix, scopes=k.scopes,
            created_at=k.created_at, expires_at=k.expires_at,
            last_used_at=k.last_used_at, is_active=k.is_active,
        )
        for k in keys
    ]


@router.post("/auth/api-keys", response_model=NewApiKeyResponse, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key. The raw key is returned ONCE and cannot be retrieved again.
    Store it securely immediately.
    """
    env = "live" if settings.is_production else "test"
    raw_key, prefix, key_hash = ApiKey.generate_key(env)

    expires_at = None
    if body.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_days)

    ak = ApiKey(
        tenant_id=user.tenant_id,
        created_by=user.id,
        name=body.name,
        prefix=prefix,
        key_hash=key_hash,
        scopes=body.scopes,
        expires_at=expires_at,
    )
    db.add(ak)
    await db.commit()
    await db.refresh(ak)

    return NewApiKeyResponse(
        id=str(ak.id), name=ak.name, prefix=ak.prefix, scopes=ak.scopes,
        created_at=ak.created_at, expires_at=ak.expires_at,
        last_used_at=None, is_active=True,
        key=raw_key,
    )


@router.delete("/auth/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key immediately."""
    await db.execute(
        update(ApiKey)
        .where(
            ApiKey.id == uuid.UUID(key_id),
            ApiKey.tenant_id == user.tenant_id,
        )
        .values(is_active=False, revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
