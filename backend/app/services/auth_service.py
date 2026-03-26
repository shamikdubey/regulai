"""
Auth Service — Phase 1: refresh tokens, API keys, lockout, Auth0
"""
import hashlib, secrets, structlog
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import User, Tenant, RefreshToken, ApiKey

settings = get_settings()
logger = structlog.get_logger()
bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict = {}
_jwks_cache_ts: Optional[datetime] = None

def _get_jwks() -> dict:
    global _jwks_cache, _jwks_cache_ts
    now = datetime.now(timezone.utc)
    if _jwks_cache and _jwks_cache_ts and (now - _jwks_cache_ts).seconds < 3600:
        return _jwks_cache
    if not settings.AUTH0_DOMAIN:
        return {}
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    with httpx.Client(timeout=10.0) as c:
        r = c.get(url); r.raise_for_status()
        _jwks_cache = r.json(); _jwks_cache_ts = now
        return _jwks_cache

def decode_auth0_token(token: str) -> dict:
    try:
        kid = jwt.get_unverified_header(token).get("kid")
        rsa_key = next(({"kty":k["kty"],"kid":k["kid"],"use":k["use"],"n":k["n"],"e":k["e"]}
                        for k in _get_jwks().get("keys",[]) if k["kid"]==kid), None)
        if not rsa_key:
            _jwks_cache.clear()
            rsa_key = next(({"kty":k["kty"],"kid":k["kid"],"use":k["use"],"n":k["n"],"e":k["e"]}
                            for k in _get_jwks().get("keys",[]) if k["kid"]==kid), None)
        if not rsa_key: raise HTTPException(401, "JWT key not found")
        return jwt.decode(token, rsa_key, algorithms=["RS256"],
                          audience=settings.AUTH0_API_AUDIENCE,
                          issuer=f"https://{settings.AUTH0_DOMAIN}/")
    except JWTError as e: raise HTTPException(401, f"Token invalid: {e}")

def decode_internal_token(token: str) -> dict:
    try: return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e: raise HTTPException(401, f"Token invalid: {e}")

def create_access_token(user_id: str, tenant_id: str, email: str, role: str, expires_minutes: Optional[int]=None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "tenant_id": tenant_id, "email": email, "role": role,
                       "https://regulai.app/tenant_id": tenant_id, "exp": exp,
                       "iat": datetime.now(timezone.utc)},
                      settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def create_refresh_token(db: AsyncSession, user: User, device_hint: Optional[str]=None,
                                ip_address: Optional[str]=None, family: Optional[str]=None) -> str:
    raw = RefreshToken.generate()
    rt = RefreshToken(user_id=user.id, tenant_id=user.tenant_id,
                      token_hash=RefreshToken.hash_token(raw),
                      family=family or secrets.token_hex(16),
                      device_hint=device_hint, ip_address=ip_address,
                      expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(rt); await db.flush()
    return raw

async def rotate_refresh_token(db: AsyncSession, raw_token: str, ip_address: Optional[str]=None):
    token_hash = RefreshToken.hash_token(raw_token)
    now = datetime.now(timezone.utc)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if not rt: raise HTTPException(401, "Refresh token not found")
    if rt.expires_at < now: raise HTTPException(401, "Refresh token expired")
    if rt.is_revoked:
        await db.execute(update(RefreshToken).where(RefreshToken.family == rt.family).values(is_revoked=True))
        await db.commit()
        logger.warning("token_reuse_detected", family=rt.family, ip=ip_address)
        raise HTTPException(401, "Token reuse detected. All sessions revoked.")
    rt.is_revoked = True; rt.last_used_at = now
    user_r = await db.execute(select(User).where(User.id == rt.user_id, User.is_active == True))
    user = user_r.scalar_one_or_none()
    if not user: raise HTTPException(401, "User inactive")
    access = create_access_token(str(user.id), str(user.tenant_id), user.email, user.role)
    refresh = await create_refresh_token(db, user, rt.device_hint, ip_address, rt.family)
    return user, access, refresh

async def revoke_all_user_sessions(db: AsyncSession, user_id: str) -> int:
    r = await db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id,
                          RefreshToken.is_revoked == False).values(is_revoked=True).returning(RefreshToken.id))
    return len(r.all())

MAX_FAILED = 5; LOCKOUT_MIN = 15

async def record_failed_login(db: AsyncSession, user: User):
    user.failed_login_count += 1
    if user.failed_login_count >= MAX_FAILED:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MIN)
        logger.warning("account_locked", user_id=str(user.id))
    await db.flush()

async def check_locked(user: User):
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        mins = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise HTTPException(429, f"Account locked. Try again in {mins} minutes.")

async def clear_failed_logins(db: AsyncSession, user: User):
    user.failed_login_count = 0; user.locked_until = None
    user.last_login = datetime.now(timezone.utc); await db.flush()

async def authenticate_api_key(raw_key: str, db: AsyncSession):
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    r = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True))
    ak = r.scalar_one_or_none()
    if not ak: raise HTTPException(401, "Invalid API key")
    if ak.expires_at and ak.expires_at < datetime.now(timezone.utc): raise HTTPException(401, "API key expired")
    if ak.revoked_at: raise HTTPException(401, "API key revoked")
    ak.last_used_at = datetime.now(timezone.utc)
    ur = await db.execute(select(User).where(User.id == ak.created_by, User.is_active == True))
    user = ur.scalar_one_or_none()
    if not user: raise HTTPException(401, "API key owner inactive")
    return user, ak

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
                            db: AsyncSession = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(401, "Authentication required")
    token = credentials.credentials
    if token.startswith("rkai_"):
        user, _ = await authenticate_api_key(token, db); return user
    try:
        payload = decode_auth0_token(token) if settings.AUTH0_DOMAIN else decode_internal_token(token)
    except HTTPException: raise
    r = await db.execute(select(User).where(User.auth0_user_id == payload.get("sub",""), User.is_active == True))
    user = r.scalar_one_or_none()
    if not user: raise HTTPException(401, "User not found or inactive")
    return user

async def get_current_tenant(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Tenant:
    r = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id, Tenant.is_active == True))
    t = r.scalar_one_or_none()
    if not t: raise HTTPException(403, "Tenant not found or inactive")
    return t

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin","superadmin"): raise HTTPException(403, "Admin role required")
    return user

def require_scope(scope: str):
    async def _check(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
                     db: AsyncSession = Depends(get_db)) -> User:
        if not credentials: raise HTTPException(401, "Authentication required")
        token = credentials.credentials
        if token.startswith("rkai_"):
            user, ak = await authenticate_api_key(token, db)
            if scope not in ak.scopes and "*" not in ak.scopes:
                raise HTTPException(403, f"Missing scope: {scope}")
            return user
        return await get_current_user(credentials, db)
    return _check
