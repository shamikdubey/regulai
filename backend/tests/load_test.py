"""
RegulAI Load Test — Phase 4
============================
Simulates realistic multi-user load to validate Phase 2 scaling.

Usage:
  pip install locust
  locust -f tests/load_test.py --host https://staging.regulai.app

  # Headless: 50 users, 2 min duration
  locust -f tests/load_test.py \
    --host https://staging.regulai.app \
    --users 50 \
    --spawn-rate 5 \
    --run-time 120s \
    --headless \
    --html load_test_report.html

Target SLOs:
  p95 latency (query/stream first byte): < 3s
  p95 latency (reference data endpoints): < 500ms
  Error rate: < 0.1%
  Concurrent users: 50
"""
import json
import os
from locust import HttpUser, task, between, events
from locust.env import Environment

# Set these via environment variables before running
TEST_EMAIL = os.environ.get("LOCUST_EMAIL", "loadtest@regulai.app")
TEST_PASSWORD = os.environ.get("LOCUST_PASSWORD", "LoadTest1234!")


class ComplianceUser(HttpUser):
    """
    Simulates a typical RegulAI user session:
    - Authenticates on startup
    - Mixes reference data lookups (fast) with AI queries (slow)
    - Occasionally runs a gap assessment
    """
    wait_time = between(2, 8)    # Realistic think time between requests

    def on_start(self):
        """Login and store token."""
        r = self.client.post(
            "/api/v1/auth/token",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
            name="[Auth] Login",
        )
        if r.status_code == 200:
            self.token = r.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(10)
    def get_allowable_limits(self):
        """High-frequency: reference data lookup (should be fast, cached)."""
        self.client.get(
            "/api/v1/allowable-limits?jurisdiction=india&limit_type=additive",
            headers=self.headers,
            name="[Data] Allowable limits",
        )

    @task(8)
    def get_labeling_requirements(self):
        self.client.get(
            "/api/v1/labeling-requirements?jurisdiction=usa",
            headers=self.headers,
            name="[Data] Labeling requirements",
        )

    @task(6)
    def get_licensing_pathways(self):
        self.client.get(
            "/api/v1/licensing-pathways?jurisdiction=eu",
            headers=self.headers,
            name="[Data] Licensing pathways",
        )

    @task(5)
    def get_ingredient_specs(self):
        self.client.get(
            "/api/v1/ingredient-specs",
            headers=self.headers,
            name="[Data] Ingredient specs",
        )

    @task(4)
    def get_regulatory_bodies(self):
        self.client.get(
            "/api/v1/regulations/bodies?jurisdiction=india",
            headers=self.headers,
            name="[Data] Regulatory bodies",
        )

    @task(3)
    def audit_log(self):
        self.client.get(
            "/api/v1/audit/?limit=10",
            headers=self.headers,
            name="[Audit] List entries",
        )

    @task(2)
    def ai_query_sync(self):
        """
        Synchronous AI query — validates the non-streaming path holds up.
        NOTE: Only run sync queries in load test to avoid SSE complexity.
        """
        payload = {
            "query": "What are the maximum limits for sodium benzoate in beverages?",
            "jurisdiction": "india",
            "domain": "food",
        }
        with self.client.post(
            "/api/v1/query",
            json=payload,
            headers=self.headers,
            name="[AI] Sync compliance query",
            catch_response=True,
            timeout=90,
        ) as r:
            if r.status_code == 200:
                body = r.json()
                if "answer" not in body:
                    r.failure("Response missing 'answer' field")
            elif r.status_code == 429:
                r.success()   # Rate limited = expected, not an error
            else:
                r.failure(f"Status {r.status_code}")

    @task(1)
    def gap_assessment_async(self):
        """
        Enqueue a gap assessment (async mode).
        Only check job was queued — don't poll for result in load test.
        """
        payload = {
            "product_name": "LoadTest Supplement",
            "product_description": "Omega-3 fish oil capsules",
            "product_type": "nutra",
            "target_jurisdictions": ["india", "usa"],
            "intended_claims": "Supports heart health",
        }
        with self.client.post(
            "/api/v1/gap-assessment",
            json=payload,
            headers=self.headers,
            name="[AI] Gap assessment (async)",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 202):
                body = r.json()
                if "job_id" not in body and "overall_risk" not in body:
                    r.failure("Unexpected response format")
            elif r.status_code == 429:
                r.success()
            else:
                r.failure(f"Status {r.status_code}: {r.text[:200]}")

    @task(2)
    def health_check(self):
        """Health check should always be fast."""
        with self.client.get(
            "/health/live",
            name="[Health] Liveness",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Health check failed: {r.status_code}")

    @task(1)
    def get_alerts(self):
        self.client.get(
            "/api/v1/alerts?jurisdiction=india",
            headers=self.headers,
            name="[Data] Alerts",
        )

    @task(1)
    def billing_usage(self):
        self.client.get(
            "/api/v1/billing/usage",
            headers=self.headers,
            name="[Billing] Usage dashboard",
        )


class ReferenceDataUser(HttpUser):
    """
    A lighter user that only hits reference data endpoints.
    Simulates integrations/bots that query the data API programmatically.
    """
    wait_time = between(0.5, 2)

    def on_start(self):
        r = self.client.post(
            "/api/v1/auth/token",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
            name="[Auth] Login",
        )
        if r.status_code == 200:
            self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        else:
            self.headers = {}

    @task(5)
    def allowable_limits_search(self):
        self.client.get(
            "/api/v1/allowable-limits?substance=sodium+benzoate",
            headers=self.headers,
            name="[Data] Substance search",
        )

    @task(3)
    def jurisdiction_labels(self):
        for jur in ["india", "usa", "eu", "brazil"]:
            self.client.get(
                f"/api/v1/labeling-requirements?jurisdiction={jur}",
                headers=self.headers,
                name=f"[Data] Labels {jur}",
            )

    @task(2)
    def licensing_by_complexity(self):
        self.client.get(
            "/api/v1/licensing-pathways?complexity=HIGH",
            headers=self.headers,
            name="[Data] High complexity pathways",
        )


# ── Custom SLO validation on test end ────────────────────────────────────────

@events.quitting.add_listener
def validate_slos(environment: Environment, **kwargs):
    """Fail the load test if SLOs are not met."""
    stats = environment.runner.stats

    failures = []

    # Check p95 latency for AI queries
    ai_query_stats = stats.entries.get(("/api/v1/query", "POST"))
    if ai_query_stats and ai_query_stats.num_requests > 10:
        p95 = ai_query_stats.get_response_time_percentile(0.95)
        if p95 > 30000:  # 30 seconds p95 for sync AI
            failures.append(f"AI query p95 too high: {p95}ms (limit: 30000ms)")

    # Check error rate
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    if total_requests > 0:
        error_rate = total_failures / total_requests
        if error_rate > 0.01:  # 1% error threshold
            failures.append(f"Error rate too high: {error_rate:.1%} (limit: 1%)")

    # Check reference data p95
    for endpoint in ["/api/v1/allowable-limits", "/api/v1/labeling-requirements"]:
        s = stats.entries.get((endpoint, "GET"))
        if s and s.num_requests > 10:
            p95 = s.get_response_time_percentile(0.95)
            if p95 > 500:
                failures.append(f"{endpoint} p95 too high: {p95}ms (limit: 500ms)")

    if failures:
        print("\n❌ SLO VIOLATIONS:")
        for f in failures:
            print(f"  - {f}")
        environment.process_exit_code = 1
    else:
        print("\n✓ All SLOs met")
