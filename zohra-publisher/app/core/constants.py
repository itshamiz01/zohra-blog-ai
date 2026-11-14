"""
Zohra — Application constants and enumerations.

Centralized definitions for states, severities, and other domain values.
Business logic references these instead of scattering magic strings.
"""

from __future__ import annotations

from enum import Enum

# ──────────────────────────────────────────────────────────────────
# Content Workflow States
# ──────────────────────────────────────────────────────────────────


class WorkflowState(str, Enum):
    """
    Lifecycle states for content items.
    Transitions are validated by the WorkflowEngine — not every
    transition is legal. See VALID_TRANSITIONS below.
    """

    DISCOVERED = "discovered"
    FILTERED = "filtered"
    RESEARCHING = "researching"
    RESEARCHED = "researched"
    PLANNED = "planned"
    DRAFTING = "drafting"
    DRAFTED = "drafted"
    VERIFYING = "verifying"
    SEO_REVIEW = "seo_review"
    QUALITY_REVIEW = "quality_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    MONITORING = "monitoring"
    REFRESH_CANDIDATE = "refresh_candidate"
    ARCHIVED = "archived"
    FAILED = "failed"


# Legal state transitions — forward progression plus controlled fallbacks
VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.DISCOVERED: {
        WorkflowState.FILTERED,
        WorkflowState.FAILED,
        WorkflowState.ARCHIVED,
    },
    WorkflowState.FILTERED: {
        WorkflowState.RESEARCHING,
        WorkflowState.FAILED,
        WorkflowState.ARCHIVED,
    },
    WorkflowState.RESEARCHING: {WorkflowState.RESEARCHED, WorkflowState.FAILED},
    WorkflowState.RESEARCHED: {WorkflowState.PLANNED, WorkflowState.FAILED, WorkflowState.ARCHIVED},
    WorkflowState.PLANNED: {WorkflowState.DRAFTING, WorkflowState.FAILED, WorkflowState.ARCHIVED},
    WorkflowState.DRAFTING: {WorkflowState.DRAFTED, WorkflowState.FAILED},
    WorkflowState.DRAFTED: {WorkflowState.VERIFYING, WorkflowState.FAILED},
    WorkflowState.VERIFYING: {
        WorkflowState.SEO_REVIEW,
        WorkflowState.DRAFTED,
        WorkflowState.FAILED,
    },
    WorkflowState.SEO_REVIEW: {
        WorkflowState.QUALITY_REVIEW,
        WorkflowState.DRAFTED,
        WorkflowState.FAILED,
    },
    WorkflowState.QUALITY_REVIEW: {
        WorkflowState.APPROVED,
        WorkflowState.DRAFTED,
        WorkflowState.FAILED,
    },
    WorkflowState.APPROVED: {
        WorkflowState.SCHEDULED,
        WorkflowState.PUBLISHED,
        WorkflowState.FAILED,
    },
    WorkflowState.SCHEDULED: {WorkflowState.PUBLISHED, WorkflowState.FAILED},
    WorkflowState.PUBLISHED: {WorkflowState.MONITORING, WorkflowState.FAILED},
    WorkflowState.MONITORING: {WorkflowState.REFRESH_CANDIDATE, WorkflowState.ARCHIVED},
    WorkflowState.REFRESH_CANDIDATE: {WorkflowState.RESEARCHING, WorkflowState.ARCHIVED},
    WorkflowState.ARCHIVED: set(),  # terminal
    WorkflowState.FAILED: {
        WorkflowState.DISCOVERED,
        WorkflowState.ARCHIVED,
    },  # can retry from start
}


# ──────────────────────────────────────────────────────────────────
# Job States
# ──────────────────────────────────────────────────────────────────


class JobStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


# ──────────────────────────────────────────────────────────────────
# Agent Run States
# ──────────────────────────────────────────────────────────────────


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# ──────────────────────────────────────────────────────────────────
# Error Severity
# ──────────────────────────────────────────────────────────────────


class ErrorSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ──────────────────────────────────────────────────────────────────
# Audit Actor Types
# ──────────────────────────────────────────────────────────────────


class ActorType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"
    API = "api"


# ──────────────────────────────────────────────────────────────────
# Redis Key Namespaces
# ──────────────────────────────────────────────────────────────────

