"""
Unit tests for configuration settings
Testing Pydantic models, validators, and business logic for 100% coverage
"""

import base64
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from shared.config.settings import (
    APIConfig,
    CacheConfig,
    DatabaseConfig,
    DevelopmentSettings,
    Environment,
    ExternalServiceConfig,
    LoggingConfig,
    LogLevel,
    MonitoringConfig,
    ProductionSettings,
    SecurityConfig,
    Settings,
    TestingSettings,
    get_settings,
    get_settings_class,
    reload_settings,
    validate_settings,
)


class TestEnvironmentEnum:
    """Test Environment enum values"""

    def test_environment_values(self):
        """Test all environment enum values"""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"


class TestLogLevelEnum:
    """Test LogLevel enum values"""

    def test_log_level_values(self):
        """Test all log level enum values"""
        assert LogLevel.CRITICAL == "CRITICAL"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.DEBUG == "DEBUG"


class TestDatabaseConfig:
    """Test DatabaseConfig validation and properties"""

    def test_database_config_defaults(self):
        """Test default database configuration"""
        config = DatabaseConfig()

        assert config.url == "sqlite+aiosqlite:///./soleflip.db"
        assert config.echo is False
        assert config.pool_size == 20
        assert config.max_overflow == 30
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

    def test_database_config_postgresql_url(self):
        """Test PostgreSQL URL validation"""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        assert config.url == "postgresql://user:pass@localhost/db"

        config = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/db")
        assert config.url == "postgresql+asyncpg://user:pass@localhost/db"

    def test_database_config_sqlite_url(self):
        """Test SQLite URL validation"""
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config.url == "sqlite:///test.db"

        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        assert config.url == "sqlite+aiosqlite:///:memory:"

    def test_database_config_invalid_url(self):
        """Test invalid database URL validation"""
        with pytest.raises(ValidationError, match="DATABASE_URL must be a valid"):
            DatabaseConfig(url="mysql://invalid")

        with pytest.raises(ValidationError, match="DATABASE_URL must be a valid"):
            DatabaseConfig(url="")

        with pytest.raises(ValidationError, match="DATABASE_URL must be a valid"):
            DatabaseConfig(url="not-a-url")

    def test_is_sqlite_property(self):
        """Test is_sqlite property"""
        sqlite_config = DatabaseConfig(url="sqlite+aiosqlite:///test.db")
        assert sqlite_config.is_sqlite is True

        postgres_config = DatabaseConfig(url="postgresql://localhost/test")
        assert postgres_config.is_sqlite is False

    def test_is_postgresql_property(self):
        """Test is_postgresql property"""
        postgres_config = DatabaseConfig(url="postgresql://localhost/test")
        assert postgres_config.is_postgresql is True

        sqlite_config = DatabaseConfig(url="sqlite:///test.db")
        assert sqlite_config.is_postgresql is False

    def test_database_config_bounds(self):
        """Test database config bounds validation"""
        # Test valid bounds
        config = DatabaseConfig(pool_size=1, max_overflow=0, pool_timeout=1, pool_recycle=60)
        assert config.pool_size == 1

        # Test invalid bounds
        with pytest.raises(ValidationError):
            DatabaseConfig(pool_size=0)  # below minimum

        with pytest.raises(ValidationError):
            DatabaseConfig(pool_size=101)  # above maximum

        with pytest.raises(ValidationError):
            DatabaseConfig(pool_timeout=0)  # below minimum


