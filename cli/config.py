#!/usr/bin/env python3
"""
Configuration Management for Retro CLI
Handles environment variables, database connections, and API credentials
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration"""

    host: str
    port: int
    database: str
    username: str
    password: str
    test_database: Optional[str] = None

    @property
    def url(self) -> str:
        """Get SQLAlchemy database URL"""
        return (
            f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        )

    @property
    def test_url(self) -> str:
        """Get test database URL"""
        test_db = self.test_database or f"{self.database}_test"
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{test_db}"


@dataclass
class ShopifyConfig:
    """Shopify API configuration"""

    shop_name: str
    access_token: str
    api_version: str = "2024-01"

    @property
    def base_url(self) -> str:
        """Get Shopify API base URL"""
        return f"https://{self.shop_name}.myshopify.com/admin/api/{self.api_version}"


@dataclass
class AwinConfig:
    """Awin affiliate network configuration"""

    api_token: str
    advertiser_id: str
    publisher_id: str
    base_url: str = "https://api.awin.com"


@dataclass
class SystemConfig:
    """System and security configuration"""

    encryption_key: str
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    test_mode: bool = False

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test mode"""
        return self.test_mode or self.environment.lower() == "test"


class Config:
    """Main configuration class"""

    def __init__(self):
        self.database = self._load_database_config()
        self.shopify = self._load_shopify_config()
        self.awin = self._load_awin_config()
        self.system = self._load_system_config()

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment"""
        # Check if DATABASE_URL is provided (priority over individual vars)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Parse DATABASE_URL - format: postgresql://user:pass@host:port/database
            # or postgresql+asyncpg://user:pass@host:port/database
            import re

            # Remove protocol variations
            clean_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            clean_url = clean_url.replace("http://", "")  # Remove http:// if present

            # Parse URL with regex
            pattern = r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)"
            match = re.match(pattern, clean_url)

            if match:
                username, password, host, port, database = match.groups()
                return DatabaseConfig(
                    host=host,
                    port=int(port),
                    database=database,
                    username=username,
                    password=password,
                    test_database=os.getenv("DB_TEST_NAME"),
                )

        # Fallback to individual environment variables
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "soleflip"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            test_database=os.getenv("DB_TEST_NAME"),
        )

    def _load_shopify_config(self) -> Optional[ShopifyConfig]:
        """Load Shopify configuration from environment"""
        shop_name = os.getenv("SHOPIFY_SHOP_NAME")
        access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")

        if not shop_name or not access_token:
            return None

        return ShopifyConfig(
            shop_name=shop_name,
            access_token=access_token,
            api_version=os.getenv("SHOPIFY_API_VERSION", "2024-01"),
        )

    def _load_awin_config(self) -> Optional[AwinConfig]:
        """Load Awin configuration from environment"""
        api_token = os.getenv("AWIN_API_TOKEN")
        advertiser_id = os.getenv("AWIN_ADVERTISER_ID")
        publisher_id = os.getenv("AWIN_PUBLISHER_ID")

        if not api_token:
            return None

        return AwinConfig(
            api_token=api_token,
            advertiser_id=advertiser_id or "",
            publisher_id=publisher_id or "",
            base_url=os.getenv("AWIN_BASE_URL", "https://api.awin.com"),
        )

    def _load_system_config(self) -> SystemConfig:
        """Load system configuration from environment"""
        return SystemConfig(
            encryption_key=os.getenv("FIELD_ENCRYPTION_KEY", ""),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            test_mode=os.getenv("TEST_MODE", "false").lower() == "true",
        )

    def validate(self) -> Dict[str, bool]:
        """Validate configuration and return status"""
        status = {
            "database": bool(self.database.username and self.database.password),
            "shopify": self.shopify is not None,
            "awin": self.awin is not None,
            "encryption_key": bool(self.system.encryption_key),
        }

        return status

    def get_connection_string(self, use_test: bool = False) -> str:
        """Get database connection string"""
        if use_test:
            return self.database.test_url
        return self.database.url

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (for debugging)"""
        return {
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "database": self.database.database,
                "username": self.database.username,
                "password": "***" if self.database.password else None,
            },
            "shopify": (
                {
                    "shop_name": self.shopify.shop_name if self.shopify else None,
                    "access_token": "***" if self.shopify and self.shopify.access_token else None,
                    "api_version": self.shopify.api_version if self.shopify else None,
                }
                if self.shopify
                else None
            ),
            "awin": (
                {
                    "api_token": "***" if self.awin and self.awin.api_token else None,
                    "advertiser_id": self.awin.advertiser_id if self.awin else None,
                    "publisher_id": self.awin.publisher_id if self.awin else None,
                }
                if self.awin
                else None
            ),
            "system": {
                "encryption_key": "***" if self.system.encryption_key else None,
                "environment": self.system.environment,
                "debug": self.system.debug,
                "log_level": self.system.log_level,
                "test_mode": self.system.test_mode,
            },
        }


# Global config instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get singleton config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config() -> Config:
    """Reload configuration from environment"""
    global _config_instance
    _config_instance = None
    load_dotenv(override=True)  # Reload .env file
    return get_config()


# Environment variable templates for easy setup
ENV_TEMPLATE = """
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=soleflip
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_TEST_NAME=soleflip_test

# Shopify Configuration (Optional)
SHOPIFY_SHOP_NAME=your-shop-name
SHOPIFY_ACCESS_TOKEN=your_access_token_here
SHOPIFY_API_VERSION=2024-01

# Awin Configuration (Optional)
AWIN_API_TOKEN=your_awin_token_here
AWIN_ADVERTISER_ID=your_advertiser_id
AWIN_PUBLISHER_ID=your_publisher_id

# System Configuration
FIELD_ENCRYPTION_KEY=your_encryption_key_here
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
TEST_MODE=false
"""


def create_env_template(file_path: str = ".env.example"):
    """Create environment template file"""
    with open(file_path, "w") as f:
        f.write(ENV_TEMPLATE.strip())
    print(f"Environment template created at: {file_path}")


if __name__ == "__main__":
    # Demo configuration loading
    config = get_config()

    print("Configuration Status:")
    validation = config.validate()
    for service, status in validation.items():
        status_text = "✓ Configured" if status else "✗ Missing"
        print(f"  {service}: {status_text}")

    print("\nConfiguration Details:")
    import json

    print(json.dumps(config.to_dict(), indent=2))
