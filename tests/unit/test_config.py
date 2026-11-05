"""Unit Tests for Configuration Management."""

from src.core.config import Settings


def test_default_settings() -> None:
    """Verify default application settings are properly initialized."""
    config = Settings()
    assert config.PROJECT_NAME == "SchemeSaathi"
    assert config.API_V1_PREFIX == "/api/v1"
    assert config.ENVIRONMENT in ["development", "testing", "staging", "production"]
    assert config.DB_POOL_SIZE == 20
    assert config.DB_MAX_OVERFLOW == 10
    assert config.REDIS_MAX_CONNECTIONS == 20
    assert not config.is_production


def test_cors_origins_parsing() -> None:
    """Test assembling CORS origins from list or comma-separated string."""
    # List of strings
    config1 = Settings(CORS_ORIGINS=["https://schemesaathi.in", "http://localhost:3000"])
    assert len(config1.CORS_ORIGINS) == 2
    assert "https://schemesaathi.in" in config1.CORS_ORIGINS

    # Comma-separated string
    config2 = Settings(CORS_ORIGINS="https://schemesaathi.in, http://localhost:3000")
    assert len(config2.CORS_ORIGINS) == 2
    assert "http://localhost:3000" in config2.CORS_ORIGINS


def test_environment_flags() -> None:
    """Test environment status properties."""
    prod_config = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="valid-secure-production-secret-key-32chars",
        ADMIN_API_KEY="valid-admin-api-key-32chars",
    )
    assert prod_config.is_production
    assert not prod_config.is_testing

    test_config = Settings(ENVIRONMENT="testing")
    assert test_config.is_testing
    assert not test_config.is_production
