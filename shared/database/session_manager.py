"""
Advanced Database Session Management
Production-ready session lifecycle management with proper cleanup and monitoring
"""
from typing import AsyncGenerator, Optional, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
import structlog
import asyncio
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class SessionStats:
    """Track session statistics for monitoring"""
    
    def __init__(self):
        self.active_sessions = 0
        self.total_sessions = 0
        self.failed_sessions = 0
        self.average_duration = 0.0
        self._session_start_times: Dict[id, datetime] = {}
    
    def session_started(self, session_id: int):
        self.active_sessions += 1
        self.total_sessions += 1
        self._session_start_times[session_id] = datetime.utcnow()
    
    def session_ended(self, session_id: int, failed: bool = False):
        self.active_sessions -= 1
        if failed:
            self.failed_sessions += 1
        
        # Calculate session duration
        if session_id in self._session_start_times:
            duration = (datetime.utcnow() - self._session_start_times[session_id]).total_seconds()
            # Simple moving average
            self.average_duration = (self.average_duration * 0.9) + (duration * 0.1)
            del self._session_start_times[session_id]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": self.active_sessions,
            "total_sessions": self.total_sessions,
            "failed_sessions": self.failed_sessions,
            "success_rate": ((self.total_sessions - self.failed_sessions) / max(self.total_sessions, 1)) * 100,
            "average_duration_seconds": round(self.average_duration, 2)
        }


class SessionManager:
    """Advanced session manager with monitoring and cleanup"""
    
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.stats = SessionStats()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background task to cleanup stale sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error in session cleanup loop", error=str(e))
    
    async def _cleanup_stale_sessions(self):
        """Clean up sessions that have been running too long"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        stale_sessions = [
            session_id for session_id, start_time in self.stats._session_start_times.items()
            if start_time < cutoff_time
        ]
        
        if stale_sessions:
            logger.warning(
                "Found stale sessions",
                count=len(stale_sessions),
                session_ids=stale_sessions
            )
            # Mark as ended (they're likely already closed by the database)
            for session_id in stale_sessions:
                self.stats.session_ended(session_id, failed=True)
    
    @asynccontextmanager
    async def get_session(
        self,
        autocommit: bool = True,
        read_only: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        """Get a managed database session with proper lifecycle"""
        session = self.session_factory()
        session_id = id(session)
        
        self.stats.session_started(session_id)
        session_failed = False
        
        try:
            # Configure session
            if read_only:
                # Set session to read-only mode (PostgreSQL specific)
                try:
                    await session.execute("SET TRANSACTION READ ONLY")
                except Exception:
                    pass  # Ignore if not supported (e.g., SQLite)
            
            logger.debug(
                "Database session started",
                session_id=session_id,
                autocommit=autocommit,
                read_only=read_only
            )
            
            yield session
            
            # Auto-commit if requested and no explicit rollback
            if autocommit and session.in_transaction():
                await session.commit()
                logger.debug("Session auto-committed", session_id=session_id)
            
        except Exception as e:
            session_failed = True
            # Rollback on any error
            try:
                if session.in_transaction():
                    await session.rollback()
                    logger.debug("Session rolled back due to error", session_id=session_id)
            except Exception as rollback_error:
                logger.error(
                    "Failed to rollback session",
                    session_id=session_id,
                    rollback_error=str(rollback_error)
                )
            
            # Log the original error
            logger.error(
                "Database session error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            # Always close the session
            try:
                await session.close()
                logger.debug("Database session closed", session_id=session_id)
            except Exception as close_error:
                logger.error(
                    "Error closing session",
                    session_id=session_id,
                    error=str(close_error)
                )
            
            self.stats.session_ended(session_id, failed=session_failed)
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a session with explicit transaction control"""
        async with self.get_session(autocommit=False) as session:
            async with session.begin():
                yield session
    
    async def execute_with_retry(
        self,
        operation,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **session_kwargs
    ):
        """Execute an operation with automatic retry logic"""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                async with self.get_session(**session_kwargs) as session:
                    return await operation(session)
            except SQLAlchemyError as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        "Database operation failed, retrying",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e)
                    )
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(
                        "Database operation failed after all retries",
                        attempts=max_retries + 1,
                        error=str(e)
                    )
        
        raise last_error
    
    async def bulk_insert(
        self,
        model_class,
        data: list,
        batch_size: int = 1000
    ):
        """Efficiently insert large amounts of data"""
        async with self.get_session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                session.add_all([model_class(**item) for item in batch])
                await session.flush()
                
                logger.debug(
                    "Bulk insert batch processed",
                    model=model_class.__name__,
                    batch_number=i // batch_size + 1,
                    batch_size=len(batch)
                )
            
            await session.commit()
            logger.info(
                "Bulk insert completed",
                model=model_class.__name__,
                total_records=len(data)
            )
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        return self.stats.get_stats()
    
    async def shutdown(self):
        """Cleanup resources on shutdown"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class QueryOptimizer:
    """Query optimization utilities"""
    
    @staticmethod
    def with_eager_loading(query, *relationships):
        """Add eager loading to prevent N+1 queries"""
        for rel in relationships:
            query = query.options(selectinload(rel))
        return query
    
    @staticmethod
    def paginate_query(query, page: int, page_size: int = 50):
        """Add pagination to a query"""
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size)
    
    @staticmethod
    def add_filters(query, filters: Dict[str, Any]):
        """Dynamically add filters to a query"""
        for field, value in filters.items():
            if value is not None:
                if isinstance(value, str) and '%' in value:
                    # Use LIKE for string patterns
                    query = query.filter(getattr(query.column_descriptions[0]['type'], field).like(value))
                else:
                    # Exact match for other values
                    query = query.filter(getattr(query.column_descriptions[0]['type'], field) == value)
        return query


# Decorators for common session patterns
def with_db_session(autocommit: bool = True, read_only: bool = False):
    """Decorator to inject a database session"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from shared.database.connection import db_manager
            session_manager = SessionManager(db_manager.session_factory)
            
            async with session_manager.get_session(autocommit=autocommit, read_only=read_only) as session:
                return await func(*args, session=session, **kwargs)
        
        return wrapper
    return decorator


def with_transaction():
    """Decorator to wrap function in a database transaction"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from shared.database.connection import db_manager
            session_manager = SessionManager(db_manager.session_factory)
            
            async with session_manager.transaction() as session:
                return await func(*args, session=session, **kwargs)
        
        return wrapper
    return decorator