class TestSecurityConfig:
    """Test SecurityConfig validation and methods"""

    def test_security_config_defaults(self):
        """Test default security configuration"""
        config = SecurityConfig()

        assert config.encryption_key == ""
        assert len(config.secret_key) > 20  # Generated token
        assert config.allowed_hosts == ["*"]
        assert config.cors_origins == ["*"]
        assert config.rate_limit_enabled is True

    def test_encryption_key_validation_empty(self):
        """Test empty encryption key is allowed"""
        config = SecurityConfig(encryption_key="")
        assert config.encryption_key == ""

    def test_encryption_key_validation_valid(self):
        """Test valid encryption key"""
        # Generate a valid Fernet key
        key = base64.urlsafe_b64encode(b"0" * 32).decode()
        config = SecurityConfig(encryption_key=key)
        assert config.encryption_key == key

    def test_encryption_key_validation_invalid_format(self):
        """Test invalid encryption key format"""
        with pytest.raises(ValidationError, match="valid Fernet key"):
            SecurityConfig(encryption_key="invalid-key")

    def test_encryption_key_validation_wrong_length(self):
        """Test encryption key with wrong length"""
        # 16 bytes instead of 32
        short_key = base64.urlsafe_b64encode(b"0" * 16).decode()
        with pytest.raises(ValidationError, match="32-byte base64-encoded string"):
            SecurityConfig(encryption_key=short_key)

    def test_parse_list_env_string(self):
        """Test parsing comma-separated string to list"""
        config = SecurityConfig(
            allowed_hosts="localhost,127.0.0.1,example.com",
            cors_origins="http://localhost:3000,https://app.example.com",
        )

        assert config.allowed_hosts == ["localhost", "127.0.0.1", "example.com"]
        assert config.cors_origins == ["http://localhost:3000", "https://app.example.com"]

    def test_parse_list_env_already_list(self):
        """Test parsing when value is already a list"""
        hosts = ["localhost", "127.0.0.1"]
        config = SecurityConfig(allowed_hosts=hosts)
        assert config.allowed_hosts == hosts


class TestAPIConfig:
    """Test APIConfig validation"""

    def test_api_config_defaults(self):
        """Test default API configuration"""
        config = APIConfig()

        assert config.title == "SoleFlipper API"
        assert config.version == "0.9.0"
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.workers == 1

    def test_api_config_port_validation(self):
        """Test API port validation"""
        # Valid ports
        config = APIConfig(port=8080)
        assert config.port == 8080

        config = APIConfig(port=65535)
        assert config.port == 65535

        # Invalid ports
        with pytest.raises(ValidationError):
            APIConfig(port=0)

        with pytest.raises(ValidationError):
            APIConfig(port=65536)


class TestLoggingConfig:
    """Test LoggingConfig validation"""

    def test_logging_config_defaults(self):
        """Test default logging configuration"""
        config = LoggingConfig()

        assert config.level == LogLevel.INFO
        assert config.format == "json"
        assert config.database_logging is True
        assert config.file_logging is False

    def test_logging_config_file_logging_without_path(self):
        """Test file logging enabled without path"""
        with pytest.raises(ValidationError, match="LOG_FILE_PATH is required"):
            LoggingConfig(file_logging=True, log_file=None)

    def test_logging_config_file_logging_with_path(self):
        """Test file logging enabled with valid path"""
        config = LoggingConfig(file_logging=True, log_file="/var/log/app.log")
        assert config.file_logging is True
        assert config.log_file == "/var/log/app.log"

    def test_logging_config_file_logging_disabled(self):
        """Test file logging disabled doesn't require path"""
        config = LoggingConfig(file_logging=False, log_file=None)
        assert config.file_logging is False
        assert config.log_file is None


class TestExternalServiceConfig:
    """Test ExternalServiceConfig"""

    def test_external_service_config_defaults(self):
        """Test default external service configuration"""
        config = ExternalServiceConfig()

        assert config.stockx_enabled is True
        assert config.stockx_api_base_url == "https://api.stockx.com/v2"
        assert config.stockx_timeout == 30
        assert config.n8n_enabled is False
        assert config.metabase_enabled is True


class TestMonitoringConfig:
    """Test MonitoringConfig"""

    def test_monitoring_config_defaults(self):
        """Test default monitoring configuration"""
        config = MonitoringConfig()

        assert config.health_check_enabled is True
        assert config.metrics_enabled is True
        assert config.sentry_enabled is False
        assert config.sentry_traces_sample_rate == 0.1