REDIS_PREFIX = "zohra"
REDIS_CACHE_PREFIX = f"{REDIS_PREFIX}:cache"
REDIS_LOCK_PREFIX = f"{REDIS_PREFIX}:lock"
REDIS_RATE_PREFIX = f"{REDIS_PREFIX}:rate"
REDIS_IDEMPOTENCY_PREFIX = f"{REDIS_PREFIX}:idempotency"


# ──────────────────────────────────────────────────────────────────
# Default Limits
# ──────────────────────────────────────────────────────────────────

DEFAULT_LOCK_TIMEOUT_SECONDS = 30
DEFAULT_LOCK_TTL_SECONDS = 300
DEFAULT_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours
MAX_RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 60.0


# ──────────────────────────────────────────────────────────────────
# Part 2: Discovery, Sources & Events Enums
# ──────────────────────────────────────────────────────────────────


class SourceType(str, Enum):
    RSS = "rss"
    ATOM = "atom"
    NEWS_FEED = "news_feed"
    OFFICIAL_SITE = "official_site"
    COMPANY_BLOG = "company_blog"
    GOVERNMENT_SOURCE = "government_source"
    RESEARCH_SOURCE = "research_source"
    COMMUNITY = "community"
    SOCIAL_SIGNAL = "social_signal"
    MANUAL = "manual"
    API = "api"
    SEARCH_PROVIDER = "search_provider"


class SourceTier(int, Enum):
    TIER_1 = 1  # Official, government, primary research, company announcements
    TIER_2 = 2  # Established professional reporting & specialist press
    TIER_3 = 3  # Industry publications, reputable experts
    TIER_4 = 4  # Community signals (Reddit, forums, social discussions)
    TIER_5 = 5  # Unknown or unverified sources


class SourceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"


class EventStatus(str, Enum):
    EMERGING = "emerging"
    ACTIVE = "active"
    ACCELERATING = "accelerating"
    PEAKING = "peaking"
    DECLINING = "declining"
    STABLE = "stable"
    DORMANT = "dormant"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class EventType(str, Enum):
    PRODUCT_LAUNCH = "product_launch"
    ANNOUNCEMENT = "announcement"
    RESEARCH_RELEASE = "research_release"
    SOFTWARE_UPDATE = "software_update"
    FUNDING = "funding"
    ACQUISITION = "acquisition"
    EARNINGS = "earnings"
    LEGAL_DEVELOPMENT = "legal_development"
    SECURITY_INCIDENT = "security_incident"
    ENTERTAINMENT_RELEASE = "entertainment_release"
    VIRAL_TOPIC = "viral_topic"
    PUBLIC_STATEMENT = "public_statement"
    INDUSTRY_CHANGE = "industry_change"
    UNKNOWN = "unknown"


class TrendClassification(str, Enum):
    NOISE = "noise"  # 0–29
    WEAK_SIGNAL = "weak_signal"  # 30–49
    MONITOR = "monitor"  # 50–64
    EMERGING = "emerging"  # 65–74
    TRENDING = "trending"  # 75–84
    HIGH_VELOCITY = "high_velocity"  # 85–94
    EXCEPTIONAL_SIGNAL = "exceptional_signal"  # 95–100


class RiskFlag(str, Enum):
    MEDICAL = "medical"
    FINANCIAL = "financial"
    LEGAL = "legal"
    POLITICAL = "political"
    VIOLENCE = "violence"
    DEATH = "death"
    ALLEGATION = "allegation"
    CRIME = "crime"
    MINOR = "minor"
    PRIVACY = "privacy"
    BREAKING_EMERGENCY = "breaking_emergency"


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PRODUCT = "PRODUCT"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    TECHNOLOGY = "TECHNOLOGY"
    DATE = "DATE"
    MONEY = "MONEY"


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# Discovery Scoring Weights
DEFAULT_TREND_WEIGHTS: dict[str, float] = {
    "velocity": 0.25,
    "momentum": 0.20,
    "diversity": 0.15,
    "freshness": 0.15,
    "authority": 0.10,
    "cross_platform": 0.10,
    "confidence": 0.05,
}


# ──────────────────────────────────────────────────────────────────
# Part 3: Search Intent, Opportunity Intelligence & SERP Constants
# ──────────────────────────────────────────────────────────────────


class SearchIntent(str, Enum):
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    COMMERCIAL_INVESTIGATION = "commercial_investigation"
    TRANSACTIONAL = "transactional"
    NEWS = "news"
    COMPARISON = "comparison"
    TUTORIAL = "tutorial"
    TROUBLESHOOTING = "troubleshooting"
    LOCAL = "local"
    REFERENCE = "reference"


