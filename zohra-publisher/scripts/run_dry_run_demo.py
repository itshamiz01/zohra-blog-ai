"""
Execute and print a full live dry-run simulation of the Reddit Engine.
"""

import asyncio
import json
import uuid

from sqlalchemy import select

from app.db.models.sites import Site
from app.db.session import get_session_factory
from app.reddit.service import RedditEngineService


async def main():
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(select(Site))
        site = res.scalars().first()
        site_id = site.id if site else uuid.uuid4()

        service = RedditEngineService(db)
        result = await service.execute_dry_run(
            site_id=site_id,
            sample_title="How can high school students use ChatGPT for essay outlining without plagiarizing?",
            sample_body="Looking for ethical study workflows that preserve critical thinking rather than generating shortcuts.",
            subreddit="education",
        )
        print("=== DRY RUN SIMULATION RESULT ===")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
