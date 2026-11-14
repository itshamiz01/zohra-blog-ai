"""
Zohra Autonomous Publishing Engine — Central Configuration

All application settings are loaded from environment variables via Pydantic Settings.
Secrets never have defaults. Optional future integrations do not block startup.
Environment-specific behavior is centralized here.
"""

from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Strongly-typed application settings.
    Required settings raise validation errors if missing.
    Optional future-integration settings default to None.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "zohra-publisher"
    APP_ENV: AppEnvironment = AppEnvironment.DEVELOPMENT
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- API ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Authentication ---
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str

    # --- Security ---
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --- Timezone ---
    DEFAULT_TIMEZONE: str = "UTC"

    # --- AI Cost Budgets ---
    LLM_DAILY_BUDGET: float = 10.0
    LLM_MONTHLY_BUDGET: float = 200.0

    # --- Feature Flags ---
    ENABLE_DISCOVERY: bool = False
    ENABLE_RESEARCH: bool = False
    ENABLE_WRITING: bool = False
    ENABLE_AUTO_PUBLISH: bool = False
    ENABLE_ANALYTICS: bool = False

    # --- Autonomy & Maintenance ---
    AUTONOMY_ENABLED: bool = False
    MAINTENANCE_MODE: bool = False

    # --- Part 2: Discovery Engine Configuration ---
    DISCOVERY_DEFAULT_INTERVAL_MINUTES: int = 15
    MAX_FETCH_CONCURRENCY: int = 10
    MAX_DOMAIN_CONCURRENCY: int = 2
    FETCH_TIMEOUT_SECONDS: float = 15.0
    MAX_RESPONSE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    MAX_REDIRECTS: int = 5
    DISCOVERY_USER_AGENT: str = "ZohraBot/1.0 (+https://zohra.ai/bot; bot@zohra.ai)"

    # Event Clustering & Trend Thresholds
    EVENT_CLUSTER_WINDOW_HOURS: int = 48
    EVENT_SIMILARITY_THRESHOLD: float = 0.40
    POSSIBLE_EVENT_THRESHOLD: float = 0.25
    MIN_TREND_SCORE_FOR_HANDOFF: float = 50.0
    MIN_CONFIDENCE_FOR_HANDOFF: float = 60.0
    RAW_CONTENT_RETENTION_DAYS: int = 7
    MAX_DISCOVERY_COST_PER_DAY: float = 15.0

    # --- Part 3: Content Opportunity & Keyword Intelligence ---
    ENABLE_OPPORTUNITY_ENGINE: bool = False
    DEFAULT_SITE_DOMAIN: str = "zohra.ai"
    SERP_PROVIDER: str = "mock"
    SEO_METRICS_PROVIDER: str = "mock"
    MIN_OPPORTUNITY_SCORE_FOR_HANDOFF: float = 65.0
    MIN_OPPORTUNITY_CONFIDENCE_FOR_HANDOFF: float = 60.0
    CANNIBALIZATION_SIMILARITY_THRESHOLD: float = 0.70
    KEYWORD_METRICS_CACHE_HOURS: int = 48
    SERP_BREAKING_CACHE_HOURS: int = 4
    SERP_EVERGREEN_CACHE_HOURS: int = 72
    MAX_KEYWORD_EXPANSIONS_PER_EVENT: int = 25
    MAX_DEEP_SERP_ANALYSES_PER_EVENT: int = 5
    MAX_OPPORTUNITY_COST_PER_DAY: float = 15.0

    # --- Part 9: Learning, Optimization & Experimentation ---
    ENABLE_OPTIMIZATION: bool = True
    OPTIMIZATION_ENABLED: bool = True
    AUTO_OPTIMIZATION_ENABLED: bool = False
    MAX_DAILY_AUTO_OPTIMIZATIONS: int = 10
    MAX_DAILY_MAJOR_CHANGES: int = 3
    MAX_DAILY_REDIRECTS: int = 1
    MAX_DAILY_CONTENT_REFRESHES: int = 5
    MAX_DAILY_OPTIMIZATION_AI_COST: float = 20.0
    MAX_MONTHLY_OPTIMIZATION_AI_COST: float = 200.0
    MIN_ARTICLES_FOR_STRATEGY_LEARNING: int = 5
    MIN_EXPERIMENTS_FOR_PATTERN_LEARNING: int = 3
    MIN_DAYS_FOR_STRATEGY_CHANGE: int = 14
    MAX_PARAMETER_CHANGE_PERCENT: float = 0.25
    DEFAULT_EXPLORATION_RATIO: float = 0.15

    # --- Future Integrations (optional, not required for Part 1) ---
    WORDPRESS_URL: str | None = None
    WORDPRESS_USERNAME: str | None = None
    WORDPRESS_APP_PASSWORD: str | None = None

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # --- LLM Providers & Routing ---
    LLM_PRIMARY_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_ENABLED: bool = True
    OPENAI_WRITING_MODEL: str = "gpt-4o"
    OPENAI_RESEARCH_MODEL: str = "gpt-4o-mini"
    OPENAI_VERIFICATION_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: float = 60.0
    OPENAI_MAX_RETRIES: int = 3

    GEMINI_ENABLED: bool = False
    GEMINI_API_KEY: str | None = None
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    ANTHROPIC_API_KEY: str | None = None

    # OpenRouter
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_ENABLED: bool = True
    OPENROUTER_WRITING_MODEL: str = "openai/gpt-4o"
    OPENROUTER_RESEARCH_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_VERIFICATION_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_TIMEOUT_SECONDS: float = 60.0
    OPENROUTER_MAX_RETRIES: int = 3
    OPENROUTER_SITE_URL: str | None = None
    OPENROUTER_APP_NAME: str = "Zohra-Publisher"

    # --- Heavenly Insights Publishing Target ---
    HEAVENLY_SITE_URL: str | None = None
    HEAVENLY_API_URL: str | None = None
    HEAVENLY_API_TOKEN: str | None = None
    # Upload the generated cover to Heavenly Insights (POST /api/images) so the
    # article references a public absolute URL instead of a local /storage path.
    HEAVENLY_UPLOAD_IMAGES: bool = True

    # --- Reddit Opportunity & Referral Engine ---
    REDDIT_CLIENT_ID: str | None = None
    REDDIT_CLIENT_SECRET: str | None = None
    REDDIT_USER_AGENT: str = "ZohraBot/1.0 (Content Intelligence; by /u/ZohraAI)"
    REDDIT_USERNAME: str | None = None
    REDDIT_PASSWORD: str | None = None
    REDDIT_REFRESH_TOKEN: str | None = None

    REDDIT_ENABLED: bool = False
    REDDIT_DISCOVERY_ENABLED: bool = True
    REDDIT_RESPONSE_GENERATION_ENABLED: bool = False
    REDDIT_POSTING_ENABLED: bool = False
    REDDIT_AUTONOMY_MODE: str = "DISCOVERY_ONLY"  # REDDIT_OFF, DISCOVERY_ONLY, DRAFT_RESPONSES, APPROVAL_REQUIRED, AUTO_LOW_RISK

    REDDIT_MAX_COMMENTS_PER_DAY: int = 5
    REDDIT_MAX_COMMENTS_PER_SUBREDDIT_PER_DAY: int = 1
    REDDIT_MIN_HOURS_BETWEEN_POSTS: float = 4.0
    REDDIT_MIN_OPPORTUNITY_SCORE: float = 65.0
    REDDIT_MIN_RELEVANCE_SCORE: float = 60.0
    REDDIT_MONITORED_SUBREDDITS: list[str] = [
        "artificial",
        "ChatGPT",
        "OpenAI",
        "learnmachinelearning",
        "edtech",
        "education",
    ]

    # --- Article Image Generation & Media Engine ---
    ARTICLE_IMAGES_ENABLED: bool = True
    ARTICLE_IMAGE_PROVIDER: str = "local_ai"  # local_ai, openai, procedural, pollinations
    ARTICLE_FEATURED_IMAGE_REQUIRED: bool = True
    ARTICLE_IMAGE_GENERATION_ENABLED: bool = True
    ARTICLE_IMAGE_OPTIMIZATION_ENABLED: bool = True
    ARTICLE_IMAGE_REQUIRE_GENERATIVE_AI: bool = True
    ARTICLE_IMAGE_ALLOW_PAID_FALLBACK: bool = False
    ARTICLE_IMAGE_ALLOW_PROCEDURAL_FALLBACK: bool = False
    ARTICLE_IMAGE_MODEL: str = "dall-e-3"
    ARTICLE_IMAGE_QUALITY: str = "standard"  # standard, hd
    ARTICLE_IMAGE_ASPECT_RATIO: str = "16:9"
    ARTICLE_IMAGE_RELEVANCE_MIN_SCORE: float = 70.0
    ARTICLE_IMAGE_MAX_REGENERATIONS: int = 2
    ARTICLE_IMAGE_FAILURE_POLICY: str = "BLOCK"  # BLOCK, PUBLISH_WITH_APPROVED_FALLBACK, HUMAN_REVIEW
    ARTICLE_IMAGE_DAILY_BUDGET: float = 10.0
    # Every article must ship with a cover image. When True, a failed generative
    # attempt degrades to a procedural/placeholder visual instead of publishing
    # an imageless article. This is the guarantee that fixes intermittent covers.
    ARTICLE_IMAGE_GUARANTEE_IMAGE: bool = True
    STORAGE_DIR: str = "./storage"

    # --- Local Generative AI Provider Settings ---
    LOCAL_IMAGE_MODEL_ID: str = "stabilityai/sd-turbo"
    LOCAL_IMAGE_DEVICE: str = "auto"  # auto, cpu, cuda
    LOCAL_IMAGE_PRECISION: str = "auto"  # auto, fp32, fp16, bfloat16
    LOCAL_IMAGE_WIDTH: int = 512
    LOCAL_IMAGE_HEIGHT: int = 512
    LOCAL_IMAGE_STEPS: int = 1
    LOCAL_IMAGE_GUIDANCE: float = 0.0
    LOCAL_IMAGE_MAX_CONCURRENT_JOBS: int = 1
    LOCAL_IMAGE_MODEL_OFFLOAD: bool = True
    LOCAL_IMAGE_UNLOAD_AFTER_GENERATION: bool = False
    LOCAL_IMAGE_THREAD_LIMIT: int = 4

    # --- Computed Properties ---

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnvironment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == AppEnvironment.TESTING

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous database URL for Alembic migrations."""
        url = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        url = url.replace("sqlite+aiosqlite://", "sqlite://")
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance. Call once per process lifetime."""
    return Settings()


def __getattr__(name: str) -> Any:
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
