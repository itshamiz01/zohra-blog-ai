"""Seed initial data for Zohra OS Command Center demonstration."""
import asyncio
import uuid
from app.db.session import get_session_factory
from app.db.models.sites import Site
from app.db.models.operations import User, UserRole, Alert, AlertSeverity, AlertCategory, AlertStatus
from app.core.config import get_settings

async def seed():
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 1. Admin user
        from sqlalchemy import select
        res = await session.execute(select(User).where(User.username == "admin"))
        if not res.scalar_one_or_none():
            admin_user = User(
                username="admin",
                email="admin@zohra.ai",
                hashed_password=settings.ADMIN_PASSWORD_HASH,
                role=UserRole.SUPER_ADMIN.value,
                is_active=True
            )
            session.add(admin_user)
            print("Added admin user")

        # 2. Sample Sites
        res = await session.execute(select(Site).where(Site.domain == "neuralhorizon.io"))
        if not res.scalar_one_or_none():
            site1 = Site(
                name="Neural Horizon Tech",
                domain="neuralhorizon.io",
                niche="Artificial Intelligence & Autonomous Systems",
                description="Deep coverage on AI agents, neural systems, and enterprise automation.",
                default_language="en",
                primary_country="global",
                target_audiences=["AI Researchers", "Founders", "Engineers"],
                enabled=True,
                publishing_enabled=True,
                autonomous_publishing_enabled=True,
                max_posts_per_day=4,
                minimum_publish_interval_minutes=90
            )
            session.add(site1)

            site2 = Site(
                name="GreenPulse Review",
                domain="greenpulse.org",
                niche="Clean Tech & Energy Transition",
                description="Analysis of clean energy investments and renewable technology.",
                default_language="en",
                primary_country="global",
                target_audiences=["CleanTech Investors", "Energy Analysts"],
                enabled=True,
                publishing_enabled=True,
                autonomous_publishing_enabled=False,
                max_posts_per_day=3,
                minimum_publish_interval_minutes=120
            )
            session.add(site2)
            print("Added sample sites")

        # 3. Initial system operational alert
        res = await session.execute(select(Alert).where(Alert.title == "Autonomous OS Guardrails Initialized"))
        if not res.scalar_one_or_none():
            alert = Alert(
                title="Autonomous OS Guardrails Initialized",
                message="Cost governor, pre-publish verifier, and emergency kill-switch operational.",
                category=AlertCategory.SYSTEM,
                severity=AlertSeverity.INFO,
                status=AlertStatus.OPEN,
                deduplication_key="init-alert-001",
                occurrence_count=1
            )
            session.add(alert)
            print("Added initial system alert")

        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
