"""Unit Tests for Production Configuration Fail-Safe Validation (Work Item R5)."""

import pytest

from src.core.config import Settings


def test_production_fails_safe_with_default_secret_key() -> None:
    """Verify production settings fail validation if default SECRET_KEY is used."""
    with pytest.raises(
        ValueError, match="SECRET_KEY must be a cryptographically secure random token"
    ):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            ADMIN_API_KEY="super-secret-admin-key-32chars",
            SECRET_KEY="insecure-development-secret-key-change-in-production-env",
            DATABASE_URL="postgresql+asyncpg://schemesaathi:strongpass@prod-db:5432/schemesaathi_db",
        )


def test_production_fails_safe_with_missing_admin_api_key() -> None:
    """Verify production settings fail validation if ADMIN_API_KEY is not configured."""
    with pytest.raises(ValueError, match="ADMIN_API_KEY must be configured"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            ADMIN_API_KEY=None,
            SECRET_KEY="a-very-long-and-secure-random-token-for-production-use",
            DATABASE_URL="postgresql+asyncpg://schemesaathi:strongpass@prod-db:5432/schemesaathi_db",
        )


def test_production_fails_safe_with_short_admin_api_key() -> None:
    """Verify production settings fail validation if ADMIN_API_KEY is less than 16 chars."""
    with pytest.raises(ValueError, match="ADMIN_API_KEY must be configured and >= 16 characters"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            ADMIN_API_KEY="too-short-key",
            SECRET_KEY="a-very-long-and-secure-random-token-for-production-use",
            DATABASE_URL="postgresql+asyncpg://schemesaathi:strongpass@prod-db:5432/schemesaathi_db",
        )


def test_production_fails_safe_with_debug_enabled() -> None:
    """Verify production settings fail validation if DEBUG is True."""
    with pytest.raises(ValueError, match="DEBUG must be False in production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            ADMIN_API_KEY="super-secret-admin-key-32chars",
            SECRET_KEY="a-very-long-and-secure-random-token-for-production-use",
            DATABASE_URL="postgresql+asyncpg://schemesaathi:strongpass@prod-db:5432/schemesaathi_db",
        )


def test_production_fails_safe_with_sqlite_database() -> None:
    """Verify production settings fail validation if SQLite is used."""
    with pytest.raises(ValueError, match="SQLite is strictly forbidden"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            ADMIN_API_KEY="super-secret-admin-key-32chars",
            SECRET_KEY="a-very-long-and-secure-random-token-for-production-use",
            DATABASE_URL="sqlite+aiosqlite:///production.db",
        )


def test_production_valid_configuration_succeeds() -> None:
    """Verify production settings succeed when fully and safely configured."""
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        ADMIN_API_KEY="secure-production-admin-api-key-32chars",
        SECRET_KEY="secure-production-jwt-signing-secret-key-64charslong1234567890",
        DATABASE_URL="postgresql+asyncpg://prod_user:strongpassword123@prod-cluster:5432/schemesaathi_prod",
    )
    assert settings.is_production is True
    assert settings.DEBUG is False
    assert settings.ADMIN_API_KEY == "secure-production-admin-api-key-32chars"
