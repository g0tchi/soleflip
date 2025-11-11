"""
Database Performance Optimizations
Advanced database performance improvements for large-scale operations.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Type, TypeVar

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class DatabaseOptimizer:
    """Database performance optimization utilities"""

    def __init__(self):
        self._query_cache = {}
        self._prepared_statements = {}

    async def optimize_bulk_insert(
        self,
        session: AsyncSession,
        model_class: Type[T],
        data: List[Dict[str, Any]],
        batch_size: int = 1000,
    ) -> List[T]:
        """
        Optimized bulk insert with batching and RETURNING clause.
        Much faster than individual inserts for large datasets.
        """

        if not data:
            return []

        logger.info(
            "Starting optimized bulk insert",
            model=model_class.__name__,
            total_records=len(data),
            batch_size=batch_size,
        )

        all_created = []

        # Process in batches to avoid memory issues
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]

            try:
                # Use bulk_insert_mappings for better performance
                result = await session.execute(
                    model_class.__table__.insert().returning(model_class), batch
                )

                created_objects = result.scalars().all()
                all_created.extend(created_objects)

                # Commit each batch to avoid long-running transactions
                await session.commit()

                logger.debug(
                    "Bulk insert batch completed",
                    batch_size=len(batch),
                    batch_index=i // batch_size + 1,
                )

            except Exception as e:
                await session.rollback()
                logger.error(
                    "Bulk insert batch failed", batch_index=i // batch_size + 1, error=str(e)
                )
                raise

        logger.info(
            "Optimized bulk insert completed",
            model=model_class.__name__,
            total_created=len(all_created),
        )

        return all_created

    async def optimize_bulk_update(
        self,
        session: AsyncSession,
        model_class: Type[T],
        updates: List[Dict[str, Any]],
        key_field: str = "id",
        batch_size: int = 1000,
    ) -> int:
        """
        Optimized bulk update using CASE statements.
        Much faster than individual updates.
        """

        if not updates:
            return 0

        logger.info(
            "Starting optimized bulk update",
            model=model_class.__name__,
            total_records=len(updates),
            batch_size=batch_size,
        )

        total_updated = 0

        # Process in batches
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]

            try:
                # Build CASE statements for each field
                update_values = {}
                key_values = [item[key_field] for item in batch]

                # Get all fields to update (excluding the key field)
                fields_to_update = set()
                for item in batch:
                    fields_to_update.update(k for k in item.keys() if k != key_field)

                for field in fields_to_update:
                    # Build CASE statement for this field
                    case_conditions = []
                    for item in batch:
                        if field in item:
                            case_conditions.append(
                                f"WHEN {key_field} = :key_{item[key_field]} THEN :val_{field}_{item[key_field]}"
                            )

                    if case_conditions:
                        case_sql = f"CASE {' '.join(case_conditions)} ELSE {field} END"
                        update_values[field] = text(case_sql)

                # Prepare parameters
                params = {}
                for item in batch:
                    params[f"key_{item[key_field]}"] = item[key_field]
                    for field in fields_to_update:
                        if field in item:
                            params[f"val_{field}_{item[key_field]}"] = item[field]

                # Execute bulk update
                if update_values:
                    stmt = (
                        model_class.__table__.update()
                        .where(getattr(model_class, key_field).in_(key_values))
                        .values(**update_values)
                    )

                    result = await session.execute(stmt, params)
                    batch_updated = result.rowcount
                    total_updated += batch_updated

                    await session.commit()

                    logger.debug(
                        "Bulk update batch completed",
                        batch_updated=batch_updated,
                        batch_index=i // batch_size + 1,
                    )

            except Exception as e:
                await session.rollback()
                logger.error(
                    "Bulk update batch failed", batch_index=i // batch_size + 1, error=str(e)
                )
                raise

        logger.info(
            "Optimized bulk update completed",
            model=model_class.__name__,
            total_updated=total_updated,
        )

        return total_updated

    async def optimize_bulk_upsert(
        self,
        session: AsyncSession,
        model_class: Type[T],
        data: List[Dict[str, Any]],
        conflict_columns: List[str],
        update_columns: List[str],
        batch_size: int = 1000,
    ) -> Dict[str, int]:
        """
        Optimized bulk upsert (INSERT ... ON CONFLICT).
        PostgreSQL specific optimization.
        """

        if not data:
            return {"inserted": 0, "updated": 0}

        logger.info(
            "Starting optimized bulk upsert",
            model=model_class.__name__,
            total_records=len(data),
            conflict_columns=conflict_columns,
            batch_size=batch_size,
        )

        total_inserted = 0
        total_updated = 0

        # Check if we're using PostgreSQL
        from shared.database.utils import IS_POSTGRES

        if not IS_POSTGRES:
            # Fallback to separate insert/update operations for SQLite
            return await self._fallback_upsert(session, model_class, data, conflict_columns[0])

        # Process in batches
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]

            try:
                # Build PostgreSQL UPSERT query
                table = model_class.__table__

                # Build conflict clause
                conflict_clause = f"({', '.join(conflict_columns)})"

                # Build update clause
                update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])

                # Create the UPSERT statement
                upsert_sql = f"""
                    INSERT INTO {table.name} ({', '.join(table.columns.keys())})
                    VALUES {', '.join(['(' + ', '.join([f':{col}_{j}' for col in table.columns.keys()]) + ')' for j in range(len(batch))])}
                    ON CONFLICT {conflict_clause}
                    DO UPDATE SET {update_clause}
                """

                # Prepare parameters
                params = {}
                for j, item in enumerate(batch):
                    for col in table.columns.keys():
                        params[f"{col}_{j}"] = item.get(col)

                # Execute upsert
                await session.execute(text(upsert_sql), params)
                await session.commit()

                # For now, assume all were successful (could track actual counts with more complex query)
                total_inserted += len(batch)  # Simplified

                logger.debug(
                    "Bulk upsert batch completed",
                    batch_size=len(batch),
                    batch_index=i // batch_size + 1,
                )

            except Exception as e:
                await session.rollback()
                logger.error(
                    "Bulk upsert batch failed", batch_index=i // batch_size + 1, error=str(e)
                )
                raise

        logger.info(
            "Optimized bulk upsert completed", model=model_class.__name__, total_processed=len(data)
        )

        return {"inserted": total_inserted, "updated": total_updated}

    async def _fallback_upsert(
        self,
        session: AsyncSession,
        model_class: Type[T],
        data: List[Dict[str, Any]],
        key_field: str,
    ) -> Dict[str, int]:
        """Fallback upsert for non-PostgreSQL databases"""

        inserted = 0
        updated = 0

        # Get existing records
        key_values = [item[key_field] for item in data]
        existing_query = select(model_class).where(getattr(model_class, key_field).in_(key_values))
        result = await session.execute(existing_query)
        existing_records = {getattr(r, key_field): r for r in result.scalars().all()}

        # Separate inserts and updates
        inserts = []
        updates = []

        for item in data:
            key_value = item[key_field]
            if key_value in existing_records:
                updates.append(item)
            else:
                inserts.append(item)

        # Perform bulk operations
        if inserts:
            await self.optimize_bulk_insert(session, model_class, inserts)
            inserted = len(inserts)

        if updates:
            await self.optimize_bulk_update(session, model_class, updates, key_field)
            updated = len(updates)

        return {"inserted": inserted, "updated": updated}

    def optimize_query_with_indexes(self, query: Select, model_class: Type[T]) -> Select:
        """Optimize query by suggesting appropriate eager loading and hints"""

        # Add query hints for better performance
        # This is database-specific and would need more sophisticated logic

        return query

    async def create_performance_indexes(self, session: AsyncSession):
        """Create performance-critical indexes"""

        logger.info("Creating performance indexes")

        try:
            # Import batch indexes
            await session.execute(
                text("CREATE INDEX IF NOT EXISTS idx_import_batch_status ON import_batches(status)")
            )
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_import_batch_source_created ON import_batches(source_type, created_at)"
                )
            )

            # Product indexes
            await session.execute(
                text("CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)")
            )
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_brand_category ON products(brand_id, category_id)"
                )
            )
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_active_created ON products(is_active, created_at)"
                )
            )

            # Inventory indexes
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_inventory_product_id ON inventory_items(product_id)"
                )
            )
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_inventory_quantity ON inventory_items(quantity_available)"
                )
            )

            # Event store indexes
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_event_store_aggregate ON event_store(aggregate_id)"
                )
            )
            await session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_event_store_type_timestamp ON event_store(event_type, timestamp)"
                )
            )

            await session.commit()
            logger.info("Performance indexes created successfully")

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create performance indexes: {e}")
            raise


class QueryOptimizer:
    """Advanced query optimization utilities"""

    @staticmethod
    def optimize_eager_loading(query: Select, relationships: List[str]) -> Select:
        """Add optimal eager loading for relationships"""

        for relationship in relationships:
            # Use selectinload for collections, joinedload for single relationships
            # This is a simplified heuristic - in practice, you'd analyze the relationship
            if relationship.endswith("s"):  # Assume plural = collection
                query = query.options(selectinload(relationship))
            else:
                query = query.options(joinedload(relationship))

        return query

    @staticmethod
    def add_query_hints(query: Select, hints: List[str]) -> Select:
        """Add database-specific query hints"""

        # This would be database-specific
        # PostgreSQL example: query.execution_options(postgresql_hint="...")

        return query

    @staticmethod
    def optimize_pagination(
        query: Select, page: int, per_page: int, order_by: Optional[str] = None
    ) -> Select:
        """Optimize pagination queries"""

        # Add stable ordering for consistent pagination
        if order_by:
            # Add primary key as tie-breaker for stable sorting
            query = query.order_by(order_by, "id")
        else:
            query = query.order_by("id")

        # Use offset/limit
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        return query


@asynccontextmanager
async def optimized_db_session():
    """Context manager for optimized database sessions"""

    async with get_db_session() as session:
        # Set session-level optimizations
        await session.execute(text("SET work_mem = '256MB'"))  # PostgreSQL specific
        await session.execute(text("SET random_page_cost = 1.1"))  # SSD optimization

        try:
            yield session
        finally:
            # Reset to defaults
            await session.execute(text("RESET work_mem"))
            await session.execute(text("RESET random_page_cost"))


# Global optimizer instance
_db_optimizer: Optional[DatabaseOptimizer] = None


def get_database_optimizer() -> DatabaseOptimizer:
    """Get the global database optimizer instance"""
    global _db_optimizer
    if _db_optimizer is None:
        _db_optimizer = DatabaseOptimizer()
    return _db_optimizer
