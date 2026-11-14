"""Zohra DB models — package init. Import all models here for Alembic discovery."""

from app.db.models.agent_runs import AgentRun
from app.db.models.article_blueprints import ArticleBlueprint
from app.db.models.article_images import ArticleFeaturedMedia, ArticleImageBrandProfile
from app.db.models.audit_checks import AuditCheck
from app.db.models.audit_issues import AuditIssue
from app.db.models.audit_logs import AuditLog
from app.db.models.audit_projects import AuditProject
from app.db.models.audited_claims import AuditedClaim
from app.db.models.brand_voice_profiles import BrandVoiceProfile
from app.db.models.claims import Claim
from app.db.models.content_gaps import ContentGap
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.content_overlap_findings import ContentOverlapFinding
from app.db.models.content_risk_policies import ContentRiskPolicy
from app.db.models.content_strategies import ContentStrategy
from app.db.models.contradictions import Contradiction
from app.db.models.discovery_queries import DiscoveryQuery
from app.db.models.document_versions import DocumentVersion
from app.db.models.draft_claim_usage import DraftClaimUsage
from app.db.models.draft_projects import DraftProject
from app.db.models.draft_versions import DraftVersion
from app.db.models.editorial_draft_packages import EditorialDraftPackage
from app.db.models.entities import DocumentEntity, Entity
from app.db.models.entity_relationships import EntityRelationship
from app.db.models.event_documents import EventDocument
from app.db.models.event_snapshots import EventSnapshot
from app.db.models.events import Event
from app.db.models.evidence_items import EvidenceItem
from app.db.models.final_audit_packages import FinalAuditPackage
from app.db.models.headline_candidates import HeadlineCandidate
from app.db.models.internal_link_candidates import InternalLinkCandidate
from app.db.models.jobs import Job
from app.db.models.keyword_clusters import KeywordCluster, KeywordClusterMember
from app.db.models.keywords import Keyword
from app.db.models.media_assets import MediaAsset, MediaPlan
from app.db.models.model_usage import ModelUsage
from app.db.models.operations import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AutonomyMode,
    NotificationChannel,
    NotificationLog,
    NotificationPreference,
    OutboxEvent,
    OutboxStatus,
    ScheduledTaskRegistry,
    SecretRecord,
    SecurityEvent,
    User,
    UserRole,
    UserSiteRole,
)
from app.db.models.opportunity_snapshots import OpportunitySnapshot, OpportunityWatchlist
from app.db.models.optimization import (
    ArticleRefreshHistory,
    CandidateStatus,
    ContentSnapshot,
    Experiment,
    ExperimentStatus,
    FreshnessPolicy,
    MemoryStatus,
    OptimizationApproval,
    OptimizationCandidate,
    OptimizationChangeset,
    OptimizationEvent,
    OptimizationPlan,
    OptimizationPolicy,
    PredictionOutcome,
    RefreshSchedule,
    RiskClass,
    StrategyMemory,
    StrategyParameter,
    StrategyVersion,
    StrategyVersionStatus,
)
from app.db.models.publication_authorizations import PublicationAuthorization
from app.db.models.publication_jobs import PublicationEvent, PublicationJob, PublicationSchedule
from app.db.models.published_articles import IndexingJob, PublicationApproval, PublishedArticle
from app.db.models.questions import DiscoveredQuestion
from app.db.models.reddit import (
    RedditCommunityPolicy,
    RedditJobStatus,
    RedditOpportunity,
    RedditOpportunityAction,
    RedditPublication,
    RedditQuestion,
    RedditQuestionCluster,
    RedditQuestionType,
    RedditReferralEvent,
    RedditResponseDraft,
    RedditResponseType,
    RedditSource,
)
from app.db.models.research_followup_requests import ResearchFollowupRequest
from app.db.models.research_gaps import ResearchGap
from app.db.models.research_notes import ResearchNote
from app.db.models.research_packages import ResearchPackage
from app.db.models.research_projects import ResearchProject
from app.db.models.research_queries import ResearchQuery
from app.db.models.research_questions import ResearchQuestion
from app.db.models.research_sources import ResearchSource
from app.db.models.research_timeline import ResearchTimelineEvent
from app.db.models.revision_tasks import RevisionTask
from app.db.models.search_analytics import (
    AnalyticsAnomaly,
    AnalyticsIngestionProfile,
    AnalyticsIngestionRun,
    AnalyticsQueryCluster,
    AnalyticsQueryClusterMember,
    AnalyticsWatermark,
    ArticleEconomicsSnapshot,
    ArticlePerformanceSnapshot,
    ArticleRevenueDaily,
    CTRBenchmark,
    IndexingStatusHistory,
    PageCountryDailyMetric,
    PageDailyMetric,
    PageDeviceDailyMetric,
    PageQueryDailyMetric,
    PerformanceAnnotation,
    PerformanceOpportunity,
    PerformanceSuccessProfile,
    QueryAlignmentRecord,
    QueryDailyMetric,
    SearchAnalyticsRaw,
    SearchCannibalizationEvent,
    SearchConsoleProperty,
    SiteDailyMetric,
    SitePerformanceSnapshot,
    TopicPerformanceSnapshot,
)
from app.db.models.sentence_grounding import SentenceGrounding
from app.db.models.seo_publication_packages import SEOPublicationPackage
from app.db.models.serp import SERPResult, SERPSnapshot
from app.db.models.site_content import SiteContent
from app.db.models.site_health import OrphanMediaRecord, SiteHealth
from app.db.models.site_topics import SiteTopic
from app.db.models.sites import Site
from app.db.models.source_documents import SourceDocument
from app.db.models.sources import Source
from app.db.models.system_errors import SystemError
from app.db.models.system_settings import SystemSetting
from app.db.models.topic_clusters import TopicCluster
from app.db.models.visual_brand_profiles import VisualBrandProfile

