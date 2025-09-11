"""
Async Processing Pipeline for Large-Scale Retailer Imports
Handles high-volume data processing with chunking, queuing, and parallel execution
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Protocol
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from shared.database.models import ImportBatch
from shared.events import publish_event, ImportBatchCreatedEvent, ImportBatchProgressEvent, ImportBatchCompletedEvent, ImportBatchFailedEvent
from shared.exceptions.domain_exceptions import BatchProcessingException, ServiceIntegrationException

logger = structlog.get_logger(__name__)


class ProcessingStage(str, Enum):
    """Processing pipeline stages"""
    QUEUED = "queued"
    PARSING = "parsing" 
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    PERSISTENCE = "persistence"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingPriority(str, Enum):
    """Processing priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProcessingContext:
    """Context object passed through the pipeline stages"""
    batch_id: UUID
    source_type: str
    total_records: int
    chunk_size: int = 1000
    current_chunk: int = 0
    processed_records: int = 0
    failed_records: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def progress_percentage(self) -> float:
        """Calculate processing progress percentage"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100


@dataclass 
class ChunkResult:
    """Result of processing a single chunk"""
    chunk_index: int
    records_processed: int
    records_failed: int
    processing_time_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ProcessingStageProtocol(Protocol):
    """Protocol for processing stage implementations"""
    
    async def process_chunk(
        self, 
        chunk_data: List[Dict[str, Any]], 
        context: ProcessingContext
    ) -> ChunkResult:
        """Process a single chunk of data"""
        ...
    
    async def setup(self, context: ProcessingContext) -> None:
        """Setup stage before processing begins"""
        ...
    
    async def cleanup(self, context: ProcessingContext) -> None:
        """Cleanup after processing is complete"""
        ...


class AsyncProcessingPipeline:
    """
    High-performance async processing pipeline for large-scale imports.
    Supports chunked processing, parallel execution, and error recovery.
    """
    
    def __init__(
        self,
        max_concurrent_chunks: int = 5,
        chunk_size: int = 1000,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        self.max_concurrent_chunks = max_concurrent_chunks
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.stages: Dict[ProcessingStage, ProcessingStageProtocol] = {}
        self.progress_callbacks: List[Callable[[ProcessingContext], None]] = []
        
        # Processing state
        self._active_pipelines: Dict[UUID, ProcessingContext] = {}
        self._processing_semaphore = asyncio.Semaphore(max_concurrent_chunks)
    
    def register_stage(self, stage: ProcessingStage, processor: ProcessingStageProtocol):
        """Register a processing stage"""
        self.stages[stage] = processor
        logger.info(f"Registered processing stage: {stage}")
    
    def add_progress_callback(self, callback: Callable[[ProcessingContext], None]):
        """Add progress monitoring callback"""
        self.progress_callbacks.append(callback)
    
    async def process_large_dataset(
        self,
        batch_id: UUID,
        data_stream: AsyncGenerator[List[Dict[str, Any]], None],
        source_type: str,
        total_records: Optional[int] = None,
        priority: ProcessingPriority = ProcessingPriority.NORMAL
    ) -> ProcessingContext:
        """
        Process large dataset using async pipeline with chunking and parallel processing.
        
        Args:
            batch_id: Unique batch identifier
            data_stream: Async generator yielding chunks of data
            source_type: Type of data source (e.g., 'retailer_catalog')
            total_records: Total number of records (if known)
            priority: Processing priority level
            
        Returns:
            Final processing context with results
        """
        
        # Initialize processing context
        context = ProcessingContext(
            batch_id=batch_id,
            source_type=source_type,
            total_records=total_records or 0,
            chunk_size=self.chunk_size
        )
        
        self._active_pipelines[batch_id] = context
        
        # Publish batch created event
        await publish_event(ImportBatchCreatedEvent(
            aggregate_id=batch_id,
            batch_id=batch_id,
            source_type=source_type,
            filename=context.metadata.get('filename'),
            total_records=total_records
        ))
        
        logger.info(
            "Starting large dataset processing",
            batch_id=str(batch_id),
            source_type=source_type,
            total_records=total_records,
            priority=priority
        )
        
        try:
            # Setup all stages
            for stage, processor in self.stages.items():
                await processor.setup(context)
            
            # Process data in chunks with concurrency control
            chunk_tasks = []
            async for chunk_data in data_stream:
                if not chunk_data:
                    continue
                
                # Update total records if not known initially
                if context.total_records == 0:
                    context.total_records += len(chunk_data)
                
                # Create async task for chunk processing
                task = asyncio.create_task(
                    self._process_chunk_with_retry(chunk_data, context)
                )
                chunk_tasks.append(task)
                
                # Control concurrency - process in batches
                if len(chunk_tasks) >= self.max_concurrent_chunks:
                    # Wait for current batch to complete
                    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
                    await self._handle_chunk_results(chunk_results, context)
                    chunk_tasks.clear()
            
            # Process remaining chunks
            if chunk_tasks:
                chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
                await self._handle_chunk_results(chunk_results, context)
            
            # Cleanup all stages
            for stage, processor in self.stages.items():
                await processor.cleanup(context)
            
            # Update final status
            await self._update_batch_status(context, "completed")
            
            # Publish batch completed event
            processing_time = (datetime.now(timezone.utc) - context.start_time).total_seconds()
            await publish_event(ImportBatchCompletedEvent(
                aggregate_id=batch_id,
                batch_id=batch_id,
                total_processed=context.processed_records,
                total_failed=context.failed_records,
                processing_time_seconds=processing_time,
                success=context.failed_records == 0
            ))
            
            logger.info(
                "Large dataset processing completed",
                batch_id=str(batch_id),
                processed_records=context.processed_records,
                failed_records=context.failed_records,
                progress=context.progress_percentage,
                duration_seconds=processing_time
            )
            
        except Exception as e:
            context.failed_records += context.total_records - context.processed_records
            await self._update_batch_status(context, "failed")
            
            # Publish batch failed event
            await publish_event(ImportBatchFailedEvent(
                aggregate_id=batch_id,
                batch_id=batch_id,
                error_message=str(e),
                error_type=type(e).__name__,
                failed_at_stage="pipeline_execution"
            ))
            
            logger.error(
                "Large dataset processing failed",
                batch_id=str(batch_id),
                error=str(e),
                processed_records=context.processed_records,
                exc_info=True
            )
            
            raise BatchProcessingException(
                f"Pipeline processing failed for batch {batch_id}: {str(e)}",
                details={
                    "batch_id": str(batch_id),
                    "processed_records": context.processed_records,
                    "failed_records": context.failed_records
                }
            ) from e
        
        finally:
            # Cleanup
            self._active_pipelines.pop(batch_id, None)
        
        return context
    
    async def _process_chunk_with_retry(
        self, 
        chunk_data: List[Dict[str, Any]], 
        context: ProcessingContext
    ) -> ChunkResult:
        """Process a single chunk with retry logic"""
        
        async with self._processing_semaphore:  # Control concurrency
            chunk_index = context.current_chunk
            context.current_chunk += 1
            
            for attempt in range(self.max_retries + 1):
                try:
                    start_time = time.time()
                    
                    # Process through all pipeline stages
                    current_data = chunk_data
                    total_processed = 0
                    total_failed = 0
                    all_errors = []
                    
                    for stage in [ProcessingStage.PARSING, ProcessingStage.VALIDATION, 
                                 ProcessingStage.TRANSFORMATION, ProcessingStage.PERSISTENCE]:
                        if stage not in self.stages:
                            continue
                        
                        stage_result = await self.stages[stage].process_chunk(current_data, context)
                        total_processed += stage_result.records_processed
                        total_failed += stage_result.records_failed
                        all_errors.extend(stage_result.errors)
                        
                        # Update progress
                        context.processed_records += stage_result.records_processed
                        context.failed_records += stage_result.records_failed
                        
                        # Publish progress event
                        await publish_event(ImportBatchProgressEvent(
                            aggregate_id=context.batch_id,
                            batch_id=context.batch_id,
                            processed_records=context.processed_records,
                            failed_records=context.failed_records,
                            progress_percentage=context.progress_percentage,
                            current_stage=stage.value
                        ))
                        
                        # Notify progress callbacks
                        for callback in self.progress_callbacks:
                            try:
                                await callback(context) if asyncio.iscoroutinefunction(callback) else callback(context)
                            except Exception as cb_error:
                                logger.warning(f"Progress callback error: {cb_error}")
                    
                    processing_time = (time.time() - start_time) * 1000
                    
                    result = ChunkResult(
                        chunk_index=chunk_index,
                        records_processed=len(chunk_data) - total_failed,
                        records_failed=total_failed,
                        processing_time_ms=processing_time,
                        errors=all_errors
                    )
                    
                    logger.debug(
                        "Chunk processed successfully",
                        batch_id=str(context.batch_id),
                        chunk_index=chunk_index,
                        records=len(chunk_data),
                        processing_time_ms=processing_time,
                        attempt=attempt + 1
                    )
                    
                    return result
                
                except Exception as e:
                    if attempt == self.max_retries:
                        # Final failure
                        context.failed_records += len(chunk_data)
                        
                        logger.error(
                            "Chunk processing failed after all retries",
                            batch_id=str(context.batch_id),
                            chunk_index=chunk_index,
                            attempt=attempt + 1,
                            error=str(e)
                        )
                        
                        return ChunkResult(
                            chunk_index=chunk_index,
                            records_processed=0,
                            records_failed=len(chunk_data),
                            processing_time_ms=0,
                            errors=[f"Processing failed: {str(e)}"]
                        )
                    else:
                        # Retry with exponential backoff
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            "Chunk processing failed, retrying",
                            batch_id=str(context.batch_id),
                            chunk_index=chunk_index,
                            attempt=attempt + 1,
                            retry_delay=delay,
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
    
    async def _handle_chunk_results(self, results: List[Any], context: ProcessingContext):
        """Handle results from a batch of processed chunks"""
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Chunk processing exception: {result}")
                continue
            
            if isinstance(result, ChunkResult):
                # Log chunk completion
                logger.debug(
                    "Chunk result processed",
                    batch_id=str(context.batch_id),
                    chunk_index=result.chunk_index,
                    processed=result.records_processed,
                    failed=result.records_failed
                )
    
    async def _update_batch_status(self, context: ProcessingContext, status: str):
        """Update batch status in database"""
        try:
            async with get_db_session() as session:
                batch = await session.get(ImportBatch, context.batch_id)
                if batch:
                    batch.status = status
                    batch.processed_records = context.processed_records
                    batch.error_records = context.failed_records
                    
                    if status in ["completed", "failed"]:
                        batch.completed_at = datetime.now(timezone.utc)
                    
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update batch status: {e}")
    
    def get_active_pipelines(self) -> Dict[UUID, ProcessingContext]:
        """Get all currently active processing pipelines"""
        return self._active_pipelines.copy()
    
    async def cancel_pipeline(self, batch_id: UUID) -> bool:
        """Cancel an active pipeline"""
        if batch_id in self._active_pipelines:
            context = self._active_pipelines[batch_id]
            await self._update_batch_status(context, "cancelled")
            
            logger.info(f"Pipeline cancelled for batch {batch_id}")
            return True
        return False


# Global pipeline instance
_pipeline_instance = None


def get_async_pipeline() -> AsyncProcessingPipeline:
    """Get the global async processing pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = AsyncProcessingPipeline(
            max_concurrent_chunks=5,
            chunk_size=1000,
            max_retries=3
        )
    return _pipeline_instance