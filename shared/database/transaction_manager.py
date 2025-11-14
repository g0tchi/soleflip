"""
Database Transaction Manager
Safe transaction handling for complex operations
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TransactionManager:
    """
    Utility class for managing database transactions safely
    Provides context managers for automatic rollback on errors
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @asynccontextmanager
    async def transaction(
        self, rollback_on_error: bool = True
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for safe database transactions

        Args:
            rollback_on_error: Whether to automatically rollback on exceptions

        Yields:
            AsyncSession: The database session

        Usage:
            async with TransactionManager(db).transaction() as session:
                # Database operations here
                session.add(model)
                # Automatic commit on success, rollback on error
        """
        try:
            # Begin transaction (if not already in one)
            if not self.db.in_transaction():
                await self.db.begin()

            yield self.db

            # Commit if we reach here without exceptions
            if self.db.in_transaction():
                await self.db.commit()
                logger.debug("Transaction committed successfully")

        except Exception as e:
            # Rollback on any exception
            if rollback_on_error and self.db.in_transaction():
                await self.db.rollback()
                logger.error(f"Transaction rolled back due to error: {str(e)}")
            raise

    @asynccontextmanager
    async def savepoint(self, name: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for savepoints (nested transactions)

        Args:
            name: Optional savepoint name

        Yields:
            AsyncSession: The database session

        Usage:
            async with TransactionManager(db).savepoint("my_savepoint") as session:
                # Nested operation that might fail
                session.add(risky_model)
                # Will rollback to savepoint on error, not entire transaction
        """
        savepoint_name = name or f"sp_{id(self)}"

        try:
            # Create savepoint
            savepoint = await self.db.begin_nested()
            logger.debug(f"Created savepoint: {savepoint_name}")

            yield self.db

            # Commit savepoint if we reach here
            await savepoint.commit()
            logger.debug(f"Savepoint committed: {savepoint_name}")

        except Exception as e:
            # Rollback to savepoint
            await savepoint.rollback()
            logger.error(f"Rolled back to savepoint {savepoint_name}: {str(e)}")
            raise

    async def execute_in_transaction(self, operation, *args, **kwargs) -> Any:
        """
        Execute a function within a transaction

        Args:
            operation: Async function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Usage:
            result = await transaction_manager.execute_in_transaction(
                my_database_operation,
                param1=value1,
                param2=value2
            )
        """
        async with self.transaction():
            return await operation(self.db, *args, **kwargs)

    async def batch_operation(
        self, operations: list, continue_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Execute multiple operations in a single transaction

        Args:
            operations: List of (operation_func, args, kwargs) tuples
            continue_on_error: Whether to continue if one operation fails

        Returns:
            Dict with results and error info

        Usage:
            operations = [
                (create_listing, (listing_data,), {}),
                (update_inventory, (product_id,), {'quantity': 10}),
            ]
            results = await transaction_manager.batch_operation(operations)
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(operations),
            "success_count": 0,
            "error_count": 0,
        }

        if continue_on_error:
            # Execute each operation with its own savepoint
            async with self.transaction():
                for i, (operation, args, kwargs) in enumerate(operations):
                    try:
                        async with self.savepoint(f"batch_op_{i}"):
                            result = await operation(self.db, *args, **kwargs)
                            results["successful"].append({"index": i, "result": result})
                            results["success_count"] += 1

                    except Exception as e:
                        logger.error(f"Batch operation {i} failed: {str(e)}")
                        results["failed"].append(
                            {
                                "index": i,
                                "error": str(e),
                                "operation": (
                                    operation.__name__
                                    if hasattr(operation, "__name__")
                                    else str(operation)
                                ),
                            }
                        )
                        results["error_count"] += 1
        else:
            # Execute all operations in single transaction (all or nothing)
            try:
                async with self.transaction():
                    for i, (operation, args, kwargs) in enumerate(operations):
                        result = await operation(self.db, *args, **kwargs)
                        results["successful"].append({"index": i, "result": result})
                        results["success_count"] += 1

            except Exception as e:
                logger.error(
                    f"Batch operation failed at index {len(results['successful'])}: {str(e)}"
                )
                results["failed"].append(
                    {
                        "index": len(results["successful"]),
                        "error": str(e),
                        "operation": "batch_transaction",
                    }
                )
                results["error_count"] = 1
                # All successful operations are automatically rolled back

        return results


class TransactionMixin:
    """
    Mixin class to add transaction management to service classes
    """

    def __init__(self, db_session: AsyncSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db_session
        self._transaction_manager = TransactionManager(db_session)

    @property
    def transaction_manager(self) -> TransactionManager:
        """Get the transaction manager for this service"""
        return self._transaction_manager

    async def with_transaction(self, operation, *args, **kwargs):
        """Execute operation within a transaction"""
        return await self._transaction_manager.execute_in_transaction(operation, *args, **kwargs)

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions"""
        async with self._transaction_manager.transaction() as session:
            yield session

    @asynccontextmanager
    async def savepoint(self, name: Optional[str] = None):
        """Context manager for savepoints"""
        async with self._transaction_manager.savepoint(name) as session:
            yield session


# Decorator for automatic transaction handling
def transactional(rollback_on_error: bool = True):
    """
    Decorator to automatically wrap a method in a transaction

    Usage:
        class MyService(TransactionMixin):
            @transactional()
            async def create_complex_entity(self, data):
                # This method will run in a transaction
                # Automatic rollback on any exception
                pass
    """

    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            if not hasattr(self, "_transaction_manager"):
                raise AttributeError(
                    "Class must inherit from TransactionMixin to use @transactional decorator"
                )

            async with self._transaction_manager.transaction(rollback_on_error=rollback_on_error):
                return await func(self, *args, **kwargs)

        return wrapper

    return decorator
