"""
Integration tests for API endpoints — health, auth, system, jobs.
Uses FastAPI test client with mocked dependencies.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestHealthEndpoints:
    """Health check endpoint tests."""

    @pytest.mark.asyncio
    async def test_liveness(self, client):
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_health_with_mocked_deps(self, client):
        """Health endpoint returns status when dependencies are mocked."""
        with (
            patch(
                "app.api.v1.health.check_database_health", new_callable=AsyncMock, return_value=True
            ),
            patch(
                "app.api.v1.health.check_redis_health", new_callable=AsyncMock, return_value=True
            ),
        ):
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["database"]["status"] == "healthy"
            assert data["services"]["redis"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_degraded_when_db_down(self, client):
        """Health reports degraded when database is unreachable."""
        with (
            patch(
                "app.api.v1.health.check_database_health",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.api.v1.health.check_redis_health", new_callable=AsyncMock, return_value=True
            ),
        ):
            response = await client.get("/health")
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["database"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_readiness_503_when_not_ready(self, client):
        """Readiness returns 503 when dependencies are down."""
        with (
            patch(
                "app.api.v1.health.check_database_health",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.api.v1.health.check_redis_health", new_callable=AsyncMock, return_value=False
            ),
        ):
            response = await client.get("/health/ready")
            assert response.status_code == 503


class TestAuthEndpoints:
    """Admin authentication tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Valid admin credentials return a JWT token."""
        response = await client.post(
            "/api/v1/admin/login",
            auth=("admin", "testpass123"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        response = await client.post(
            "/api/v1/admin/login",
            auth=("admin", "wrong-password"),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_username(self, client):
        """Wrong username returns 401."""
        response = await client.post(
            "/api/v1/admin/login",
            auth=("hacker", "testpass123"),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client):
        """Admin endpoints reject requests without auth."""
        response = await client.get("/api/v1/admin/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_token(self, client, admin_headers):
        """Admin endpoints accept valid JWT tokens."""
        response = await client.get("/api/v1/admin/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "admin"

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, client):
        """Admin endpoints reject invalid JWT tokens."""
        response = await client.get(
            "/api/v1/admin/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestSystemEndpoints:
    """System status and job management tests."""

    @pytest.mark.asyncio
    async def test_system_status_requires_auth(self, client):
        """System status rejects unauthenticated requests."""
        response = await client.get("/api/v1/system/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_system_status_with_auth(self, client, admin_headers):
        """System status returns data for authenticated admin."""
        with (
            patch(
                "app.api.v1.system.check_database_health", new_callable=AsyncMock, return_value=True
            ),
            patch(
                "app.api.v1.system.check_redis_health", new_callable=AsyncMock, return_value=True
            ),
        ):
            response = await client.get("/api/v1/system/status", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "version" in data["data"]
            assert "autonomy_enabled" in data["data"]
            assert "feature_flags" in data["data"]

    @pytest.mark.asyncio
    async def test_create_job(self, client, admin_headers):
        """Create a job via API."""
        response = await client.post(
            "/api/v1/system/jobs",
            json={
                "job_type": "test_job",
                "priority": 5,
                "payload": {"test": True},
                "max_attempts": 3,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job_type"] == "test_job"
        assert data["data"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_job_with_idempotency(self, client, admin_headers):
        """Duplicate idempotency keys are rejected."""
        job_data = {
            "job_type": "test",
            "idempotency_key": "unique-123",
        }
        # First creation succeeds
        resp1 = await client.post("/api/v1/system/jobs", json=job_data, headers=admin_headers)
        assert resp1.status_code == 201

        # Second with same key fails
        resp2 = await client.post("/api/v1/system/jobs", json=job_data, headers=admin_headers)
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_get_job(self, client, admin_headers):
        """Retrieve a job by ID."""
        # Create
        create_resp = await client.post(
            "/api/v1/system/jobs",
            json={"job_type": "test"},
            headers=admin_headers,
        )
        job_id = create_resp.json()["data"]["id"]

        # Get
        get_resp = await client.get(f"/api/v1/system/jobs/{job_id}", headers=admin_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["id"] == job_id

    @pytest.mark.asyncio
    async def test_transition_job_status(self, client, admin_headers):
        """Transition a job to a new status."""
        # Create
        create_resp = await client.post(
            "/api/v1/system/jobs",
            json={"job_type": "test"},
            headers=admin_headers,
        )
        job_id = create_resp.json()["data"]["id"]

        # Transition to running
        transition_resp = await client.put(
            f"/api/v1/system/jobs/{job_id}/status",
            json={"new_status": "running"},
            headers=admin_headers,
        )
        assert transition_resp.status_code == 200
        assert transition_resp.json()["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_invalid_job_status(self, client, admin_headers):
        """Invalid status value is rejected."""
        create_resp = await client.post(
            "/api/v1/system/jobs",
            json={"job_type": "test"},
            headers=admin_headers,
        )
        job_id = create_resp.json()["data"]["id"]

        resp = await client.put(
            f"/api/v1/system/jobs/{job_id}/status",
            json={"new_status": "banana"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_costs(self, client, admin_headers):
        """Cost summary endpoint returns valid data."""
        response = await client.get("/api/v1/system/costs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "daily_total" in data["data"]
        assert "monthly_total" in data["data"]


class TestApiResponseFormat:
    """Verify all responses use the standard envelope format."""

    @pytest.mark.asyncio
    async def test_success_envelope(self, client, admin_headers):
        resp = await client.get("/api/v1/admin/me", headers=admin_headers)
        data = resp.json()
        assert "success" in data
        assert "data" in data

    @pytest.mark.asyncio
    async def test_error_envelope(self, client):
        resp = await client.get("/api/v1/admin/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_request_id_header(self, client):
        resp = await client.get("/health/live")
        assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_custom_request_id_propagated(self, client):
        custom_id = "my-trace-id-123"
        resp = await client.get(
            "/health/live",
            headers={"X-Request-ID": custom_id},
        )
        assert resp.headers.get("x-request-id") == custom_id
