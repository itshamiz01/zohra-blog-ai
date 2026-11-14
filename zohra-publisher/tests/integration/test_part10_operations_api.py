"""
Integration tests for Part 10 — Operations, Autonomy, Alerts, Backups, Secrets, and RBAC API.
"""

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_operations_snapshot_and_autonomy_api(client: AsyncClient, admin_headers: dict[str, str]):
    # 1. Snapshot endpoint
    snap_res = await client.get("/api/v1/operations/snapshot", headers=admin_headers)
    assert snap_res.status_code == 200
    snap_data = snap_res.json()
    assert snap_data["success"] is True
    assert "autonomy_status" in snap_data["data"]
    assert "spend_today_usd" in snap_data["data"]

    # 2. Autonomy status endpoint
    aut_res = await client.get("/api/v1/operations/autonomy", headers=admin_headers)
    assert aut_res.status_code == 200
    aut_data = aut_res.json()
    assert aut_data["success"] is True
    assert aut_data["data"]["autonomy_status"] in ("ACTIVE", "PAUSED")

    # 3. Emergency Kill Switch via /operations/autonomy/pause
    pause_res = await client.post(
        "/api/v1/operations/autonomy/pause",
        headers=admin_headers,
        json={"reason": "Emergency security testing drill"},
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["autonomy_status"] == "PAUSED"

    # Verify status changed
    status_check = await client.get("/api/v1/operations/autonomy", headers=admin_headers)
    assert status_check.json()["data"]["kill_switch_active"] is True

    # 4. Resume Autonomy via /operations/autonomy/resume
    resume_res = await client.post(
        "/api/v1/operations/autonomy/resume",
        headers=admin_headers,
        json={"reason": "Testing drill completed successfully"},
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["autonomy_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_system_autonomy_alias_endpoints(client: AsyncClient, admin_headers: dict[str, str]):
    # Prompt #15 specific endpoint aliases
    pause_res = await client.post("/api/v1/system/autonomy/pause", headers=admin_headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["autonomy_status"] == "PAUSED"

    resume_res = await client.post("/api/v1/system/autonomy/resume", headers=admin_headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["autonomy_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_alerts_lifecycle_api(client: AsyncClient, admin_headers: dict[str, str]):
    # 1. Emit alert
    emit_res = await client.post(
        "/api/v1/alerts",
        headers=admin_headers,
        json={
            "title": "Search Console API Quota Warning",
            "message": "Quota limit reached 85%",
            "category": "INTEGRATION",
            "severity": "WARNING",
            "source": "gsc_poller",
        },
    )
    assert emit_res.status_code == 200
    alert_id = emit_res.json()["data"]["id"]

    # 2. List alerts
    list_res = await client.get("/api/v1/alerts", headers=admin_headers)
    assert list_res.status_code == 200
    alerts = list_res.json()["data"]
    assert any(a["id"] == alert_id for a in alerts)

    # 3. Acknowledge alert
    ack_res = await client.post(f"/api/v1/alerts/{alert_id}/acknowledge", headers=admin_headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "ACKNOWLEDGED"

    # 4. Resolve alert
    res_res = await client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=admin_headers)
    assert res_res.status_code == 200
    assert res_res.json()["data"]["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_users_and_rbac_api(client: AsyncClient, admin_headers: dict[str, str]):
    # 1. Current user profile
    me_res = await client.get("/api/v1/users/me", headers=admin_headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["global_role"] == "SUPER_ADMIN"

    # 2. Create user with EDITOR role
    unique_user = f"editor_{uuid.uuid4().hex[:6]}"
    create_res = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": unique_user,
            "email": f"{unique_user}@example.com",
            "password": "SecurePassword123!",
            "role": "EDITOR",
            "is_active": True,
        },
    )
    assert create_res.status_code == 200
    user_data = create_res.json()["data"]
    assert user_data["username"] == unique_user
    assert user_data["role"] == "EDITOR"

    # 3. List users
    users_list = await client.get("/api/v1/users", headers=admin_headers)
    assert users_list.status_code == 200
    assert len(users_list.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_secrets_api_zero_plaintext_leakage(client: AsyncClient, admin_headers: dict[str, str]):
    site_id = str(uuid.uuid4())

    # 1. Store secret
    store_res = await client.post(
        "/api/v1/secrets",
        headers=admin_headers,
        json={
            "key_name": "WP_APPLICATION_PASSWORD",
            "value": "top_secret_token_never_leak_999",
            "site_id": site_id,
        },
    )
    assert store_res.status_code == 200
    assert store_res.json()["data"]["version"] == 1

    # 2. List secrets metadata — verify plaintext is NEVER returned
    list_res = await client.get(f"/api/v1/secrets?site_id={site_id}", headers=admin_headers)
    assert list_res.status_code == 200
    records = list_res.json()["data"]
    assert len(records) >= 1
    assert "top_secret_token_never_leak_999" not in str(list_res.text)


@pytest.mark.asyncio
async def test_backups_api_lifecycle(client: AsyncClient, admin_headers: dict[str, str]):
    # 1. Trigger encrypted backup
    create_res = await client.post("/api/v1/backups?encrypt=true", headers=admin_headers)
    assert create_res.status_code == 200
    backup_data = create_res.json()["data"]
    backup_name = backup_data["backup_name"]
    assert backup_data["is_encrypted"] is True

    # 2. List backups
    list_res = await client.get("/api/v1/backups", headers=admin_headers)
    assert list_res.status_code == 200
    assert any(b["backup_name"] == backup_name for b in list_res.json()["data"])

    # 3. Verify backup
    verify_res = await client.post(f"/api/v1/backups/{backup_name}/verify", headers=admin_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["status"] == "VALID"

    # 4. Test sandbox restore
    restore_res = await client.post(f"/api/v1/backups/{backup_name}/test-restore", headers=admin_headers)
    assert restore_res.status_code == 200
    assert restore_res.json()["data"]["sandbox_restore_success"] is True


@pytest.mark.asyncio
async def test_command_center_console_ui(client: AsyncClient):
    """Verify /console serves the interactive Command Center UI."""
    res = await client.get("/console")
    assert res.status_code == 200
    assert "ZOHRA PUBLISHING COMMAND CENTER" in res.text
    assert "EMERGENCY PAUSE" in res.text
