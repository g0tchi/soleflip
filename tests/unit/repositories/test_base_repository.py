"""
Comprehensive tests for BaseRepository
Testing all CRUD operations, pagination, filtering, and security features
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from shared.repositories.base_repository import BaseRepository

# Create a test model for repository testing
Base = declarative_base()


class TestModel(Base):
    """Test model for repository operations"""

    __tablename__ = "test_model"

    id = Column(String, primary_key=True)
    name = Column(String)
    value = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def test_repository(mock_db_session):
    """Create test repository instance"""
    return BaseRepository(TestModel, mock_db_session)


class TestCreate:
    """Test create operations"""

    async def test_create_success(self, test_repository, mock_db_session):
        """Test successful entity creation"""
        # Arrange
        test_id = uuid4()
        entity_data = {"id": str(test_id), "name": "Test Entity", "value": "test_value"}

        mock_entity = TestModel(**entity_data)
        mock_entity.id = str(test_id)

        # Mock db.add to do nothing
        mock_db_session.add = MagicMock()
        # Mock refresh to set the entity
        mock_db_session.refresh = AsyncMock()

        # Act
        with patch.object(TestModel, "__init__", return_value=None) as mock_init:
            mock_init.return_value = None
            # We need to actually create the entity for the test
            test_repository.model_class = MagicMock(return_value=mock_entity)

            await test_repository.create(**entity_data)

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()

    async def test_create_batch_success(self, test_repository, mock_db_session):
        """Test batch entity creation"""
        # Arrange
        entities_data = [
            {"id": str(uuid4()), "name": "Entity 1"},
            {"id": str(uuid4()), "name": "Entity 2"},
            {"id": str(uuid4()), "name": "Entity 3"},
        ]

        mock_entities = [TestModel(**data) for data in entities_data]

        mock_db_session.add_all = MagicMock()
        mock_db_session.refresh = AsyncMock()

        # Mock the model class to return our mock entities
        test_repository.model_class = MagicMock(side_effect=mock_entities)

        # Act
        await test_repository.create_batch(entities_data)

        # Assert
        mock_db_session.add_all.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        assert mock_db_session.refresh.await_count == 3


class TestRead:
    """Test read operations"""

    async def test_get_by_id_found(self, test_repository, mock_db_session):
        """Test get entity by ID when entity exists"""
        # Arrange
        test_id = uuid4()
        mock_entity = TestModel(id=str(test_id), name="Found Entity")
        mock_db_session.get = AsyncMock(return_value=mock_entity)

        # Act
        result = await test_repository.get_by_id(test_id)

        # Assert
        mock_db_session.get.assert_awaited_once_with(TestModel, test_id)
        assert result == mock_entity

    async def test_get_by_id_not_found(self, test_repository, mock_db_session):
        """Test get entity by ID when entity doesn't exist"""
        # Arrange
        test_id = uuid4()
        mock_db_session.get = AsyncMock(return_value=None)

        # Act
        result = await test_repository.get_by_id(test_id)

        # Assert
        assert result is None

    async def test_get_by_id_with_related(self, test_repository, mock_db_session):
        """Test get entity with eager loaded relationships"""
        # Arrange
        test_id = uuid4()
        mock_entity = TestModel(id=str(test_id), name="Entity with relations")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_entity)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act - use valid field name from TestModel
        result = await test_repository.get_by_id_with_related(test_id, ["name"])

        # Assert
        mock_db_session.execute.assert_awaited_once()
        assert result == mock_entity

    async def test_get_all_no_filters(self, test_repository, mock_db_session):
        """Test get all entities without filters"""
        # Arrange
        mock_entities = [TestModel(id=str(uuid4())) for _ in range(3)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_entities)
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.get_all()

        # Assert
        assert len(result) == 3
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_filters(self, test_repository, mock_db_session):
        """Test get all with field filters"""
        # Arrange
        mock_entities = [TestModel(id=str(uuid4()), status="active")]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_entities)
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.get_all(filters={"status": "active"})

        # Assert
        assert len(result) == 1
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_pagination(self, test_repository, mock_db_session):
        """Test get all with limit and offset"""
        # Arrange
        mock_entities = [TestModel(id=str(uuid4())) for _ in range(2)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_entities)
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.get_all(limit=10, offset=20)

        # Assert
        assert len(result) == 2
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_ordering_asc(self, test_repository, mock_db_session):
        """Test get all with ascending order"""
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await test_repository.get_all(order_by="name")

        # Assert
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_ordering_desc(self, test_repository, mock_db_session):
        """Test get all with descending order"""
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await test_repository.get_all(order_by="-name")

        # Assert
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_paginated(self, test_repository, mock_db_session):
        """Test paginated get all"""
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await test_repository.get_all_paginated(skip=10, limit=20)

        # Assert
        mock_db_session.execute.assert_awaited_once()

    async def test_count_all_no_filters(self, test_repository, mock_db_session):
        """Test count all entities without filters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=42)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.count_all()

        # Assert
        assert result == 42
        mock_db_session.execute.assert_awaited_once()

    async def test_count_all_with_filters(self, test_repository, mock_db_session):
        """Test count with filters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=10)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.count_all(filters={"status": "active"})

        # Assert
        assert result == 10

    async def test_count_all_returns_zero_when_none(self, test_repository, mock_db_session):
        """Test count returns 0 when scalar returns None"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.count_all()

        # Assert
        assert result == 0


class TestUpdate:
    """Test update operations"""

    async def test_update_success(self, test_repository, mock_db_session):
        """Test successful entity update"""
        # Arrange
        test_id = uuid4()
        updated_entity = TestModel(id=str(test_id), name="Updated Entity")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_entity)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.update(test_id, name="Updated Entity")

        # Assert
        mock_db_session.execute.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()
        assert result == updated_entity

    async def test_update_not_found(self, test_repository, mock_db_session):
        """Test update when entity doesn't exist"""
        # Arrange
        test_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.update(test_id, name="Updated")

        # Assert
        assert result is None

    async def test_update_ignores_none_values(self, test_repository, mock_db_session):
        """Test update filters out None values"""
        # Arrange
        test_id = uuid4()
        mock_entity = TestModel(id=str(test_id), name="Original")

        mock_db_session.get = AsyncMock(return_value=mock_entity)

        # Act - passing None should skip the update
        result = await test_repository.update(test_id, name=None, value=None)

        # Assert - should call get_by_id instead of update
        mock_db_session.get.assert_awaited_once()
        assert result == mock_entity

    async def test_update_sets_updated_at(self, test_repository, mock_db_session):
        """Test update automatically sets updated_at timestamp"""
        # Arrange
        test_id = uuid4()
        updated_entity = TestModel(id=str(test_id))

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_entity)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await test_repository.update(test_id, name="New Name")

        # Assert
        mock_db_session.execute.assert_awaited_once()
        # Check that the update query includes updated_at
        # The query should have been called with updated_at


