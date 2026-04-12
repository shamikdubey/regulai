"""
Filing Wizard Test Suite
"""
import uuid
import pytest
from httpx import AsyncClient

MEDICAL_PROJECT = {
    "product_name": "CardioGuard Pro",
    "country": "India",
    "domain": "MEDICAL_DEVICE",
    "device_class": "Class B",
}

FOOD_PROJECT = {
    "product_name": "Omega Boost Supplement",
    "country": "US",
    "domain": "FOOD",
    "food_category": "Food Supplements",
}


class TestCreateProjectAuthenticated:
    @pytest.mark.asyncio
    async def test_create_project_authenticated(self, client, auth_headers):
        r = await client.post("/api/v1/filing-wizard/projects", json=MEDICAL_PROJECT, headers=auth_headers)
        assert r.status_code == 201, r.text

class TestCreateProjectUnauthenticated:
    @pytest.mark.asyncio
    async def test_create_project_unauthenticated(self, client):
        r = await client.post("/api/v1/filing-wizard/projects", json=MEDICAL_PROJECT)
        assert r.status_code == 401

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_b_cannot_get_tenant_a_project(self, client, auth_headers, other_tenant_headers):
        create_r = await client.post("/api/v1/filing-wizard/projects", json=MEDICAL_PROJECT, headers=auth_headers)
        assert create_r.status_code == 201
        project_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/filing-wizard/projects/{project_id}", headers=other_tenant_headers)
        assert r.status_code == 404

class TestGetProjectNotFound:
    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client, auth_headers):
        r = await client.get(f"/api/v1/filing-wizard/projects/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

class TestListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_authenticated(self, client, auth_headers):
        r = await client.get("/api/v1/filing-wizard/templates", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_templates_unauthenticated(self, client):
        r = await client.get("/api/v1/filing-wizard/templates")
        assert r.status_code == 401

class TestChecklistGeneration:
    @pytest.mark.asyncio
    async def test_checklist_generation_unauthenticated(self, client):
        r = await client.post(f"/api/v1/filing-wizard/projects/{uuid.uuid4()}/checklist/generate", json={})
        assert r.status_code == 401