__all__ = [
    # Core
    "SystemSetting",
    "AgentRun",
    "ModelUsage",
    "SystemError",
    "AuditLog",
    "Job",
    # Part 2 Discovery & Events
    "Source",
    "SourceDocument",
    "Entity",
    "DocumentEntity",
    "Event",
    "EventDocument",
    "EventSnapshot",
    "DiscoveryQuery",
    # Part 3 Opportunity Intelligence & SEO
    "Site",
    "SiteTopic",
    "SiteContent",
    "Keyword",
    "KeywordCluster",
    "KeywordClusterMember",
    "SERPSnapshot",
    "SERPResult",
    "ContentGap",
    "DiscoveredQuestion",
    "TopicCluster",
    "ContentOpportunity",
    "OpportunitySnapshot",
    "OpportunityWatchlist",
    # Part 4 Deep Research & Evidence Intelligence
    "ResearchProject",
    "ResearchQuestion",
    "ResearchQuery",
    "ResearchSource",
    "DocumentVersion",
    "Claim",
    "EvidenceItem",
    "Contradiction",
    "EntityRelationship",
    "ResearchTimelineEvent",
    "ResearchGap",
    "ResearchNote",
    "ResearchPackage",
    # Part 5 Editorial Generation & Drafting
    "DraftProject",
    "ContentStrategy",
    "ArticleBlueprint",
    "DraftClaimUsage",
    "SentenceGrounding",
    "HeadlineCandidate",
    "BrandVoiceProfile",
    "DraftVersion",
    "RevisionTask",
    "ResearchFollowupRequest",
    "EditorialDraftPackage",
    "InternalLinkCandidate",
    # Part 6 Independent Editorial Audit & Quality Firewall
    "AuditProject",
    "AuditIssue",
    "AuditedClaim",
    "ContentOverlapFinding",
    "ContentRiskPolicy",
    "AuditCheck",
    "FinalAuditPackage",
    # Part 7 Media, SEO Packaging & WordPress Publishing Engine
    "PublicationAuthorization",
    "VisualBrandProfile",
    "MediaPlan",
    "MediaAsset",
    "ArticleFeaturedMedia",
    "ArticleImageBrandProfile",
    "SEOPublicationPackage",
    "PublicationJob",
    "PublicationSchedule",
    "PublicationEvent",
    "PublicationApproval",
    "PublishedArticle",
    "IndexingJob",
    "SiteHealth",
    "OrphanMediaRecord",
    # Part 8 Search Analytics, Performance Intelligence & Indexing
    "SearchConsoleProperty",
    "AnalyticsIngestionProfile",
    "AnalyticsIngestionRun",
    "SearchAnalyticsRaw",
    "PageDailyMetric",
    "QueryDailyMetric",
    "PageQueryDailyMetric",
    "PageCountryDailyMetric",
    "PageDeviceDailyMetric",
    "SiteDailyMetric",
    "IndexingStatusHistory",
    "QueryAlignmentRecord",
    "AnalyticsQueryCluster",
    "AnalyticsQueryClusterMember",
    "CTRBenchmark",
    "ArticlePerformanceSnapshot",
    "TopicPerformanceSnapshot",
    "SitePerformanceSnapshot",
    "SearchCannibalizationEvent",
    "AnalyticsAnomaly",
    "PerformanceOpportunity",
    "PerformanceAnnotation",
    "AnalyticsWatermark",
    "PerformanceSuccessProfile",
    "ArticleRevenueDaily",
    "ArticleEconomicsSnapshot",
    # Part 9 Learning, Optimization & Controlled Experiments
    "OptimizationPolicy",
    "OptimizationCandidate",
    "OptimizationPlan",
    "ContentSnapshot",
    "OptimizationChangeset",
    "OptimizationApproval",
    "Experiment",
    "PredictionOutcome",
    "StrategyMemory",
    "StrategyParameter",
    "StrategyVersion",
    "FreshnessPolicy",
    "RefreshSchedule",
    "ArticleRefreshHistory",
    "OptimizationEvent",
    "RiskClass",
    "CandidateStatus",
    "ExperimentStatus",
    "MemoryStatus",
    "StrategyVersionStatus",
    # Part 10 Production Operations & Command Center
    "User",
    "UserSiteRole",
    "UserRole",
    "AutonomyMode",
    "Alert",
    "AlertCategory",
    "AlertSeverity",
    "AlertStatus",
    "NotificationLog",
    "NotificationPreference",
    "NotificationChannel",
    "ScheduledTaskRegistry",
    "OutboxEvent",
    "OutboxStatus",
    "SecurityEvent",
    "SecretRecord",
    # Reddit Opportunity & Referral Engine
    "RedditSource",
    "RedditQuestion",
    "RedditQuestionCluster",
    "RedditOpportunity",
    "RedditCommunityPolicy",
    "RedditResponseDraft",
    "RedditPublication",
    "RedditReferralEvent",
    "RedditQuestionType",
    "RedditOpportunityAction",
    "RedditJobStatus",
    "RedditResponseType",
]
