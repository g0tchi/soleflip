"""
Memori MCP Server Configuration
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoriMCPSettings(BaseSettings):
    """Configuration for Memori MCP Server."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql://soleflip:password@postgres:5432/memori",
        description="PostgreSQL connection URL for Memori",
    )

    # Memory Configuration
    namespace: str = Field(
        default="soleflip",
        description="Default namespace for memory organization",
    )

    conscious_ingest: bool = Field(
        default=True,
        description="Enable conscious memory ingestion (AI-powered)",
    )

    auto_ingest: bool = Field(
        default=True,
        description="Automatically ingest conversations",
    )

    # Optional: OpenAI API Key for embeddings/ingestion
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for embeddings (if using OpenAI)",
    )

    # Logging
    logging_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )

    # Performance
    max_memories_per_query: int = Field(
        default=5,
        description="Maximum memories to return per search query",
    )

    context_limit: int = Field(
        default=3,
        description="Maximum memories to include in context",
    )


# Singleton instance
settings = MemoriMCPSettings()
