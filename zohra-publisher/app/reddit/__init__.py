"""
Zohra — Reddit Opportunity & Referral Engine package.
"""

from app.reddit.anti_spam import RedditAntiSpamGuard
from app.reddit.approval import RedditApprovalManager
from app.reddit.classifier import QuestionAnalysisResult, RedditQuestionClassifier
from app.reddit.clustering import RedditQuestionClusterer
from app.reddit.dedup import RedditDuplicateDetector
from app.reddit.exceptions import (
    RedditAuthError,
    RedditError,
    RedditPostNotFoundError,
    RedditRateLimitError,
    RedditRuleViolationError,
    RedditSpamBlockedError,
    RedditUnavailableError,
)
from app.reddit.handoff import build_reddit_opportunity_package
from app.reddit.learning import RedditLearningEngine
from app.reddit.opportunity import RedditOpportunityEngine
from app.reddit.provider import RedditProvider
from app.reddit.referral import RedditReferralTracker, build_attributable_url
from app.reddit.relevance import RedditRelevanceScorer, RelevanceScoreResult
from app.reddit.response_writer import GeneratedRedditResponse, RedditResponseWriter
from app.reddit.rules import SubredditRuleChecker
from app.reddit.scanner import RedditQuestionScanner
from app.reddit.service import RedditEngineService

__all__ = [
    "RedditError",
    "RedditAuthError",
    "RedditRateLimitError",
    "RedditUnavailableError",
    "RedditPostNotFoundError",
    "RedditRuleViolationError",
    "RedditSpamBlockedError",
    "RedditProvider",
    "QuestionAnalysisResult",
    "RedditQuestionClassifier",
    "RelevanceScoreResult",
    "RedditRelevanceScorer",
    "RedditDuplicateDetector",
    "RedditQuestionClusterer",
    "RedditOpportunityEngine",
    "build_reddit_opportunity_package",
    "SubredditRuleChecker",
    "GeneratedRedditResponse",
    "RedditResponseWriter",
    "RedditAntiSpamGuard",
    "RedditApprovalManager",
    "RedditReferralTracker",
    "build_attributable_url",
    "RedditLearningEngine",
    "RedditQuestionScanner",
    "RedditEngineService",
]
