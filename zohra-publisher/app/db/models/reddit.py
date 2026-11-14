"""
Zohra — Reddit Opportunity & Referral Engine Database Models.

Defines persistence for Reddit source tracking, discovered questions,
question clusters, opportunity scoring, community rule policies,
response drafts, publication records, and referral analytics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


# ── Enums ────────────────────────────────────────────────────────


class RedditQuestionType(str, Enum):
    DIRECT_QUESTION = "direct_question"
    PROBLEM = "problem"
    ADVICE_REQUEST = "advice_request"
    COMPARISON = "comparison"
    HOW_TO = "how_to"
    TROUBLESHOOTING = "troubleshooting"
    EXPERIENCE_REQUEST = "experience_request"
    EXPLANATION_REQUEST = "explanation_request"
    RECOMMENDATION_REQUEST = "recommendation_request"
    DISCUSSION = "discussion"
    NEWS_REACTION = "news_reaction"
    RANT = "rant"
    MEME = "meme"
    SPAM = "spam"
    OTHER = "other"


class RedditOpportunityAction(str, Enum):
    CREATE_NEW_ARTICLE = "create_new_article"
    UPDATE_EXISTING_ARTICLE = "update_existing_article"
    EXPAND_EXISTING_ARTICLE = "expand_existing_article"
    ADD_FAQ = "add_faq"
    CREATE_SUPPORTING_ARTICLE = "create_supporting_article"
    ANSWER_REDDIT_ONLY = "answer_reddit_only"
    WATCH = "watch"
    REJECT = "reject"
    HUMAN_REVIEW = "human_review"


class RedditJobStatus(str, Enum):
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    CLASSIFIED = "classified"
    CLUSTERED = "clustered"
    SCORED = "scored"
    QUALIFIED = "qualified"
    RESEARCHING = "researching"
    ARTICLE_CREATING = "article_creating"
    ARTICLE_PUBLISHED = "article_published"
    RESPONSE_DRAFTED = "response_drafted"
    RULE_CHECKING = "rule_checking"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    FAILED = "failed"


class RedditResponseType(str, Enum):
    ANSWER_ONLY = "answer_only"
    ANSWER_WITH_OPTIONAL_RESOURCE = "answer_with_optional_resource"
    DISCUSSION_RESPONSE = "discussion_response"
    CLARIFICATION = "clarification"
    NO_RESPONSE = "no_response"


# ── Database Models ──────────────────────────────────────────────


class RedditSource(ZohraBase):
    """Monitored subreddit source configuration."""

    __tablename__ = "reddit_sources"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subscriber_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relevance_keywords: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    scan_frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    post_count_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    questions = relationship("RedditQuestion", back_populates="source", cascade="all, delete-orphan")
    community_policy = relationship("RedditCommunityPolicy", back_populates="source", uselist=False)

    __table_args__ = (
        Index("ix_reddit_sources_site_sub", "site_id", "subreddit", unique=True),
    )


class RedditQuestion(ZohraBase):
    """Raw and normalized question discovered from Reddit."""

    __tablename__ = "reddit_questions"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_question_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Reddit Platform Identifiers
    reddit_post_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    author_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    permalink: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Raw Post Content
    raw_title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    flair: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reddit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reddit_comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Classification & Intent
    is_question: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditQuestionType.OTHER.value, index=True
    )
    primary_question: Mapped[str] = mapped_column(Text, nullable=False)
    underlying_problem: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_intent: Mapped[str] = mapped_column(String(50), nullable=False, default="informational")
    target_audience: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extracted_entities: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    urgency_level: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")

    # Relevance & Quality Scoring
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relevance_reasons: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    clarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    answerability_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditJobStatus.DISCOVERED.value, index=True
    )

    # Relationships
    source = relationship("RedditSource", back_populates="questions")
    cluster = relationship("RedditQuestionCluster", back_populates="questions")
    opportunity = relationship("RedditOpportunity", back_populates="question", uselist=False)

    __table_args__ = (
        Index("ix_reddit_questions_site_post", "site_id", "reddit_post_id", unique=True),
        Index("ix_reddit_questions_sub_date", "subreddit", "posted_at"),
    )


class RedditQuestionCluster(ZohraBase):
    """Clusters multiple similar Reddit questions into unified parent topics."""

    __tablename__ = "reddit_question_clusters"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cluster_name: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_problem: Mapped[str] = mapped_column(Text, nullable=False)
    parent_topic: Mapped[str] = mapped_column(String(256), nullable=False)
    subtopics: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    primary_intent: Mapped[str] = mapped_column(String(50), nullable=False, default="informational")
    aggregate_momentum_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    questions = relationship("RedditQuestion", back_populates="cluster")
    opportunities = relationship("RedditOpportunity", back_populates="cluster")


class RedditOpportunity(ZohraBase):
    """Vetted content opportunity derived from Reddit question(s)."""

    __tablename__ = "reddit_opportunities"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_questions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_question_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Proposed Editorial Direction
    working_title: Mapped[str] = mapped_column(String(512), nullable=False)
    proposed_angle: Mapped[str] = mapped_column(Text, nullable=False)
    target_keyword: Mapped[str] = mapped_column(String(256), nullable=False)
    secondary_keywords: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    recommended_action: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditOpportunityAction.CREATE_NEW_ARTICLE.value, index=True
    )

    # Existing Content Matching
    existing_article_match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("published_articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    existing_article_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_gap_summary: Mapped[Text | None] = mapped_column(Text, nullable=True)

    # Multi-Dimensional Opportunity Scores (0.0 to 100.0)
    website_relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    recurrence_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    engagement_momentum_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    content_gap_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    search_intent_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    evergreen_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    answerability_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    overall_opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    score_reasons: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)

    # Pipeline Integration
    handoff_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ready_for_research", index=True
    )
    generated_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("published_articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditJobStatus.SCORED.value, index=True
    )

    # Relationships
    question = relationship("RedditQuestion", back_populates="opportunity")
    cluster = relationship("RedditQuestionCluster", back_populates="opportunities")
    response_drafts = relationship("RedditResponseDraft", back_populates="opportunity")


class RedditCommunityPolicy(ZohraBase):
    """Subreddit community rules, self-promotion policies, and posting boundaries."""

    __tablename__ = "reddit_community_policies"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_sources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Permitted Activities
    posting_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    commenting_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    external_links_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    self_promotion_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disclosure_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Restrictions & Limits
    promotion_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_karma: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_account_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rules_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_rules_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)

    # Verification Metadata
    rule_status: Mapped[str] = mapped_column(String(50), nullable=False, default="verified")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    source = relationship("RedditSource", back_populates="community_policy")

    __table_args__ = (
        Index("ix_reddit_community_policy_site_sub", "site_id", "subreddit", unique=True),
    )


class RedditResponseDraft(ZohraBase):
    """Draft Reddit response awaiting review or approval before publishing."""

    __tablename__ = "reddit_response_drafts"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reddit_post_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Draft Content
    response_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditResponseType.ANSWER_ONLY.value
    )
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    has_external_link: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proposed_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    link_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Safety & Compliance Validations
    rule_check_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rule_check_details: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    anti_spam_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anti_spam_details: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    destination_article_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Approval Gate
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditJobStatus.RESPONSE_DRAFTED.value, index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    opportunity = relationship("RedditOpportunity", back_populates="response_drafts")
    publication = relationship("RedditPublication", back_populates="draft", uselist=False)


class RedditPublication(ZohraBase):
    """Live submitted Reddit publication record for idempotency and lifecycle tracking."""

    __tablename__ = "reddit_publications"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_response_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reddit_post_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Idempotency & Verification
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    remote_comment_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    remote_comment_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Submitted Body & Links
    final_body: Mapped[str] = mapped_column(Text, nullable=False)
    included_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RedditJobStatus.SUBMITTED.value, index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_removed_by_mod: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Performance
    comment_upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    child_replies_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    draft = relationship("RedditResponseDraft", back_populates="publication")
    referral_events = relationship("RedditReferralEvent", back_populates="publication")


class RedditReferralEvent(ZohraBase):
    """Attributable visitor referral from Reddit into website content."""

    __tablename__ = "reddit_referral_events"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publication_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reddit_publications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    destination_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    article_slug: Mapped[str] = mapped_column(String(256), nullable=False, index=True)

    # Campaign Tracking
    utm_source: Mapped[str] = mapped_column(String(50), nullable=False, default="reddit")
    utm_medium: Mapped[str] = mapped_column(String(50), nullable=False, default="community")
    utm_campaign: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Session & Engagement
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    pageviews: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    engaged_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    converted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    publication = relationship("RedditPublication", back_populates="referral_events")

    __table_args__ = (
        Index("ix_reddit_referrals_article_time", "article_slug", "occurred_at"),
    )
