"""Application Configuration Management using Pydantic Settings."""

from typing import Literal

from pydantic import Field, field_validator
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
        default="postgresql+asyncpg://schemesaathi:schemesaathi@localhost:5432/schemesaathi_db",
        description="Async SQLAlchemy database connection URI",
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: float = 30.0
    DB_ECHO: bool = False

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URI",
    )
    REDIS_MAX_CONNECTIONS: int = 20

    # Rate Limiting & Security
    RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: list[str] = ["*"]
    SECRET_KEY: str = Field(
        default="insecure-development-secret-key-change-in-production-env",
        description="Cryptographic secret key for signing tokens",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"


settings = Settings()
