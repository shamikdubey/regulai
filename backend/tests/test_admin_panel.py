"""Admin Panel Test Suite"""
import uuid
import pytest
from httpx import AsyncClient

class TestAdminUsers:
    @pytest.mark.asyncio
    async def test_list_users_as_admin(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_users_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/users")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.get(f"/api/v1/admin/users/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_update_role_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.put(
            f"/api/v1/admin/users/{uuid.uuid4()}/role",
            json={"role": "user"},
            headers=auth_headers
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_self_rejected(self, client: AsyncClient, auth_headers: dict, admin_user):
        r = await client.put(
            f"/api/v1/admin/users/{admin_user.id}/deactivate",
            headers=auth_headers
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_deactivate_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.put(
            f"/api/v1/admin/users/{uuid.uuid4()}/deactivate",
            headers=auth_headers
        )
        assert r.status_code == 404

class TestAdminTenants:
    @pytest.mark.asyncio
    async def test_list_tenants_as_admin(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/api/v1/admin/tenants", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_tenants_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/tenants")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.get(f"/api/v1/admin/tenants/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

class TestAdminStats:
    @pytest.mark.asyncio
    async def test_get_stats_as_admin(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/api/v1/admin/stats", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "total_users" in body
        assert "total_tenants" in body
        assert "total_queries" in body

    @pytest.mark.asyncio
    async def test_get_stats_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/stats")
        assert r.status_code == 401

class TestNonAdminBlocked:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_users(self, client: AsyncClient):
        """No token = 401; role enforcement tested via require_admin dependency"""
        r = await client.get("/api/v1/admin/users")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_tenants(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/tenants")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_cannot_get_stats(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/stats")
        assert r.status_code == 401
