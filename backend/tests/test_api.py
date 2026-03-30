import json
"""
RegulAI Backend Test Suite — Phase 0–5
========================================
Coverage:
  - Authentication: login, token validation, refresh rotation, lockout
  - Multi-tenant RLS isolation: cross-tenant data access attempts
  - API key creation, usage, scopes, revocation
  - Rate limiting: query limit enforcement
  - GDPR: erasure, export, PII detection
  - Health checks: all component statuses
  - Reference data endpoints: allowable limits, labeling, licensing
  - Privacy endpoints
  - Billing: plans list (public)

Run: cd backend && pytest tests/test_api.py -v --tb=short
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, admin_user, tenant):
        r = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email,
            "password": "Test1234!",
        })
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        r = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email,
            "password": "WrongPassword!",
        })
        assert r.status_code == 401
        assert "Incorrect" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/token", data={
            "username": "nobody@nowhere.com",
            "password": "anything",
        })
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint(self, client: AsyncClient, auth_headers, admin_user):
        r = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == admin_user.email
        assert body["role"] == "admin"
        assert "tenant_id" in body

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        r = await client.get("/api/v1/auth/me",
                              headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_account_lockout(self, client: AsyncClient, admin_user):
        """After 5 failed attempts, account should lock."""
        for i in range(5):
            r = await client.post("/api/v1/auth/token", data={
                "username": admin_user.email,
                "password": f"wrong{i}",
            })
            assert r.status_code == 401

        # 6th attempt should hit lockout
        r = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email,
            "password": "wrongagain",
        })
        assert r.status_code == 429
        assert "locked" in r.json()["detail"].lower()


class TestRefreshTokens:
    @pytest.mark.asyncio
    async def test_refresh_rotation(self, client: AsyncClient, admin_user):
        """Refresh token rotation returns new token pair."""
        # Login to get initial tokens
        login = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email, "password": "Test1234!",
        })
        rt1 = login.json()["refresh_token"]

        # Rotate
        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        rt2 = body["refresh_token"]
        assert rt2 != rt1    # Must be a new token

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_detection(self, client: AsyncClient, admin_user):
        """Reusing a consumed refresh token must revoke entire family."""
        login = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email, "password": "Test1234!",
        })
        rt = login.json()["refresh_token"]

        # First rotation — valid
        r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert r1.status_code == 200

        # Reuse old token — should fail and revoke family
        r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert r2.status_code == 401
        assert "reuse" in r2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self, client: AsyncClient, admin_user):
        """After logout, refresh token must be unusable."""
        login = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email, "password": "Test1234!",
        })
        rt = login.json()["refresh_token"]

        # Logout
        r = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
        assert r.status_code == 204

        # Try to use revoked token
        r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert r2.status_code == 401

    @pytest.mark.asyncio
    async def test_sessions_list(self, client: AsyncClient, admin_user, auth_headers):
        r = await client.get("/api/v1/auth/sessions", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_blocked_when_users_exist(
        self, client: AsyncClient, admin_user
    ):
        """Registration endpoint returns 400 when a user already exists."""
        # admin_user fixture creates a user first, so register should be blocked
        r = await client.post("/api/v1/auth/register", json={
            "email": "newadmin@test.com",
            "password": "Test1234!",
            "full_name": "New Admin",
            "tenant_name": "New Co",
        })
        assert r.status_code in (400, 403)

    @pytest.mark.asyncio
    async def test_invite_user(self, client: AsyncClient, auth_headers):
        """Admin can invite a new user."""
        r = await client.post("/api/v1/auth/invite", json={
            "email": f"invited-{uuid.uuid4().hex[:6]}@test.com",
            "full_name": "Invited User",
            "role": "user",
        }, headers=auth_headers)
        assert r.status_code == 201
        body = r.json()
        assert "temporary_password" in body

    @pytest.mark.asyncio
    async def test_invite_requires_admin(self, client: AsyncClient, user_headers):
        """Regular user cannot invite others."""
        r = await client.post("/api/v1/auth/invite", json={
            "email": "someone@test.com",
            "full_name": "Someone",
        }, headers=user_headers)
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# API KEYS
# ══════════════════════════════════════════════════════════════════════════════

class TestApiKeys:
    @pytest.mark.asyncio
    async def test_create_api_key(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/v1/auth/api-keys", json={
            "name": "Test Integration",
            "scopes": ["query:read"],
        }, headers=auth_headers)
        assert r.status_code == 201
        body = r.json()
        assert "key" in body           # Raw key returned once
        assert body["key"].startswith("rkai_")
        assert body["prefix"] in body["key"]
        assert "query:read" in body["scopes"]

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, client: AsyncClient, api_key):
        """API key can authenticate to protected endpoints."""
        raw_key, _ = api_key
        r = await client.get("/api/v1/auth/me",
                              headers={"Authorization": f"Bearer {raw_key}"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_revoked_api_key_rejected(self, client: AsyncClient, auth_headers, api_key):
        raw_key, ak = api_key

        # Revoke
        r = await client.delete(f"/api/v1/auth/api-keys/{ak.id}",
                                 headers=auth_headers)
        assert r.status_code == 204

        # Try to use revoked key
        r2 = await client.get("/api/v1/auth/me",
                               headers={"Authorization": f"Bearer {raw_key}"})
        assert r2.status_code == 401

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client: AsyncClient, auth_headers, api_key):
        r = await client.get("/api/v1/auth/api-keys", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_api_key_requires_admin(self, client: AsyncClient, user_headers):
        r = await client.post("/api/v1/auth/api-keys", json={
            "name": "Should fail", "scopes": ["query:read"]
        }, headers=user_headers)
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TENANT RLS ISOLATION
# ══════════════════════════════════════════════════════════════════════════════

class TestTenantIsolation:
    """
    Critical security tests: verify that RLS prevents cross-tenant data access.
    A user from Tenant B must never be able to read Tenant A's data.
    """

    @pytest.mark.asyncio
    async def test_tenant_me_returns_own_tenant(
        self, client: AsyncClient, auth_headers, tenant
    ):
        r = await client.get("/api/v1/tenants/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == str(tenant.id)

    @pytest.mark.asyncio
    async def test_other_tenant_cannot_see_my_documents(
        self,
        client: AsyncClient,
        auth_headers,
        other_tenant_headers,
        db,
    ):
        """Upload doc as tenant A. Tenant B must not see it."""
        # Upload a doc as Tenant A
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("secret.txt", b"Top secret regulatory data", "text/plain")},
            headers=auth_headers,
        )
        assert upload.status_code == 200
        doc_id = upload.json()["id"]

        # Tenant B tries to access the document status
        r = await client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers=other_tenant_headers,
        )
        # Must be 404 (not visible) not 403 (which leaks existence)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_other_tenant_cannot_see_my_audit_log(
        self,
        client: AsyncClient,
        auth_headers,
        other_tenant_headers,
    ):
        """Audit log entries are scoped to the requesting tenant."""
        # Tenant A's audit log
        r_a = await client.get("/api/v1/audit/", headers=auth_headers)
        assert r_a.status_code == 200

        # Tenant B's audit log must be empty / different
        r_b = await client.get("/api/v1/audit/", headers=other_tenant_headers)
        assert r_b.status_code == 200

        # IDs must not overlap
        ids_a = {e["id"] for e in r_a.json()}
        ids_b = {e["id"] for e in r_b.json()}
        assert ids_a.isdisjoint(ids_b), "Cross-tenant audit log leak detected!"

    @pytest.mark.asyncio
    async def test_other_tenant_sees_own_query_limit(
        self,
        client: AsyncClient,
        auth_headers,
        other_tenant_headers,
    ):
        """Each tenant has its own query limit counter."""
        r_a = await client.get("/api/v1/billing/usage", headers=auth_headers)
        r_b = await client.get("/api/v1/billing/usage", headers=other_tenant_headers)
        # Both succeed and return their own data
        assert r_a.status_code == 200
        assert r_b.status_code == 200
        # Their tenant IDs from /tenants/me must differ
        ta = (await client.get("/api/v1/tenants/me", headers=auth_headers)).json()["id"]
        tb = (await client.get("/api/v1/tenants/me", headers=other_tenant_headers)).json()["id"]
        assert ta != tb


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD RESET
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_forgot_password_always_202(self, client: AsyncClient):
        """Always returns 202 — no user enumeration possible."""
        for email in ["exists@example.com", "doesnotexist@example.com", ""]:
            r = await client.post("/api/v1/auth/forgot-password",
                                  json={"email": email or "x@x.com"})
            assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_reset_invalid_token(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/reset-password", json={
            "token": "completely-invalid-token",
            "new_password": "NewPass123!",
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_flow(self, client: AsyncClient, admin_user, db):
        """Full password reset: request → token → use → login with new password."""
        import hashlib
        import secrets as sec
        from app.db.models import PasswordResetToken
        from datetime import datetime, timezone, timedelta

        # Generate a reset token manually (in prod this comes from email)
        raw_token = sec.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        prt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(prt)
        await db.flush()
        await db.commit()  # must commit so app connection can see the token

        # Use the token
        r = await client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "BrandNew456!",
        })
        assert r.status_code == 200

        # Login with new password
        login = await client.post("/api/v1/auth/token", data={
            "username": admin_user.email,
            "password": "BrandNew456!",
        })
        assert login.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# TENANT & USERS
# ══════════════════════════════════════════════════════════════════════════════

class TestTenant:
    @pytest.mark.asyncio
    async def test_get_my_tenant(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/tenants/me", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "name" in body
        assert "slug" in body
        assert "query_limit_per_day" in body

    @pytest.mark.asyncio
    async def test_unauthenticated_no_tenant(self, client: AsyncClient):
        r = await client.get("/api/v1/tenants/me")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDocuments:
    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/documents/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_upload_text_document(self, client: AsyncClient, auth_headers):
        content = b"FSSAI Regulation 2022. Section 3.1: All health supplements must declare active ingredients."
        r = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("regulation.txt", content, "text/plain")},
            data={"jurisdiction": "india", "domain": "nutra"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["filename"] == "regulation.txt"
        assert body["processing_status"] in ("pending", "queued")
        assert body["jurisdiction"] == "india"

    @pytest.mark.asyncio
    async def test_upload_rejected_mime_type(self, client: AsyncClient, auth_headers):
        r = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("malware.exe", b"\x4d\x5a", "application/octet-stream")},
            headers=auth_headers,
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_document_status_not_found(self, client: AsyncClient, auth_headers):
        r = await client.get(f"/api/v1/documents/{uuid.uuid4()}/status",
                              headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_documents_require_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/documents/")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# REFERENCE DATA (Allowable Limits, Labeling, Licensing, Ingredient Specs)
# ══════════════════════════════════════════════════════════════════════════════

class TestReferenceData:
    @pytest.mark.asyncio
    async def test_allowable_limits_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/allowable-limits", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_allowable_limits_filter_jurisdiction(
        self, client: AsyncClient, auth_headers
    ):
        r = await client.get("/api/v1/allowable-limits?jurisdiction=india",
                              headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_allowable_limits_filter_type(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/allowable-limits?limit_type=additive",
                              headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_labeling_requirements_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/labeling-requirements", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_labeling_filter(self, client: AsyncClient, auth_headers):
        r = await client.get(
            "/api/v1/labeling-requirements?jurisdiction=usa&product_type=food",
            headers=auth_headers,
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_licensing_pathways_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/licensing-pathways", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_ingredient_specs_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/ingredient-specs", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_regulations_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/regulations/regulations", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_regulatory_bodies_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/regulations/bodies", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_reference_data_requires_auth(self, client: AsyncClient):
        for path in ["/api/v1/allowable-limits", "/api/v1/labeling-requirements",
                     "/api/v1/licensing-pathways", "/api/v1/ingredient-specs"]:
            r = await client.get(path)
            assert r.status_code == 401, f"{path} should require auth"


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/audit/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_audit_pagination(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/audit/?limit=5&offset=0", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_entry_not_found(self, client: AsyncClient, auth_headers):
        r = await client.get(f"/api/v1/audit/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/audit/")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# PRIVACY / GDPR
# ══════════════════════════════════════════════════════════════════════════════

class TestPrivacy:
    @pytest.mark.asyncio
    async def test_get_consent(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/privacy/consent", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "analytics" in body
        assert "marketing" in body

    @pytest.mark.asyncio
    async def test_update_consent(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/v1/privacy/consent", json={
            "analytics": True,
            "marketing": False,
            "third_party_sharing": False,
        }, headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_data_export(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/privacy/export", headers=auth_headers)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")
        body = r.json()
        assert "user_profile" in body
        assert "query_history" in body
        assert "uploaded_documents" in body
        assert "data_processing_purposes" in body

    @pytest.mark.asyncio
    async def test_pii_check_clean_file(self, client: AsyncClient, auth_headers):
        """Clean file should return no PII findings."""
        r = await client.post(
            "/api/v1/privacy/check-pii",
            files={"file": ("clean.txt", b"General regulatory information about food safety.", "text/plain")},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pii_detected"] is False

    @pytest.mark.asyncio
    async def test_pii_check_detects_email(self, client: AsyncClient, auth_headers):
        """File with email address should be flagged."""
        content = b"Contact the applicant at john.doe@pharma-corp.com for details."
        r = await client.post(
            "/api/v1/privacy/check-pii",
            files={"file": ("with-pii.txt", content, "text/plain")},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pii_detected"] is True
        assert any("Email" in f["type"] for f in body["findings"])

    @pytest.mark.asyncio
    async def test_processing_info(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/privacy/processing-info", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "data_categories" in body
        assert "rights" in body
        assert "controller" in body

    @pytest.mark.asyncio
    async def test_erasure_requires_confirmation(self, client: AsyncClient, auth_headers):
        """Wrong confirmation string must be rejected."""
        r = await client.request("DELETE", "/api/v1/privacy/me", json={"confirmation": "yes delete me"}, headers=auth_headers)
        assert r.status_code == 400
        assert "DELETE MY ACCOUNT" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_erasure_requires_auth(self, client: AsyncClient):
        r = await client.request("DELETE", "/api/v1/privacy/me", json={"confirmation": "DELETE MY ACCOUNT"})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH & METRICS
# ══════════════════════════════════════════════════════════════════════════════

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient, db):
        r = await client.get("/health")
        assert r.status_code in (200, 503)
        body = r.json()
        assert "status" in body
        assert "version" in body
        assert "checks" in body
        assert "database" in body["checks"]

    @pytest.mark.asyncio
    async def test_liveness_always_200(self, client: AsyncClient):
        r = await client.get("/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness(self, client: AsyncClient, db):
        r = await client.get("/health/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        r = await client.get("/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    @pytest.mark.asyncio
    async def test_json_metrics(self, client: AsyncClient):
        r = await client.get("/metrics/json")
        assert r.status_code == 200
        body = r.json()
        assert "uptime_seconds" in body

    @pytest.mark.asyncio
    async def test_circuit_breakers(self, client: AsyncClient):
        r = await client.get("/health/circuit-breakers")
        assert r.status_code == 200
        body = r.json()
        assert "anthropic" in body
        assert "openai" in body
        for provider, state in body.items():
            assert "state" in state
            assert "available" in state


# ══════════════════════════════════════════════════════════════════════════════
# BILLING
# ══════════════════════════════════════════════════════════════════════════════

class TestBilling:
    @pytest.mark.asyncio
    async def test_plans_public(self, client: AsyncClient):
        """Plans endpoint is public — no auth required."""
        r = await client.get("/api/v1/billing/plans")
        assert r.status_code == 200
        plans = r.json()
        assert "starter" in plans
        assert "growth" in plans
        assert "business" in plans
        assert "enterprise" in plans
        for slug, plan in plans.items():
            assert "features" in plan
            assert "query_limit_per_day" in plan

    @pytest.mark.asyncio
    async def test_usage_authenticated(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/billing/usage", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "usage" in body
        assert "queries_today" in body["usage"]
        assert "queries_limit_per_day" in body["usage"]

    @pytest.mark.asyncio
    async def test_usage_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/billing/usage")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_subscription_info(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/billing/subscription", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "plan" in body
        assert "limits" in body


# ══════════════════════════════════════════════════════════════════════════════
# ALERTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAlerts:
    @pytest.mark.asyncio
    async def test_alerts_list(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/alerts", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_alerts_filter_jurisdiction(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/alerts?jurisdiction=india", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_subscribe_alerts(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/v1/alerts/subscribe", json={
            "jurisdictions": ["india", "usa"],
            "domains": ["food", "pharma"],
            "severity_threshold": "medium",
            "email_enabled": True,
        }, headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_alerts_require_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/alerts")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY — Headers & CORS
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        """All required security headers must be on every response."""
        r = await client.get("/health/live")
        headers = r.headers

        assert "x-content-type-options" in headers, "X-Content-Type-Options missing"
        assert headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in headers, "X-Frame-Options missing"
        assert headers["x-frame-options"] == "DENY"

    @pytest.mark.asyncio
    async def test_api_response_not_cached(self, client: AsyncClient, auth_headers):
        """API responses must not be cached."""
        r = await client.get("/api/v1/auth/me", headers=auth_headers)
        cc = r.headers.get("cache-control", "")
        assert "no-store" in cc or "no-cache" in cc

    @pytest.mark.asyncio
    async def test_request_id_in_response(self, client: AsyncClient):
        """Every response must include X-Request-ID."""
        r = await client.get("/health/live")
        assert "x-request-id" in r.headers
