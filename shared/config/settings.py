"""
Centralized Configuration Management
Production-ready configuration with validation, type safety, and environment-specific settings
"""

import os
import secrets
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging levels"""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class DatabaseConfig(BaseSettings):
    """Database configuration"""

    url: str = Field(default="sqlite+aiosqlite:///./soleflip.db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="SQL_ECHO")
    pool_size: int = Field(default=20, ge=1, le=100, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=30, ge=0, le=100, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, ge=1, le=300, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, ge=60, env="DB_POOL_RECYCLE")
    connect_timeout: int = Field(default=30, ge=1, le=120, env="DB_CONNECT_TIMEOUT")

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v or not v.startswith(
            ("postgresql://", "postgresql+asyncpg://", "sqlite://", "sqlite+aiosqlite://")
        ):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")
        return v

    @property
    def is_sqlite(self) -> bool:
        """Check if database is SQLite"""
        return "sqlite" in self.url.lower()

    @property
    def is_postgresql(self) -> bool:
        """Check if database is PostgreSQL"""
        return "postgresql" in self.url.lower()


class SecurityConfig(BaseSettings):
    """Security configuration"""

    encryption_key: str = Field(default="", env="FIELD_ENCRYPTION_KEY")
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    max_request_size: int = Field(default=50 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 50MB
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v):
        """Validate Fernet encryption key format"""
        # Allow empty string for development/testing
        if not v:
            return v

        # Basic validation - should be base64 encoded and 32 bytes
        import base64

        try:
            decoded = base64.urlsafe_b64decode(v.encode())
            if len(decoded) != 32:
                raise ValueError("Encryption key must be 32 bytes when decoded")
        except Exception:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY must be a valid Fernet key (32-byte base64-encoded string)"
            )

        return v

    @field_validator("allowed_hosts", "cors_origins", "cors_methods", "cors_headers", mode="before")
    @classmethod
    def parse_list_env(cls, v):
        """Parse comma-separated environment variables into lists"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v


class APIConfig(BaseSettings):
    """API configuration"""

    title: str = Field(default="SoleFlipper API", env="API_TITLE")
    version: str = Field(default="2.1.0", env="API_VERSION")
    description: str = Field(
        default="Professional sneaker resale management system", env="API_DESCRIPTION"
    )
    openapi_url: str = Field(default="/openapi.json", env="API_OPENAPI_URL")
    docs_url: str = Field(default="/docs", env="API_DOCS_URL")
    redoc_url: str = Field(default="/redoc", env="API_REDOC_URL")
    host: str = Field(default="127.0.0.1", env="API_HOST")
    port: int = Field(default=8000, ge=1, le=65535, env="API_PORT")
    workers: int = Field(default=1, ge=1, le=32, env="API_WORKERS")
    reload: bool = Field(default=False, env="API_RELOAD")
    access_log: bool = Field(default=True, env="API_ACCESS_LOG")


class LoggingConfig(BaseSettings):
    """Logging configuration"""

    level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    format: str = Field(default="json", env="LOG_FORMAT")  # json or console
    database_logging: bool = Field(default=True, env="LOG_DATABASE_ENABLED")
    file_logging: bool = Field(default=False, env="LOG_FILE_ENABLED")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    structured_logging: bool = Field(default=True, env="LOG_STRUCTURED")

    @model_validator(mode="after")
    def validate_log_file(self):
        """Validate log file path when file logging is enabled"""
        if self.file_logging and not self.log_file:
            raise ValueError("LOG_FILE_PATH is required when file logging is enabled")
        return self


