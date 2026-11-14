"""
Integration tests for database models — CRUD on all foundational tables.
Uses in-memory SQLite via the db_session fixture.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db.models.agent_runs import AgentRun
from app.db.models.audit_logs import AuditLog
from app.db.models.jobs import Job
from app.db.models.model_usage import ModelUsage
from app.db.models.system_errors import SystemError
from app.db.models.system_settings import SystemSetting


class TestSystemSettings:
    @pytest.mark.asyncio
    async def test_create_and_read(self, db_session):
        setting = SystemSetting(
            key="test_key",
            value="test_value",
            value_type="string",
            description="A test setting",
            is_secret=False,
        )
        db_session.add(setting)
        await db_session.flush()

        result = await db_session.execute(
            select(SystemSetting).where(SystemSetting.key == "test_key")
        )
        found = result.scalar_one()
        assert found.value == "test_value"
        assert found.is_secret is False
        assert found.created_at is not None

    @pytest.mark.asyncio
    async def test_secret_flag(self, db_session):
        setting = SystemSetting(
            key="api_key",
            value="secret123",
            value_type="string",
            is_secret=True,
        )
        db_session.add(setting)
        await db_session.flush()

        result = await db_session.execute(
            select(SystemSetting).where(SystemSetting.key == "api_key")
        )
        found = result.scalar_one()
        assert found.is_secret is True


class TestAgentRuns:
    @pytest.mark.asyncio
    async def test_create_agent_run(self, db_session):
        run = AgentRun(
            agent_name="scout",
            agent_version="0.1.0",
            task_type="discover_topics",
            status="running",
            started_at=datetime.now(UTC),
        )
        db_session.add(run)
        await db_session.flush()

        result = await db_session.execute(select(AgentRun).where(AgentRun.agent_name == "scout"))
        found = result.scalar_one()
        assert found.status == "running"
        assert found.agent_version == "0.1.0"

    @pytest.mark.asyncio
    async def test_agent_run_with_cost(self, db_session):
        run = AgentRun(
            agent_name="writer",
            agent_version="0.1.0",
            task_type="write_article",
            status="completed",
            provider="openai",
            model="gpt-4",
            input_tokens=500,
            output_tokens=1200,
            estimated_cost=0.034,
            duration_ms=4500,
        )
        db_session.add(run)
        await db_session.flush()

        result = await db_session.execute(select(AgentRun).where(AgentRun.agent_name == "writer"))
        found = result.scalar_one()
        assert found.estimated_cost == 0.034
        assert found.input_tokens == 500


class TestModelUsage:
    @pytest.mark.asyncio
    async def test_record_usage(self, db_session):
        usage = ModelUsage(
            provider="openai",
            model="gpt-4",
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            estimated_input_cost=0.003,
            estimated_output_cost=0.006,
            estimated_total_cost=0.009,
            operation="article_generation",
        )
        db_session.add(usage)
        await db_session.flush()

        result = await db_session.execute(select(ModelUsage).where(ModelUsage.provider == "openai"))
        found = result.scalar_one()
        assert found.total_tokens == 300
        assert found.estimated_total_cost == 0.009


class TestSystemErrors:
    @pytest.mark.asyncio
    async def test_log_error(self, db_session):
        error = SystemError(
            error_code="WP_TIMEOUT",
            error_type="ExternalServiceError",
            severity="error",
            component="wordpress_publisher",
            operation="publish_article",
            message="Connection timed out after 30s",
            stack_trace="Traceback...",
            resolved=False,
        )
        db_session.add(error)
        await db_session.flush()

        result = await db_session.execute(
            select(SystemError).where(SystemError.error_code == "WP_TIMEOUT")
        )
        found = result.scalar_one()
        assert found.resolved is False
        assert found.severity == "error"


class TestAuditLogs:
    @pytest.mark.asyncio
    async def test_create_audit_log(self, db_session):
        audit = AuditLog(
            actor_type="human",
            actor_id="admin",
            action="workflow_transition",
            entity_type="article",
            entity_id=uuid.uuid4(),
            previous_state="drafted",
            new_state="published",
        )
        db_session.add(audit)
        await db_session.flush()

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "workflow_transition")
        )
        found = result.scalar_one()
        assert found.previous_state == "drafted"
        assert found.new_state == "published"


class TestJobs:
    @pytest.mark.asyncio
    async def test_create_job(self, db_session):
        job = Job(
            job_type="article_generation",
            status="pending",
            priority=5,
            payload={"topic_id": "abc123"},
            max_attempts=3,
        )
        db_session.add(job)
        await db_session.flush()

        result = await db_session.execute(select(Job).where(Job.job_type == "article_generation"))
        found = result.scalar_one()
        assert found.status == "pending"
        assert found.priority == 5
        assert found.payload == {"topic_id": "abc123"}

    @pytest.mark.asyncio
    async def test_job_idempotency_key(self, db_session):
        job = Job(
            job_type="test",
            status="pending",
            priority=0,
            idempotency_key="unique-key-123",
        )
        db_session.add(job)
        await db_session.flush()

        result = await db_session.execute(
            select(Job).where(Job.idempotency_key == "unique-key-123")
        )
        found = result.scalar_one()
        assert found.idempotency_key == "unique-key-123"

    @pytest.mark.asyncio
    async def test_job_status_transition(self, db_session):
        job = Job(job_type="test", status="pending", priority=0)
        db_session.add(job)
        await db_session.flush()

        # Transition to running
        job.status = "running"
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        await db_session.flush()

        result = await db_session.execute(select(Job).where(Job.id == job.id))
        found = result.scalar_one()
        assert found.status == "running"
        assert found.attempts == 1