class TestCacheConfig:
    """Test CacheConfig"""

    def test_cache_config_defaults(self):
        """Test default cache configuration"""
        config = CacheConfig()

        assert config.redis_enabled is False
        assert config.memory_cache_enabled is True
        assert config.redis_ttl == 3600
        assert config.memory_cache_size == 1000


class TestSettings:
    """Test main Settings class"""

    def test_settings_defaults(self):
        """Test default settings"""
        settings = Settings()

        assert settings.environment == Environment.DEVELOPMENT
        assert settings.debug is False
        assert settings.testing is False
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.security, SecurityConfig)

    def test_settings_environment_methods(self):
        """Test environment check methods"""
        dev_settings = Settings(environment=Environment.DEVELOPMENT)
        assert dev_settings.is_development() is True
        assert dev_settings.is_production() is False
        assert dev_settings.is_testing() is False

        prod_settings = Settings(
            environment=Environment.PRODUCTION,
            security=SecurityConfig(
                cors_origins=["https://example.com"], allowed_hosts=["example.com"]
            ),
        )
        assert prod_settings.is_development() is False
        assert prod_settings.is_production() is True
        assert prod_settings.is_testing() is False

        test_settings = Settings(environment=Environment.TESTING)
        assert test_settings.is_testing() is True

        testing_flag_settings = Settings(testing=True)
        assert testing_flag_settings.is_testing() is True

    def test_settings_utility_methods(self):
        """Test utility methods"""
        settings = Settings(
            database=DatabaseConfig(url="postgresql://localhost/test"),
            logging=LoggingConfig(level=LogLevel.DEBUG),
        )

        assert settings.get_database_url() == "postgresql://localhost/test"
        assert settings.get_log_level() == "DEBUG"

    def test_production_validation_debug_enabled(self):
        """Test production validation fails with debug enabled"""
        with pytest.raises(ValidationError, match="Debug mode cannot be enabled in production"):
            Settings(environment=Environment.PRODUCTION, debug=True)

    def test_production_validation_cors_wildcard(self):
        """Test production validation fails with CORS wildcard"""
        with pytest.raises(ValidationError, match="CORS origins must be restricted"):
            Settings(
                environment=Environment.PRODUCTION, security=SecurityConfig(cors_origins=["*"])
            )

    def test_production_validation_allowed_hosts_wildcard(self):
        """Test production validation fails with allowed hosts wildcard"""
        with pytest.raises(ValidationError, match="Allowed hosts must be restricted"):
            Settings(
                environment=Environment.PRODUCTION,
                security=SecurityConfig(cors_origins=["https://example.com"], allowed_hosts=["*"]),
            )

    def test_production_validation_success(self):
        """Test production validation succeeds with proper settings"""
        settings = Settings(
            environment=Environment.PRODUCTION,
            debug=False,
            security=SecurityConfig(
                cors_origins=["https://app.example.com"],
                allowed_hosts=["app.example.com", "api.example.com"],
            ),
        )

        assert settings.environment == Environment.PRODUCTION
        assert settings.debug is False

    def test_to_dict_excludes_sensitive_data(self):
        """Test to_dict method excludes sensitive information"""
        from cryptography.fernet import Fernet

        valid_key = Fernet.generate_key().decode()
        settings = Settings(
            security=SecurityConfig(encryption_key=valid_key, secret_key="secret-jwt-key"),
            external_services=ExternalServiceConfig(
                n8n_api_key="secret-n8n-key", metabase_password="secret-password"
            ),
            monitoring=MonitoringConfig(sentry_dsn="https://key@sentry.io/project"),
            cache=CacheConfig(redis_url="redis://user:password@localhost:6379/0"),
        )

        data = settings.to_dict()

        # Check sensitive data is removed
        assert "encryption_key" not in data["security"]
        assert "secret_key" not in data["security"]
        assert "n8n_api_key" not in data["external_services"]
        assert "metabase_password" not in data["external_services"]
        assert "sentry_dsn" not in data["monitoring"]
        assert "password" not in data["cache"]["redis_url"]
        assert "***" in data["cache"]["redis_url"]


