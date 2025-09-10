"""
Database fixtures for testing
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from shared.config.settings import TestingSettings
from shared.database.connection import DatabaseManager
from shared.database.models import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine with in-memory SQLite"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session
        await session.rollback()  # Rollback any changes


@pytest.fixture
async def db_session_with_transaction(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback"""
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await transaction.rollback()
    await connection.close()


@pytest.fixture
def test_db_manager(test_engine) -> DatabaseManager:
    """Create test database manager"""
    manager = DatabaseManager()
    manager.engine = test_engine
    manager.session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    return manager


@pytest.fixture
def test_settings():
    """Create test settings"""
    return TestingSettings()


@pytest.fixture
async def clean_database(db_session):
    """Ensure clean database state for each test"""
    # Clear all tables before test
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(f"DELETE FROM {table.name}")
    await db_session.commit()

    yield

    # Rollback any changes after test
    await db_session.rollback()


class DatabaseTestHelper:
    """Helper class for database operations in tests"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_and_commit(self, obj):
        """Create object and commit to database"""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def count_records(self, model_class) -> int:
        """Count records in a table"""
        from sqlalchemy import func, select

        result = await self.session.execute(select(func.count()).select_from(model_class))
        return result.scalar()

    async def get_all_records(self, model_class):
        """Get all records from a table"""
        from sqlalchemy import select

        result = await self.session.execute(select(model_class))
        return result.scalars().all()

    async def clear_table(self, model_class):
        """Clear all records from a table"""
        from sqlalchemy import delete

        await self.session.execute(delete(model_class))
        await self.session.commit()


@pytest.fixture
def db_helper(db_session) -> DatabaseTestHelper:
    """Database helper fixture"""
    return DatabaseTestHelper(db_session)