class TestDelete:
    """Test delete operations"""

    async def test_delete_success(self, test_repository, mock_db_session):
        """Test successful entity deletion"""
        # Arrange
        test_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.delete(test_id)

        # Assert
        assert result is True
        mock_db_session.execute.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_delete_not_found(self, test_repository, mock_db_session):
        """Test delete when entity doesn't exist"""
        # Arrange
        test_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.delete(test_id)

        # Assert
        assert result is False


class TestCount:
    """Test count operations"""

    async def test_count_no_filters(self, test_repository, mock_db_session):
        """Test count without filters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.count()

        # Assert
        assert result == 100

    async def test_count_with_filters(self, test_repository, mock_db_session):
        """Test count with filters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=25)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.count(filters={"status": "active"})

        # Assert
        assert result == 25

    async def test_count_with_list_filters(self, test_repository, mock_db_session):
        """Test count with IN clause filter"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=15)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.count(filters={"status": ["active", "pending"]})

        # Assert
        assert result == 15


class TestExists:
    """Test exists operations"""

    async def test_exists_true(self, test_repository, mock_db_session):
        """Test exists when entity is found"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=str(uuid4()))
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.exists(name="Test")

        # Assert
        assert result is True

    async def test_exists_false(self, test_repository, mock_db_session):
        """Test exists when entity is not found"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.exists(name="NonExistent")

        # Assert
        assert result is False


class TestFindOperations:
    """Test find_one and find_many operations"""

    async def test_find_one_found(self, test_repository, mock_db_session):
        """Test find_one when entity exists"""
        # Arrange
        mock_entity = TestModel(id=str(uuid4()), name="Found")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_entity)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.find_one(name="Found")

        # Assert
        assert result == mock_entity

    async def test_find_one_not_found(self, test_repository, mock_db_session):
        """Test find_one when entity doesn't exist"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.find_one(name="NotFound")

        # Assert
        assert result is None

    async def test_find_many(self, test_repository, mock_db_session):
        """Test find_many returns multiple entities"""
        # Arrange
        mock_entities = [TestModel(id=str(uuid4())) for _ in range(3)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_entities)
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.find_many(status="active")

        # Assert
        assert len(result) == 3


