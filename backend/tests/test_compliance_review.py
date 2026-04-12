"""Compliance Review Test Suite"""
import uuid
import pytest
from httpx import AsyncClient

REVIEW = {
    "title": "FDA 510k Compliance Check",
    "document_content": "This medical device submission covers safety and efficacy data...",
    "country": "US",
    "domain": "MEDICAL_DEVICE",
    "regulation": "21 CFR Part 807",
}

class TestCreateReview:
    @pytest.mark.asyncio
    async def test_create_review_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.post("/api/v1/compliance-review/reviews", json=REVIEW, headers=auth_headers)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "id" in body
        assert body["status"] == "pending"
        assert body["score"] is None

    @pytest.mark.asyncio
    async def test_create_review_unauthenticated(self, client: AsyncClient):
        r = await client.post("/api/v1/compliance-review/reviews", json=REVIEW)
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_create_review_blank_title(self, client: AsyncClient, auth_headers: dict):
        r = await client.post("/api/v1/compliance-review/reviews", json={**REVIEW, "title": "  "}, headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_review_blank_content(self, client: AsyncClient, auth_headers: dict):
        r = await client.post("/api/v1/compliance-review/reviews", json={**REVIEW, "document_content": "  "}, headers=auth_headers)
        assert r.status_code == 422

class TestListReviews:
    @pytest.mark.asyncio
    async def test_list_reviews(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/compliance-review/reviews", json=REVIEW, headers=auth_headers)
        r = await client.get("/api/v1/compliance-review/reviews", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_reviews_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/v1/compliance-review/reviews")
        assert r.status_code == 401

class TestGetReview:
    @pytest.mark.asyncio
    async def test_get_review(self, client: AsyncClient, auth_headers: dict):
        create_r = await client.post("/api/v1/compliance-review/reviews", json=REVIEW, headers=auth_headers)
        review_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/compliance-review/reviews/{review_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == review_id

    @pytest.mark.asyncio
    async def test_get_review_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.get(f"/api/v1/compliance-review/reviews/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_review_unauthenticated(self, client: AsyncClient):
        r = await client.get(f"/api/v1/compliance-review/reviews/{uuid.uuid4()}")
        assert r.status_code == 401

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_b_cannot_get_tenant_a_review(self, client: AsyncClient, auth_headers: dict, other_tenant_headers: dict):
        create_r = await client.post("/api/v1/compliance-review/reviews", json=REVIEW, headers=auth_headers)
        review_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/compliance-review/reviews/{review_id}", headers=other_tenant_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_b_list_does_not_show_tenant_a_reviews(self, client: AsyncClient, auth_headers: dict, other_tenant_headers: dict):
        unique = f"Secret-{uuid.uuid4().hex[:8]}"
        await client.post("/api/v1/compliance-review/reviews", json={**REVIEW, "title": unique}, headers=auth_headers)
        r = await client.get("/api/v1/compliance-review/reviews", headers=other_tenant_headers)
        assert r.status_code == 200
        assert unique not in [x["title"] for x in r.json()]

class TestDeleteReview:
    @pytest.mark.asyncio
    async def test_delete_review(self, client: AsyncClient, auth_headers: dict):
        create_r = await client.post("/api/v1/compliance-review/reviews", json=REVIEW, headers=auth_headers)
        review_id = create_r.json()["id"]
        r = await client.delete(f"/api/v1/compliance-review/reviews/{review_id}", headers=auth_headers)
        assert r.status_code == 204
        r2 = await client.get(f"/api/v1/compliance-review/reviews/{review_id}", headers=auth_headers)
        assert r2.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_review_not_found(self, client: AsyncClient, auth_headers: dict):
        r = await client.delete(f"/api/v1/compliance-review/reviews/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthenticated(self, client: AsyncClient):
        r = await client.delete(f"/api/v1/compliance-review/reviews/{uuid.uuid4()}")
        assert r.status_code == 401
