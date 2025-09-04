"""
Database Connection Management
Production-ready PostgreSQL connection with pooling,
health checks, and migration support.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load environment variables from .env file
load_dotenv()

from .models import Base

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Central database connection manager"""

    def __init__(self):
        # Use SQLite for demo/development (switch to PostgreSQL for production)
        import os

        if os.getenv("DATABASE_URL"):
            self.database_url = os.getenv("DATABASE_URL")
        else:
            # Demo mode with SQLite
            self.database_url = "sqlite+aiosqlite:///./soleflip_demo.db"

        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection and session factory"""
        logger.info("Initializing database connection...")

        # Create async engine with connection pooling options for PostgreSQL
        engine_args = {
            "future": True,
            "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
            "echo_pool": False,
        }
        if "sqlite" not in self.database_url:
            engine_args.update(
                {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_timeout": 30,
                    "pool_recycle": 1800,
                    "pool_pre_ping": True,
                    "pool_reset_on_return": "commit",
                }
            )

        self.engine = create_async_engine(self.database_url, **engine_args)

        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Test connection
        await self.test_connection()

        logger.info("Database connection initialized successfully")

    async def test_connection(self):
        """Test database connectivity"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error("Database connection test failed", error=str(e))
            raise

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def run_migrations(self):
        """Run database migrations"""
        logger.info("Running database migrations...")

        try:
            # Handle different database types
            if "sqlite" in self.database_url:
                # SQLite doesn't support schemas or extensions - just create tables
                async with self.engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                    logger.info("SQLite tables created successfully")
            else:
                # PostgreSQL-specific setup
                async with self.engine.begin() as conn:
                    # Create extensions
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

                    # Create schemas
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS products"))
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sales"))
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS integration"))
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS logging"))

                    # Create all tables
                    await conn.run_sync(Base.metadata.create_all)

            logger.info("Database migrations completed successfully")

        except Exception as e:
            logger.error("Database migration failed", error=str(e))
            raise

    async def get_health_status(self) -> dict:
        """Get database health status for monitoring"""
        try:
            async with self.engine.begin() as conn:
                # Test basic connectivity
                await conn.execute(text("SELECT 1"))

                # Get connection pool status
                pool = self.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": getattr(pool, "_invalidated", 0),
                }

                # Database-specific stats
                if "sqlite" in self.database_url:
                    db_stats = {"database_type": "SQLite", "database_name": "soleflip_demo.db"}
                else:
                    # PostgreSQL-specific stats
                    stats_query = text(
                        """
                        SELECT 
                            count(*) as active_connections,
                            current_database() as database_name,
                            version() as postgresql_version
                        FROM pg_stat_activity 
                        WHERE datname = current_database()
                    """
                    )

                    result = await conn.execute(stats_query)
                    db_stats = result.fetchone()._asdict()

                return {
                    "status": "healthy",
                    "pool": pool_status,
                    "database": db_stats,
                    "url": (
                        self.database_url.split("@")[1] if "@" in self.database_url else "hidden"
                    ),
                }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "error_type": type(e).__name__}


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI routes
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with db_manager.get_session() as session:
        yield session


# Utility functions for common database operations
async def execute_query(query: str, params: dict = None) -> list:
    """Execute raw SQL query and return results"""
    async with db_manager.get_session() as session:
        result = await session.execute(text(query), params or {})
        return [row._asdict() for row in result.fetchall()]


async def execute_scalar(query: str, params: dict = None):
    """Execute query and return single scalar value"""
    async with db_manager.get_session() as session:
        result = await session.execute(text(query), params or {})
        return result.scalar()


async def execute_transaction(queries: list[tuple[str, dict]]) -> None:
    """Execute multiple queries in a single transaction"""
    async with db_manager.get_session() as session:
        try:
            for query, params in queries:
                await session.execute(text(query), params or {})
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class DatabaseHealthCheck:
    """Health check implementation for database"""

    @staticmethod
    async def check() -> bool:
        """Perform health check"""
        try:
            health_status = await db_manager.get_health_status()
            return health_status.get("status") == "healthy"
        except Exception:
            return False

    @staticmethod
    async def detailed_status() -> dict:
        """Get detailed health status"""
        return await db_manager.get_health_status()
