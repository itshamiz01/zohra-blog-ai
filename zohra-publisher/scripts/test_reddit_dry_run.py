"""
Live Dry Run Verification Script for Zohra Reddit Opportunity & Referral Engine.
Demonstrates the complete end-to-end trace without submitting any content to Reddit.
"""

import asyncio
import json
import uuid

from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.models.sites import Site
from app.reddit.service import RedditEngineService


async def main():
    async with async_session_factory() as session:
        # Find active site
        res = await session.execute(select(Site).where(Site.enabled.is_(True)))
        site = res.scalars().first()
        if not site:
            # Fallback to any site
            res = await session.execute(select(Site))
            site = res.scalars().first()

        if not site:
            print("No site found in database!")
            return

        print(f"Target Site: {site.name} ({site.domain})")
        print(f"Site ID: {site.id}\n")

        service = RedditEngineService(session)

        sample_title = "How should high school students use ChatGPT for studying without cheating or becoming lazy?"
        sample_body = "I want practical study techniques that foster critical thinking rather than taking academic shortcuts."
        subreddit = "education"

        print(f"Executing Full End-to-End Dry Run on r/{subreddit}...")
        report = await service.execute_dry_run(
            site_id=site.id,
            sample_title=sample_title,
            sample_body=sample_body,
            subreddit=subreddit,
        )

        print("=" * 70)
        print("ZOHRA REDDIT OPPORTUNITY & REFERRAL ENGINE — DRY RUN REPORT")
        print("=" * 70)
        print(f"Question detected:          {report['question_detected']}")
        print(f"Why selected:               {report['why_selected']}")
        print(f"Opportunity score:          {report['opportunity_score']:.1f} / 100")
        print(f"Recommended website action: {report['recommended_website_action']}")
        print(f"Proposed article:           {report['proposed_article']}")
        print(f"Research status:            {report['research_status']}")
        print(f"Article status:             {report['article_status']}")
        print(f"Community rule result:      {report['community_rule_result']}")
        print(f"Anti-spam result:           {report['anti_spam_result']}")
        print(f"Would include link:         {report['would_include_link']}")
        print(f"Link rationale:             {report['link_inclusion_reason']}")
        print(f"Would publish live:         {report['would_publish']}")
        print("\nPROPOSED REDDIT-NATIVE ANSWER (STANDALONE VALUE):")
        print("-" * 70)
        print(report['proposed_reddit_answer'])
        print("-" * 70)
        print(f"\nFinal Posting Gate:         {report['posting_gate_status']}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
