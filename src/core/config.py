"""Application Configuration Management using Pydantic Settings."""

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SchemeSaathi Application Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Metadata
    PROJECT_NAME: str = "SchemeSaathi"
    VERSION: str = "0.1.0-m1.sprint1"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = False

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # PostgreSQL Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://schemesaathi:schemesaathi_dev_password@localhost:5432/schemesaathi_db",
        description="Async SQLAlchemy database connection URI",
    )
    DB_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Base persistent connection pool size per worker (2 workers * 10 = 20)",
    )
    DB_MAX_OVERFLOW: int = Field(
        default=5,
        ge=0,
        le=50,
        description="Max burst connections beyond pool size per worker (2 workers * 5 = 10, total max 30)",
    )
    DB_POOL_TIMEOUT: float = Field(
        default=30.0, ge=1.0, description="Seconds to wait before raising pool timeout"
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800, ge=60, description="Seconds after which connections are recycled"
    )
    DB_STATEMENT_TIMEOUT_MS: int = Field(
        default=30000, ge=1000, description="PostgreSQL query execution statement timeout in ms"
    )
    DB_ECHO: bool = False

    # Ingestion & Document Guardrails
    STORAGE_BASE_DIR: str = Field(
        default="data/storage",
        description="Base directory for immutable document storage",
    )
    MAX_INGESTION_FILE_SIZE_BYTES: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=50 * 1024 * 1024,
        description="Maximum permitted document upload size in bytes (default 10 MB)",
    )
    MAX_ENCODED_DOCUMENT_LENGTH: int = Field(
        default=14_000_000,
        description="Maximum length of base64 document payload string (~13.98 MB for 10 MB decoded)",
    )
    MAX_REQUEST_BODY_SIZE_BYTES: int = Field(
        default=15 * 1024 * 1024,
        description="Maximum raw HTTP request body size in bytes before middleware rejection (default 15 MB)",
    )

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URI",
    )
    REDIS_MAX_CONNECTIONS: int = 20

    # Rate Limiting & Security
    RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    SECRET_KEY: str = Field(
        default="insecure-development-secret-key-change-in-production-env",
        description="Cryptographic secret key for signing tokens",
    )
    ADMIN_API_KEY: str | None = Field(
        default=None,
        description="Administrative secret API key for write endpoints (must be set in environment)",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Fail safe: enforce strict security configuration in production mode."""
        if self.is_production:
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production environment.")
            if (
                not self.SECRET_KEY
                or self.SECRET_KEY == "insecure-development-secret-key-change-in-production-env"
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    "SECRET_KEY must be a cryptographically secure random token (>= 32 chars) in production."
                )
            if not self.ADMIN_API_KEY or len(self.ADMIN_API_KEY) < 16:
                raise ValueError(
                    "ADMIN_API_KEY must be configured and >= 16 characters in production environment."
                )
            if self.CORS_ALLOW_CREDENTIALS and ("*" in self.CORS_ORIGINS):
                raise ValueError(
                    "CORS_ORIGINS cannot contain wildcard '*' when CORS_ALLOW_CREDENTIALS is True in production."
                )
            if "sqlite" in self.DATABASE_URL.lower():
                raise ValueError("SQLite is strictly forbidden in production environment.")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"


settings = Settings()
