"""
Repository for Integration Domain Models
Provides database access logic for import-related entities.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from domains.inventory.repositories.base_repository import BaseRepository
from shared.database.models import ImportBatch

class ImportRepository(BaseRepository[ImportBatch]):
    """
    Repository for accessing and manipulating ImportBatch entities.
    """
    def __init__(self, db_session: AsyncSession):
        """
        Initializes the repository with the database session.

        Args:
            db_session: The SQLAlchemy async session.
        """
        super().__init__(ImportBatch, db_session)

    async def get_batch_with_details(self, batch_id: UUID) -> Optional[ImportBatch]:
        """
        Retrieves an import batch by its ID, eagerly loading its associated records.

        This is useful for getting a complete picture of an import job, including
        all individual records and their statuses.

        Args:
            batch_id: The UUID of the import batch to retrieve.

        Returns:
            The ImportBatch object with related import_records loaded, or None if not found.
        """
        query = (
            select(self.model_class)
            .where(self.model_class.id == batch_id)
            .options(selectinload(self.model_class.import_records))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
