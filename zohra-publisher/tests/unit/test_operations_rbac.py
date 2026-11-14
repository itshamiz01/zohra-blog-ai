"""
Unit tests for Zohra Part 10 — Operations, RBAC, Secrets, Alerts, CostGovernor, Backup, and Recovery.
"""

from __future__ import annotations

import datetime
import uuid
from datetime import UTC
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    AuthenticatedUserContext,
    is_role_sufficient,
)
from app.db.models.model_usage import ModelUsage
from app.db.models.operations import (
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    OutboxStatus,
    UserRole,
)
from app.db.models.sites import Site
from app.services.alerts import AlertManager
from app.services.backup import BackupManager, BackupVerificationError
from app.services.governor import CostGovernor, CostMode
from app.services.notifications import is_within_quiet_hours
from app.services.outbox import OutboxDispatcher, register_event_handler
from app.services.recovery import RecoveryManager
from app.services.secrets import (
    EncryptedDatabaseSecretProvider,
    derive_encryption_key,
    mask_secret,
)


# ── 1. RBAC Tests ─────────────────────────────────────────────────────

def test_role_sufficiency_hierarchy():
    # SUPER_ADMIN satisfies everything
    assert is_role_sufficient(UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN)
    assert is_role_sufficient(UserRole.SUPER_ADMIN, UserRole.ADMIN)
    assert is_role_sufficient(UserRole.SUPER_ADMIN, UserRole.EDITOR)
    assert is_role_sufficient(UserRole.SUPER_ADMIN, UserRole.ANALYST)
    assert is_role_sufficient(UserRole.SUPER_ADMIN, UserRole.VIEWER)

    # ADMIN satisfies editor and viewer, but not super_admin
    assert not is_role_sufficient(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    assert is_role_sufficient(UserRole.ADMIN, UserRole.ADMIN)
    assert is_role_sufficient(UserRole.ADMIN, UserRole.EDITOR)

    # VIEWER cannot satisfy higher roles
    assert not is_role_sufficient(UserRole.VIEWER, UserRole.EDITOR)
    assert not is_role_sufficient(UserRole.VIEWER, UserRole.ADMIN)
    assert is_role_sufficient(UserRole.VIEWER, UserRole.VIEWER)


def test_user_context_site_access():
    site_a = uuid.uuid4()
    site_b = uuid.uuid4()

    # User with specific site role on site_a
    context = AuthenticatedUserContext(
        user_id="user_123",
        username="editor_jane",
        global_role=UserRole.VIEWER,
        site_roles={site_a: UserRole.EDITOR},
    )

    # On site A, jane can edit
    assert context.can_access_site(site_a, UserRole.EDITOR)
    assert context.can_access_site(site_a, UserRole.VIEWER)
    assert not context.can_access_site(site_a, UserRole.ADMIN)

    # On site B, jane only has her global role (VIEWER)
    assert context.can_access_site(site_b, UserRole.VIEWER)
    assert not context.can_access_site(site_b, UserRole.EDITOR)


def test_super_admin_universal_site_access():
    site_random = uuid.uuid4()
    admin_ctx = AuthenticatedUserContext(
        user_id="admin_1",
        username="super_admin",
        global_role=UserRole.SUPER_ADMIN,
    )
    assert admin_ctx.can_access_site(site_random, UserRole.SUPER_ADMIN)
    assert admin_ctx.can_access_site(site_random, UserRole.ADMIN)
    assert admin_ctx.can_access_site(site_random, UserRole.EDITOR)


# ── 2. Secrets & Encryption Tests ─────────────────────────────────────

def test_secret_masking():
    assert mask_secret(None) == "[NOT_CONFIGURED]"
    assert mask_secret("") == "[NOT_CONFIGURED]"
    assert mask_secret("short") == "********"
    assert mask_secret("wp_app_password_secret_key_12345") == "wp_...345"


@pytest.mark.asyncio
async def test_encrypted_secret_provider_roundtrip(db_session: AsyncSession):
    provider = EncryptedDatabaseSecretProvider(db_session, master_key="test_master_key_123456789012345")
    site_id = uuid.uuid4()

    # Store secret
    version_1 = await provider.set_secret("WP_APPLICATION_PASSWORD", "super_secret_wp_pass_xyz", site_id=site_id)
    assert version_1 == 1

    # Decrypt and retrieve
    retrieved = await provider.get_secret("WP_APPLICATION_PASSWORD", site_id=site_id)
    assert retrieved == "super_secret_wp_pass_xyz"

    # Metadata check: ensure plaintext is never in metadata
    meta = await provider.list_secret_metadata(site_id=site_id)
    assert len(meta) == 1
    assert meta[0]["key_name"] == "WP_APPLICATION_PASSWORD"
    assert meta[0]["version"] == 1
    assert "super_secret_wp_pass_xyz" not in str(meta[0])

    # Rotate secret
    version_2 = await provider.rotate_secret("WP_APPLICATION_PASSWORD", "rotated_new_pass_999", site_id=site_id)
    assert version_2 == 2

    # New secret active
    retrieved_new = await provider.get_secret("WP_APPLICATION_PASSWORD", site_id=site_id)
    assert retrieved_new == "rotated_new_pass_999"


# ── 3. AlertManager & Notifications ───────────────────────────────────

def test_quiet_hours_evaluation():
    # Regular window 22:00 to 08:00
    assert is_within_quiet_hours(datetime.time(23, 30), "22:00", "08:00")
    assert is_within_quiet_hours(datetime.time(3, 0), "22:00", "08:00")
    assert not is_within_quiet_hours(datetime.time(14, 0), "22:00", "08:00")

    # Daytime quiet window 13:00 to 15:00
    assert is_within_quiet_hours(datetime.time(14, 30), "13:00", "15:00")
    assert not is_within_quiet_hours(datetime.time(11, 0), "13:00", "15:00")


@pytest.mark.asyncio
async def test_alert_deduplication_and_cooldown(db_session: AsyncSession):
    alert_mgr = AlertManager(db_session)
    site_id = uuid.uuid4()

    # Emit first alert
    a1 = await alert_mgr.emit_alert(
        title="WordPress Connection Timed Out",
        message="Failed connecting to WP REST API",
        category=AlertCategory.INTEGRATION,
        severity=AlertSeverity.HIGH,
        source="wp_client",
        site_id=site_id,
        cooldown_minutes=15,
    )
    assert a1.occurrence_count == 1
    assert a1.status == AlertStatus.OPEN.value

    # Emit identical alert immediately -> should deduplicate and increment occurrence_count
    a2 = await alert_mgr.emit_alert(
        title="WordPress Connection Timed Out",
        message="Failed connecting to WP REST API (repeated)",
        category=AlertCategory.INTEGRATION,
        severity=AlertSeverity.HIGH,
        source="wp_client",
        site_id=site_id,
        cooldown_minutes=15,
    )
    assert a2.id == a1.id
    assert a2.occurrence_count == 2

    # Acknowledge and resolve lifecycle
    ack = await alert_mgr.acknowledge_alert(a1.id, "operator_bob")
    assert ack.status == AlertStatus.ACKNOWLEDGED.value
    assert ack.acknowledged_by == "operator_bob"

    res = await alert_mgr.resolve_alert(a1.id, "operator_bob")
    assert res.status == AlertStatus.RESOLVED.value


# ── 4. CostGovernor & Spending Degradation ─────────────────────────────

@pytest.mark.asyncio
async def test_cost_governor_modes_and_gating(db_session: AsyncSession):
    governor = CostGovernor(db_session)

    # Normal mode check
    metrics = await governor.get_spend_metrics()
    assert metrics["current_mode"] in ("NORMAL", "ECONOMY", "ESSENTIAL_ONLY")

    # In NORMAL mode, both general and essential tasks allowed
    allowed, mode, reason = await governor.check_budget_permission("exploratory_research")
    assert allowed is True

    # Record simulated high spend in ModelUsage to trigger ESSENTIAL_ONLY
    fake_usage = ModelUsage(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=500000,
        output_tokens=100000,
        total_tokens=600000,
        estimated_total_cost=200.0,  # Exceeds default $50 daily budget
        currency="USD",
    )
    db_session.add(fake_usage)
    await db_session.flush()

    # Now verify degradation mode
    updated_metrics = await governor.get_spend_metrics()
    assert updated_metrics["current_mode"] == CostMode.ESSENTIAL_ONLY.value

    # Exploratory tasks must be BLOCKED
    allowed_exp, mode_exp, reason_exp = await governor.check_budget_permission("exploratory_research")
    assert allowed_exp is False
    assert mode_exp == CostMode.ESSENTIAL_ONLY

    # Essential tasks (safety, rollback, verification) must be PERMITTED
    allowed_safety, mode_safety, _ = await governor.check_budget_permission("safety_correction")
    assert allowed_safety is True

    allowed_rb, mode_rb, _ = await governor.check_budget_permission("critical_rollback")
    assert allowed_rb is True


# ── 5. Backup & Recovery Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_backup_create_verify_and_restore(tmp_path: Path):
    backup_mgr = BackupManager(backup_dir=tmp_path, encryption_key="backup_test_secret_1234567890123")

    # Create encrypted backup
    manifest = await backup_mgr.create_backup(db_url="sqlite:///nonexistent.db", encrypt=True)
    assert manifest["is_encrypted"] is True
    assert manifest["size_bytes"] > 0
    assert manifest["verification_status"] == "VERIFIED"

    # Verify backup
    verification = backup_mgr.verify_backup(manifest["backup_name"])
    assert verification["status"] == "VALID"

    # Test sandbox restore
    restore_ok = backup_mgr.test_restore_in_sandbox(manifest["backup_name"])
    assert restore_ok is True

    # Test tampering detection
    target_file = tmp_path / manifest["backup_name"]
    target_file.write_bytes(b"CORRUPTED_BYTES_HERE")
    with pytest.raises(BackupVerificationError):
        backup_mgr.verify_backup(manifest["backup_name"])


# ── 6. Autonomy Kill Switch & Pre-Publish Gate ─────────────────────────

@pytest.mark.asyncio
async def test_autonomy_kill_switch_and_recovery(db_session: AsyncSession):
    recovery = RecoveryManager(db_session)

    # Initial state
    assert not RecoveryManager.is_autonomy_paused()

    # Pause autonomy
    RecoveryManager.pause_autonomy()
    assert RecoveryManager.is_autonomy_paused()

    # Site check should fail while autonomy paused
    site_id = uuid.uuid4()
    site = Site(
        id=site_id,
        name="Test Tech Blog",
        domain="techtest.com",
        niche="technology",
        enabled=True,
        autonomous_publishing_enabled=True,
    )
    db_session.add(site)
    await db_session.flush()

    allowed, reason = await recovery.is_site_autonomous(site_id)
    assert allowed is False
    assert "pause is ACTIVE" in reason

    # Resume autonomy
    RecoveryManager.resume_autonomy()
    assert not RecoveryManager.is_autonomy_paused()

    allowed_after, _ = await recovery.is_site_autonomous(site_id)
    assert allowed_after is True


# ── 7. Transactional Outbox Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_transactional_outbox_dispatch(db_session: AsyncSession):
    dispatcher = OutboxDispatcher(db_session)
    event_dispatched_payload = None

    async def handle_article_approved(payload: dict):
        nonlocal event_dispatched_payload
        event_dispatched_payload = payload

    register_event_handler("ArticleApproved", handle_article_approved)

    # Record event inside business transaction
    art_id = str(uuid.uuid4())
    event = await dispatcher.record_event(
        event_type="ArticleApproved",
        aggregate_type="Article",
        aggregate_id=art_id,
        payload={"article_id": art_id, "score": 94.5},
    )
    assert event.status == OutboxStatus.PENDING.value

    # Dispatch pending events
    count = await dispatcher.dispatch_pending()
    assert count >= 1
    assert event.status == OutboxStatus.DISPATCHED.value
    assert event.published_at is not None
    assert event_dispatched_payload == {"article_id": art_id, "score": 94.5}
