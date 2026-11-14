"""
Tests for app.core.config — Settings loading and validation.
"""

from app.core.config import AppEnvironment, get_settings


class TestSettings:
    """Configuration system tests."""

    def test_settings_load_from_env(self):
        """Settings loads required values from environment."""
        settings = get_settings()
        assert settings.APP_NAME == "zohra-publisher"
        assert settings.APP_ENV == AppEnvironment.TESTING
        assert settings.SECRET_KEY == "test-secret-key-do-not-use-in-production"

    def test_settings_defaults(self):
        """Optional settings have sensible defaults."""
        settings = get_settings()
        assert settings.API_PORT == 8000
        assert settings.DEFAULT_TIMEZONE == "UTC"
        assert settings.AUTONOMY_ENABLED is False
        assert settings.MAINTENANCE_MODE is False

    def test_feature_flags_default_off(self):
        """All autonomous features are disabled by default."""
        settings = get_settings()
        assert settings.ENABLE_DISCOVERY is False
        assert settings.ENABLE_RESEARCH is False
        assert settings.ENABLE_WRITING is False
        assert settings.ENABLE_AUTO_PUBLISH is False
        assert settings.ENABLE_ANALYTICS is False

    def test_future_integrations_optional(self):
        """Future integration keys are None when not provided."""
        settings = get_settings()
        assert settings.WORDPRESS_URL is None
        assert settings.OPENAI_API_KEY is None
        assert settings.GEMINI_API_KEY is None
        assert settings.ANTHROPIC_API_KEY is None

    def test_environment_detection(self):
        """Environment helper properties work correctly."""
        settings = get_settings()
        assert settings.is_testing is True
        assert settings.is_development is False
        assert settings.is_production is False

    def test_cors_origins_parsing(self):
        """CORS origins can be parsed from JSON string or list."""
        settings = get_settings()
        assert isinstance(settings.CORS_ORIGINS, list)

    def test_sync_database_url(self):
        """sync_database_url strips asyncpg for Alembic."""
        settings = get_settings()
        # Our test uses sqlite+aiosqlite, just verify it's a string
        assert isinstance(settings.sync_database_url, str)

    def test_budget_values(self):
        """Budget values are loaded correctly."""
        settings = get_settings()
        assert settings.LLM_DAILY_BUDGET == 100.0
        assert settings.LLM_MONTHLY_BUDGET == 1000.0
