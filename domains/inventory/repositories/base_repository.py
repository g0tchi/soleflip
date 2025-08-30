"""
Base Repository Pattern
Generic repository with common CRUD operations
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic base repository with common operations"""

    def __init__(self, model_class: Type[T], db_session: AsyncSession):
        self.model_class = model_class
        self.db = db_session

    async def create(self, **kwargs) -> T:
        """Create a new entity"""
        entity = self.model_class(**kwargs)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID"""
        return await self.db.get(self.model_class, entity_id)

    async def get_by_id_with_related(self, entity_id: UUID, related: List[str]) -> Optional[T]:
        """Get entity by ID with related models eager loaded"""
        query = select(self.model_class).where(self.model_class.id == entity_id)
        for rel in related:
            query = query.options(selectinload(getattr(self.model_class, rel)))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self, limit: Optional[int] = None, offset: int = 0, order_by: Optional[str] = None
    ) -> List[T]:
        """Get all entities with optional pagination and ordering"""
        query = select(self.model_class)

        if order_by:
            if hasattr(self.model_class, order_by):
                query = query.order_by(getattr(self.model_class, order_by))

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]:
        """Update entity by ID"""
        query = (
            update(self.model_class)
            .where(self.model_class.id == entity_id)
            .values(**kwargs)
            .returning(self.model_class)
        )

        result = await self.db.execute(query)
        updated_entity = result.scalar_one_or_none()

        if updated_entity:
            await self.db.commit()
            await self.db.refresh(updated_entity)

        return updated_entity

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID"""
        query = delete(self.model_class).where(self.model_class.id == entity_id)
        result = await self.db.execute(query)

        if result.rowcount > 0:
            await self.db.commit()
            return True

        return False

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists"""
        query = select(func.count(self.model_class.id)).where(self.model_class.id == entity_id)
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0

    async def count(self) -> int:
        """Get total count of entities"""
        query = select(func.count(self.model_class.id))
        result = await self.db.execute(query)
        return result.scalar()

    async def find_by_field(self, field_name: str, value: Any) -> List[T]:
        """Find entities by field value"""
        if not hasattr(self.model_class, field_name):
            raise ValueError(f"Model {self.model_class.__name__} has no field '{field_name}'")

        field = getattr(self.model_class, field_name)
        query = select(self.model_class).where(field == value)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def find_one_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Find single entity by field value"""
        entities = await self.find_by_field(field_name, value)
        return entities[0] if entities else None

    async def find_one_or_create(self, filter_criteria: Dict[str, Any], **kwargs) -> T:
        """Find one entity or create it if it doesn't exist."""
        query = select(self.model_class).filter_by(**filter_criteria)
        result = await self.db.execute(query)
        instance = result.scalar_one_or_none()

        if instance:
            return instance
        else:
            create_data = {**filter_criteria, **kwargs}
            return await self.create(**create_data)

    async def bulk_create(self, entities_data: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities in bulk"""
        entities = [self.model_class(**data) for data in entities_data]
        self.db.add_all(entities)
        await self.db.commit()

        # Refresh all entities to get IDs
        for entity in entities:
            await self.db.refresh(entity)

        return entities

    async def bulk_update(self, updates: Dict[UUID, Dict[str, Any]]) -> int:
        """Update multiple entities in bulk"""
        updated_count = 0

        for entity_id, update_data in updates.items():
            result = await self.db.execute(
                update(self.model_class)
                .where(self.model_class.id == entity_id)
                .values(**update_data)
            )
            updated_count += result.rowcount

        await self.db.commit()
        return updated_count

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
        query = select(func.count(self.model_class.id))

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if hasattr(self.model_class, field):
                        query = query.where(getattr(self.model_class, field) == value)

        result = await self.db.execute(query)
        return result.scalar() or 0