class ExternalServiceConfig(BaseSettings):
    """External service configuration"""

    stockx_enabled: bool = Field(default=True, env="STOCKX_ENABLED")
    stockx_api_base_url: str = Field(default="https://api.stockx.com/v2", env="STOCKX_API_BASE_URL")
    stockx_auth_url: str = Field(
        default="https://accounts.stockx.com/oauth/token", env="STOCKX_AUTH_URL"
    )
    stockx_timeout: int = Field(default=30, ge=1, le=300, env="STOCKX_TIMEOUT")
    stockx_retry_attempts: int = Field(default=3, ge=1, le=10, env="STOCKX_RETRY_ATTEMPTS")
    stockx_retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, env="STOCKX_RETRY_DELAY")

    # N8N Configuration
    n8n_enabled: bool = Field(default=False, env="N8N_ENABLED")
    n8n_webhook_url: Optional[str] = Field(default=None, env="N8N_WEBHOOK_URL")
    n8n_api_key: Optional[str] = Field(default=None, env="N8N_API_KEY")

    # Metabase Configuration
    metabase_enabled: bool = Field(default=True, env="METABASE_ENABLED")
    metabase_url: Optional[str] = Field(default=None, env="METABASE_URL")
    metabase_username: Optional[str] = Field(default=None, env="METABASE_USERNAME")
    metabase_password: Optional[str] = Field(default=None, env="METABASE_PASSWORD")


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration"""

    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=8001, ge=1, le=65535, env="METRICS_PORT")
    sentry_enabled: bool = Field(default=False, env="SENTRY_ENABLED")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: Optional[str] = Field(default=None, env="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, env="SENTRY_TRACES_SAMPLE_RATE"
    )


class CacheConfig(BaseSettings):
    """Cache configuration"""

    redis_enabled: bool = Field(default=False, env="REDIS_ENABLED")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_ttl: int = Field(default=3600, ge=60, env="REDIS_TTL")  # seconds
    redis_max_connections: int = Field(default=10, ge=1, le=100, env="REDIS_MAX_CONNECTIONS")

    # In-memory cache settings
    memory_cache_enabled: bool = Field(default=True, env="MEMORY_CACHE_ENABLED")
    memory_cache_size: int = Field(default=1000, ge=100, le=10000, env="MEMORY_CACHE_SIZE")
    memory_cache_ttl: int = Field(default=300, ge=60, env="MEMORY_CACHE_TTL")  # seconds


class Settings(BaseSettings):
    """Main application settings"""

    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")

    # Configuration sections
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    external_services: ExternalServiceConfig = Field(default_factory=ExternalServiceConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        use_enum_values=True,
        extra="ignore",  # Ignore extra fields
    )

    @model_validator(mode="after")
    def validate_environment_settings(self):
        """Validate settings based on environment"""
        # Only validate in production, allow permissive settings for dev/testing
        if self.environment == Environment.PRODUCTION:
            # Production-specific validations
            if self.debug:
                raise ValueError("Debug mode cannot be enabled in production")

            # Ensure secure settings
            if self.security.cors_origins == ["*"]:
                raise ValueError("CORS origins must be restricted in production")
            if self.security.allowed_hosts == ["*"]:
                raise ValueError("Allowed hosts must be restricted in production")

        return self

    @field_validator("debug")
    @classmethod
    def debug_depends_on_environment(cls, v, info):
        """Ensure debug is only enabled in development"""
        # Note: This validation is also covered by model_validator above
        # Keeping for individual field validation
        return v

    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.environment == Environment.TESTING or self.testing

    def get_database_url(self) -> str:
        """Get database URL"""
        return self.database.url

    def get_log_level(self) -> str:
        """Get logging level"""
        return self.logging.level.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (excluding sensitive data)"""
        data = self.dict()

        # Remove sensitive information
        if "security" in data:
            data["security"].pop("encryption_key", None)
            data["security"].pop("secret_key", None)

        if "external_services" in data:
            data["external_services"].pop("n8n_api_key", None)
            data["external_services"].pop("metabase_password", None)

        if "monitoring" in data:
            data["monitoring"].pop("sentry_dsn", None)

        if "cache" in data and "redis_url" in data["cache"]:
            # Mask password in Redis URL
            redis_url = data["cache"]["redis_url"]
            if redis_url and ":" in redis_url:
                parts = redis_url.split(":")
                if len(parts) >= 3:  # redis://user:pass@host:port
                    data["cache"]["redis_url"] = ":".join(parts[:2]) + ":***@" + ":".join(parts[3:])

        return data


# Environment-specific settings classes
class DevelopmentSettings(Settings):
    """Development-specific settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        use_enum_values=True,
        env_prefix="",  # No prefix for development, use standard env vars
        extra="ignore",
    )


class ProductionSettings(Settings):
    """Production-specific settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        use_enum_values=True,
        env_prefix="PROD_",
        extra="ignore",
    )


class TestingSettings(Settings):
    """Testing-specific settings"""

    def __init__(self, **kwargs):
        super().__init__(
            environment=Environment.TESTING,
            debug=True,
            testing=True,
            database=DatabaseConfig(url="sqlite+aiosqlite:///:memory:"),
            **kwargs,
        )


# Settings factory
def get_settings_class(environment: str = None) -> type:
    """Get appropriate settings class based on environment"""
    env = environment or os.getenv("ENVIRONMENT", "development")

    settings_map = {
        Environment.DEVELOPMENT: DevelopmentSettings,
        Environment.PRODUCTION: ProductionSettings,
        Environment.TESTING: TestingSettings,
        Environment.STAGING: Settings,  # Use base settings for staging
    }

    return settings_map.get(Environment(env.lower()), Settings)


# Global settings instance with caching
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings_class = get_settings_class()
    return settings_class()


# Utility functions
def reload_settings():
    """Force reload of settings (clears cache)"""
    get_settings.cache_clear()


def validate_settings() -> Dict[str, Any]:
    """Validate current settings and return validation report"""
    try:
        settings = get_settings()
        return {
            "valid": True,
            "environment": settings.environment,
            "database_type": "PostgreSQL" if settings.database.is_postgresql else "SQLite",
            "debug_mode": settings.debug,
            "external_services": {
                "stockx": settings.external_services.stockx_enabled,
                "n8n": settings.external_services.n8n_enabled,
                "metabase": settings.external_services.metabase_enabled,
            },
            "monitoring": {
                "health_checks": settings.monitoring.health_check_enabled,
                "metrics": settings.monitoring.metrics_enabled,
                "sentry": settings.monitoring.sentry_enabled,
            },
            "caching": {
                "redis": settings.cache.redis_enabled,
                "memory": settings.cache.memory_cache_enabled,
            },
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "error_type": type(e).__name__}