class TestSpecializedSettings:
    """Test specialized settings classes"""

    def test_development_settings(self):
        """Test development settings class"""
        settings = DevelopmentSettings()
        assert isinstance(settings, Settings)
        # Should inherit all base functionality

    def test_production_settings(self):
        """Test production settings class"""
        settings = ProductionSettings()
        assert isinstance(settings, Settings)
        # Should inherit all base functionality

    def test_testing_settings(self):
        """Test testing settings class"""
        settings = TestingSettings()

        assert settings.environment == Environment.TESTING
        assert settings.debug is True
        assert settings.testing is True
        assert "memory" in settings.database.url


class TestSettingsFactory:
    """Test settings factory functions"""

    def test_get_settings_class_development(self):
        """Test get_settings_class for development"""
        cls = get_settings_class("development")
        assert cls == DevelopmentSettings

    def test_get_settings_class_production(self):
        """Test get_settings_class for production"""
        cls = get_settings_class("production")
        assert cls == ProductionSettings

    def test_get_settings_class_testing(self):
        """Test get_settings_class for testing"""
        cls = get_settings_class("testing")
        assert cls == TestingSettings

    def test_get_settings_class_staging(self):
        """Test get_settings_class for staging"""
        cls = get_settings_class("staging")
        assert cls == Settings

    def test_get_settings_class_unknown(self):
        """Test get_settings_class for unknown environment raises ValueError"""
        with pytest.raises(ValueError, match="is not a valid Environment"):
            get_settings_class("unknown")

    def test_get_settings_class_from_env(self):
        """Test get_settings_class reads from environment"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            cls = get_settings_class()
            assert cls == ProductionSettings

    def test_get_settings_cached(self):
        """Test get_settings returns cached instance"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reload_settings_clears_cache(self):
        """Test reload_settings clears the cache"""
        settings1 = get_settings()
        reload_settings()
        settings2 = get_settings()
        assert settings1 is not settings2

    def test_validate_settings_success(self):
        """Test validate_settings with valid configuration"""
        result = validate_settings()

        assert result["valid"] is True
        assert "environment" in result
        assert "database_type" in result
        assert "external_services" in result
        assert "monitoring" in result
        assert "caching" in result

        # Check structure
        assert "stockx" in result["external_services"]
        assert "health_checks" in result["monitoring"]
        assert "redis" in result["caching"]

    def test_validate_settings_with_error(self):
        """Test validate_settings handles errors gracefully"""
        # Mock get_settings to raise an exception
        with patch("shared.config.settings.get_settings") as mock_get:
            mock_get.side_effect = ValueError("Test error")

            result = validate_settings()

            assert result["valid"] is False
            assert result["error"] == "Test error"
            assert result["error_type"] == "ValueError"


class TestEnvironmentVariableHandling:
    """Test environment variable parsing"""

    def test_list_parsing_with_spaces(self):
        """Test list parsing handles spaces correctly"""
        SecurityConfig()

        # Test the static method directly
        parsed = SecurityConfig.parse_list_env("  item1 ,  item2  , item3  ")
        assert parsed == ["item1", "item2", "item3"]

    def test_list_parsing_single_item(self):
        """Test list parsing with single item"""
        SecurityConfig()
        parsed = SecurityConfig.parse_list_env("single-item")
        assert parsed == ["single-item"]

    def test_field_validator_debug_method(self):
        """Test debug field validator method exists and works"""
        # This tests the debug_depends_on_environment validator
        result = Settings.debug_depends_on_environment(True, None)
        assert result is True

        result = Settings.debug_depends_on_environment(False, None)
        assert result is False
