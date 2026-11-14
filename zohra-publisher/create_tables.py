"""Initialize tables in local database."""
import asyncio
from app.db.session import get_engine
from app.db.base import ZohraBase
import app.db.models  # noqa: F401

async def main():
    print("Connecting to database and creating tables...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(ZohraBase.metadata.create_all)
    print("All database tables created successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
