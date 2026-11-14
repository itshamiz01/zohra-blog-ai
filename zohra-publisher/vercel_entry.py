"""Vercel entrypoint: ensure SQLite tables exist on cold start, then serve the app."""
import asyncio

async def _init_db() -> None:
    try:
        import app.db.models  # noqa: F401  (registers all tables)
        from app.db.base import ZohraBase
        from app.db.session import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(ZohraBase.metadata.create_all)
    except Exception:
        pass  # never block serving on table bootstrap

try:
    asyncio.run(_init_db())
except Exception:
    pass

from app.main import app  # noqa: E402,F401