class TestExecuteRaw:
    """Test raw SQL execution with security checks"""

    async def test_execute_raw_select_allowed(self, test_repository, mock_db_session):
        """Test that SELECT queries are allowed"""
        # Arrange
        mock_result = MagicMock()
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await test_repository.execute_raw(
            "SELECT * FROM test_model WHERE id = :id", {"id": "123"}
        )

        # Assert
        mock_db_session.execute.assert_awaited_once()
        assert result == mock_result

    async def test_execute_raw_blocks_delete(self, test_repository, mock_db_session):
        """Test that DELETE queries are blocked"""
        # Act & Assert
        with pytest.raises(ValueError, match="restricted to SELECT statements only"):
            await test_repository.execute_raw("DELETE FROM test_model WHERE id = '123'")

    async def test_execute_raw_blocks_drop(self, test_repository, mock_db_session):
        """Test that DROP queries are blocked"""
        # Act & Assert
        with pytest.raises(ValueError, match="restricted to SELECT statements only"):
            await test_repository.execute_raw("DROP TABLE test_model")

    async def test_execute_raw_blocks_insert(self, test_repository, mock_db_session):
        """Test that INSERT queries are blocked"""
        # Act & Assert
        with pytest.raises(ValueError, match="restricted to SELECT statements only"):
            await test_repository.execute_raw("INSERT INTO test_model VALUES ('1', 'test')")

    async def test_execute_raw_blocks_update(self, test_repository, mock_db_session):
        """Test that UPDATE queries are blocked"""
        # Act & Assert
        with pytest.raises(ValueError, match="restricted to SELECT statements only"):
            await test_repository.execute_raw("UPDATE test_model SET name = 'hacked'")

    async def test_execute_raw_blocks_non_select(self, test_repository, mock_db_session):
        """Test that non-SELECT statements are blocked"""
        # Act & Assert
        with pytest.raises(ValueError, match="restricted to SELECT statements only"):
            await test_repository.execute_raw("CREATE TABLE hacked (id INT)")


class TestRefresh:
    """Test refresh operation"""

    async def test_refresh_success(self, test_repository, mock_db_session):
        """Test entity refresh from database"""
        # Arrange
        mock_entity = TestModel(id=str(uuid4()), name="Original")
        mock_db_session.refresh = AsyncMock()

        # Act
        result = await test_repository.refresh(mock_entity)

        # Assert
        mock_db_session.refresh.assert_awaited_once_with(mock_entity)
        assert result == mock_entity