class OpportunityStatus(str, Enum):
    CANDIDATE = "candidate"
    ANALYZING = "analyzing"
    QUALIFIED = "qualified"
    HIGH_PRIORITY = "high_priority"
    WATCH = "watch"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RESEARCH_REQUESTED = "research_requested"


class OpportunityClassification(str, Enum):
    REJECT = "reject"  # 0–39
    LOW = "low"  # 40–54
    WATCH = "watch"  # 55–64
    QUALIFIED = "qualified"  # 65–74
    HIGH_PRIORITY = "high_priority"  # 75–84
    VERY_HIGH_PRIORITY = "very_high_priority"  # 85–94
    EXCEPTIONAL = "exceptional"  # 95–100


class ContentAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    EXPAND = "expand"
    MERGE = "merge"
    WATCH = "watch"
    REJECT = "reject"
    REVIEW = "review"


class ContentType(str, Enum):
    BREAKING_NEWS = "breaking_news"
    NEWS_ANALYSIS = "news_analysis"
    EXPLAINER = "explainer"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    REVIEW = "review"
    ALTERNATIVES = "alternatives"
    LIST = "list"
    REFERENCE = "reference"
    TROUBLESHOOTING = "troubleshooting"
    CASE_STUDY = "case_study"
    TIMELINE = "timeline"
    PRICING = "pricing"
    GUIDE = "guide"
    FAQ = "faq"


class FreshnessDecayType(str, Enum):
    BREAKING = "breaking"
    FAST_DECAY = "fast_decay"
    MEDIUM_DECAY = "medium_decay"
    SLOW_DECAY = "slow_decay"
    EVERGREEN = "evergreen"
    SEASONAL = "seasonal"
    RECURRING = "recurring"


class ClusterRole(str, Enum):
    PILLAR = "pillar"
    SUPPORTING = "supporting"
    STANDALONE = "standalone"
    NEWS = "news"
    UPDATE = "update"


class AnalysisDepth(str, Enum):
    LIGHT = "light"
    STANDARD = "standard"
    DEEP = "deep"


class SERPResultType(str, Enum):
    ORGANIC = "organic"
    FEATURED_SNIPPET = "featured_snippet"
    NEWS = "news"
    VIDEO = "video"
    FORUM = "forum"
    SHOPPING = "shopping"
    LOCAL = "local"
    KNOWLEDGE = "knowledge"
    PEOPLE_ALSO_ASK = "people_also_ask"
    OTHER = "other"


class CannibalizationRisk(str, Enum):
    LOW = "low"  # 0–20
    MODERATE = "moderate"  # 21–50
    HIGH = "high"  # 51–75
    SEVERE = "severe"  # 76–100


class OpportunityDependencyStatus(str, Enum):
    READY = "ready"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    BLOCKED = "blocked"
    EXPIRED = "expired"


# Opportunity Scoring Weight Profiles
DEFAULT_OPPORTUNITY_WEIGHTS: dict[str, float] = {
    "search_demand": 0.15,
    "intent_strength": 0.10,
    "competition_opportunity": 0.10,
    "site_relevance": 0.12,
    "topical_authority": 0.08,
    "trend_strength": 0.10,
    "freshness": 0.08,
    "evergreen": 0.07,
    "original_value": 0.08,
    "serp_gap": 0.05,
    "monetization": 0.05,
    "audience_fit": 0.02,
}

BREAKING_NEWS_OPPORTUNITY_WEIGHTS: dict[str, float] = {
    "trend_strength": 0.20,
    "freshness": 0.20,
    "search_demand": 0.15,
    "site_relevance": 0.15,
    "competition_opportunity": 0.10,
    "original_value": 0.10,
    "intent_strength": 0.10,
}

EVERGREEN_OPPORTUNITY_WEIGHTS: dict[str, float] = {
    "search_demand": 0.20,
    "evergreen": 0.20,
    "site_relevance": 0.15,
    "topical_authority": 0.15,
    "competition_opportunity": 0.10,
    "original_value": 0.10,
    "intent_strength": 0.10,
}

COMMERCIAL_COMPARISON_OPPORTUNITY_WEIGHTS: dict[str, float] = {
    "monetization": 0.20,
    "intent_strength": 0.15,
    "competition_opportunity": 0.15,
    "search_demand": 0.15,
    "site_relevance": 0.15,
    "original_value": 0.10,
    "topical_authority": 0.10,
}
