"""
Centralized Base Repository Pattern
Standardized repository interface for all domain repositories.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic base repository with comprehensive CRUD operations.
    All domain repositories should inherit from this class.
    """

    def __init__(self, model_class: Type[T], db_session: AsyncSession):
        self.model_class = model_class
        self.db = db_session
        self._logger = logger.bind(repository=self.__class__.__name__, model=model_class.__name__)

    async def create(self, **kwargs) -> T:
        """Create a new entity"""
        self._logger.debug("Creating new entity", fields=list(kwargs.keys()))

        entity = self.model_class(**kwargs)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)

        self._logger.info("Entity created successfully", entity_id=getattr(entity, "id", None))
        return entity

    async def create_batch(self, entities_data: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities in batch"""
        self._logger.debug("Creating batch of entities", count=len(entities_data))

        entities = [self.model_class(**data) for data in entities_data]
        self.db.add_all(entities)
        await self.db.commit()

        # Refresh all entities to get generated IDs
        for entity in entities:
            await self.db.refresh(entity)

        self._logger.info("Batch created successfully", count=len(entities))
        return entities

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID"""
        self._logger.debug("Fetching entity by ID", entity_id=entity_id)
        return await self.db.get(self.model_class, entity_id)

    async def get_by_id_with_related(self, entity_id: UUID, related: List[str]) -> Optional[T]:
        """Get entity by ID with related models eager loaded"""
        self._logger.debug("Fetching entity with relations", entity_id=entity_id, relations=related)

        query = select(self.model_class).where(self.model_class.id == entity_id)
        for rel in related:
            query = query.options(selectinload(getattr(self.model_class, rel)))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """Get all entities with optional pagination, ordering, and filtering"""
        query = select(self.model_class)

        # Apply filters
        if filters:
            filter_conditions = []
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    if isinstance(value, list):
                        filter_conditions.append(getattr(self.model_class, field).in_(value))
                    else:
                        filter_conditions.append(getattr(self.model_class, field) == value)

            if filter_conditions:
                query = query.where(and_(*filter_conditions))

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                # Descending order
                field_name = order_by[1:]
                if hasattr(self.model_class, field_name):
                    query = query.order_by(getattr(self.model_class, field_name).desc())
            else:
                # Ascending order
                if hasattr(self.model_class, order_by):
                    query = query.order_by(getattr(self.model_class, order_by))

        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all_paginated(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get paginated list of entities with optional filters"""
        query = select(self.model_class)

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if hasattr(self.model_class, field):
                        query = query.where(getattr(self.model_class, field) == value)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_all(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total entities with optional filters"""
        from sqlalchemy import func
        
        query = select(func.count(self.model_class.id))

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if hasattr(self.model_class, field):
                        query = query.where(getattr(self.model_class, field) == value)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]:
        """Update entity by ID"""
        self._logger.debug("Updating entity", entity_id=entity_id, fields=list(kwargs.keys()))

        # Remove None values to avoid overwriting with null
        update_data = {k: v for k, v in kwargs.items() if v is not None}

        if not update_data:
            # No actual updates to perform
            return await self.get_by_id(entity_id)

        # Add updated_at timestamp if model has this field
        if hasattr(self.model_class, "updated_at"):
            update_data["updated_at"] = datetime.now(timezone.utc)

        query = (
            update(self.model_class)
            .where(self.model_class.id == entity_id)
            .values(**update_data)
            .returning(self.model_class)
        )

        result = await self.db.execute(query)
        await self.db.commit()

        updated_entity = result.scalar_one_or_none()
        if updated_entity:
            self._logger.info("Entity updated successfully", entity_id=entity_id)
        else:
            self._logger.warning("Entity not found for update", entity_id=entity_id)

        return updated_entity

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID"""
        self._logger.debug("Deleting entity", entity_id=entity_id)

        query = delete(self.model_class).where(self.model_class.id == entity_id)
        result = await self.db.execute(query)
        await self.db.commit()

        deleted = result.rowcount > 0
        if deleted:
            self._logger.info("Entity deleted successfully", entity_id=entity_id)
        else:
            self._logger.warning("Entity not found for deletion", entity_id=entity_id)

        return deleted

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering"""
        query = select(func.count(self.model_class.id))

        # Apply filters
        if filters:
            filter_conditions = []
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    if isinstance(value, list):
                        filter_conditions.append(getattr(self.model_class, field).in_(value))
                    else:
                        filter_conditions.append(getattr(self.model_class, field) == value)

            if filter_conditions:
                query = query.where(and_(*filter_conditions))

        result = await self.db.execute(query)
        return result.scalar()

    async def exists(self, **filters) -> bool:
        """Check if entity exists with given filters"""
        query = select(self.model_class.id).limit(1)

        filter_conditions = []
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                filter_conditions.append(getattr(self.model_class, field) == value)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        result = await self.db.execute(query)
        return result.scalar() is not None

    async def find_one(self, **filters) -> Optional[T]:
        """Find single entity by filters"""
        query = select(self.model_class)

        filter_conditions = []
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                filter_conditions.append(getattr(self.model_class, field) == value)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_many(self, limit: Optional[int] = None, offset: int = 0, **filters) -> List[T]:
        """Find multiple entities by filters"""
        return await self.get_all(limit=limit, offset=offset, filters=filters)

    async def execute_raw(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL query (use with extreme caution - restricted access)
        SECURITY: Only allows SELECT queries to prevent data modification
        """
        # SECURITY: Restrict to SELECT queries only
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            raise ValueError("Raw queries are restricted to SELECT statements only")
        
        # SECURITY: Block potentially dangerous keywords
        dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE", "EXEC"]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Raw query contains restricted keyword: {keyword}")
        
        self._logger.debug("Executing raw SELECT query", query=query[:100])

        result = await self.db.execute(text(query), params or {})
        return result

    async def refresh(self, entity: T) -> T:
        """Refresh entity from database"""
        await self.db.refresh(entity)
        return entity
