"""Document Editor Test Suite"""
import uuid
import pytest
from httpx import AsyncClient

DRAFT = {
    "title": "510k Submission Cover Letter",
    "content": "This document covers the premarket notification...",
    "document_type": "cover_letter",
    "country": "US",
    "domain": "MEDICAL_DEVICE",
}

class TestCreateDraftAuthenticated:
    @pytest.mark.asyncio
    async def test_create_draft(self, client: AsyncClient, auth_headers: dict):
        r = await client.post("/api/v1/document-editor/drafts", json=DRAFT, headers=auth_headers)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "id" in body
        assert body["title"] == DRAFT["title"]
        assert body["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_draft_blank_title(self, client: AsyncClient, auth_headers: dict):
        r = await client.post("/api/v1/document-editor/drafts", json={**DRAFT, "title": "  "}, headers=auth_headers)
        assert r.status_code == 422

class TestCreateDraftUnauthenticated:
    @pytest.mark.asyncio
    async def test_create_draft_unauthenticated(self, client: AsyncClient):
        r = await client.post("/api/v1/document-editor/drafts", json=DRAFT)
        assert r.status_code == 401

class TestListDrafts:
    @pytest.mark.asyncio
    async def test_list_drafts(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/document-editor/drafts", json=DRAFT, headers=auth_headers)
        r = await client.get("/api/v1/document-editor/drafts", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_drafts_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/v1/document-editor/drafts")
        assert r.status_code == 401

class TestGetDraft:
    @pytest.mark.asyncio
    async def test_get_draft(self, client: AsyncClient, auth_headers: dict):
        create_r = await client.post("/api/v1/document-editor/drafts", json=DRAFT, headers=auth_headers)
        draft_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/document-editor/drafts/{draft_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == draft_id

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.get(f"/api/v1/document-editor/drafts/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

class TestUpdateDraft:
    @pytest.mark.asyncio
    async def test_update_draft(self, client: AsyncClient, auth_headers: dict):
        create_r = await client.post("/api/v1/document-editor/drafts", json=DRAFT, headers=auth_headers)
        draft_id = create_r.json()["id"]
        r = await client.put(f"/api/v1/document-editor/drafts/{draft_id}", json={"title": "Updated Title"}, headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_update_draft_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.put(f"/api/v1/document-editor/drafts/{uuid.uuid4()}", json={"title": "X"}, headers=auth_headers)
        assert r.status_code == 404

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_b_cannot_get_tenant_a_draft(self, client: AsyncClient, auth_headers: dict, other_tenant_headers: dict):
        create_r = await client.post("/api/v1/document-editor/drafts", json=DRAFT, headers=auth_headers)
        draft_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/document-editor/drafts/{draft_id}", headers=other_tenant_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_b_list_does_not_show_tenant_a_drafts(self, client: AsyncClient, auth_headers: dict, other_tenant_headers: dict):
        unique = f"Secret-{uuid.uuid4().hex[:8]}"
        await client.post("/api/v1/document-editor/drafts", json={**DRAFT, "title": unique}, headers=auth_headers)
        r = await client.get("/api/v1/document-editor/drafts", headers=other_tenant_headers)
        assert r.status_code == 200
        assert unique not in [d["title"] for d in r.json()]

class TestVersions:
    @pytest.mark.asyncio
    async def test_create_and_list_versions(self, client: AsyncClient, auth_headers: dict):
        create_r = await client.post("/api/v1/document-editor/drafts", json=DRAFT, headers=auth_headers)
        draft_id = create_r.json()["id"]
        v = await client.post(f"/api/v1/document-editor/drafts/{draft_id}/versions", json={"content": "v1 content", "comment": "first save"}, headers=auth_headers)
        assert v.status_code == 201
        r = await client.get(f"/api/v1/document-editor/drafts/{draft_id}/versions", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    @pytest.mark.asyncio
    async def test_versions_unauthenticated(self, client: AsyncClient):
        r = await client.get(f"/api/v1/document-editor/drafts/{uuid.uuid4()}/versions")
        assert r.status_code == 401
