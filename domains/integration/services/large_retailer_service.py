"""
Large Retailer Import Service
Handles large-scale product imports from retailers using streaming processing,
event-driven architecture, and optimized pipeline stages.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import ImportBatch
from shared.events import publish_event, ImportBatchCreatedEvent
from shared.processing.async_pipeline import ProcessingStage, get_async_pipeline
from shared.processing.streaming_processor import StreamingConfig, get_streaming_processor
from shared.processing.stages import (
    RetailerParsingStage,
    RetailerValidationStage,
    RetailerTransformationStage,
    RetailerPersistenceStage,
)
from shared.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class LargeRetailerImportService:
    """
    Service for importing large retailer datasets.
    Optimized for millions of products with memory-efficient streaming.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.pipeline = get_async_pipeline()
        
        # Configure for large retailer imports
        self.streaming_config = StreamingConfig(
            chunk_size=5000,  # Larger chunks for retailer data
            max_memory_mb=1000,  # Allow more memory for large imports
            max_concurrent_chunks=2,  # Conservative for very large imports
            buffer_size=16384,  # Larger buffer for file reading
            enable_backpressure=True,
            progress_interval=5000
        )
        
        self.streaming_processor = get_streaming_processor(self.streaming_config)
        self._setup_pipeline_stages()
    
    def _setup_pipeline_stages(self):
        """Setup processing stages for retailer imports"""
        
        # Register processing stages
        self.pipeline.register_stage(ProcessingStage.PARSING, RetailerParsingStage())
        self.pipeline.register_stage(ProcessingStage.VALIDATION, RetailerValidationStage())
        self.pipeline.register_stage(ProcessingStage.TRANSFORMATION, RetailerTransformationStage())
        self.pipeline.register_stage(ProcessingStage.PERSISTENCE, RetailerPersistenceStage())
        
        logger.info("Retailer import pipeline stages configured")
    
    async def import_csv_file(
        self,
        file_path: str,
        retailer_name: str,
        import_name: Optional[str] = None,
        encoding: str = 'utf-8-sig'
    ) -> UUID:
        """
        Import large CSV file from retailer.
        
        Args:
            file_path: Path to the CSV file
            retailer_name: Name of the retailer (e.g., "Nike", "Adidas")
            import_name: Optional custom name for the import
            encoding: File encoding (default: utf-8-sig for Excel exports)
        
        Returns:
            batch_id: UUID of the created import batch
        """
        
        batch_id = uuid4()
        file_name = Path(file_path).name
        
        logger.info(
            "Starting large retailer CSV import",
            batch_id=str(batch_id),
            file_path=file_path,
            retailer_name=retailer_name,
            file_name=file_name
        )
        
        try:
            # Create import batch record
            await self._create_import_batch(
                batch_id=batch_id,
                source_type=f"retailer_{retailer_name.lower()}",
                filename=file_name,
                import_name=import_name or f"{retailer_name} Product Import"
            )
            
            # Process using streaming processor
            context = await self.streaming_processor.process_csv_stream(
                file_path=file_path,
                batch_id=batch_id,
                source_type=f"retailer_{retailer_name.lower()}",
                encoding=encoding
            )
            
            logger.info(
                "Large retailer CSV import completed",
                batch_id=str(batch_id),
                processed_records=context.processed_records,
                failed_records=context.failed_records,
                progress_percentage=context.progress_percentage
            )
            
            return batch_id
            
        except Exception as e:
            logger.error(
                "Large retailer CSV import failed",
                batch_id=str(batch_id),
                file_path=file_path,
                error=str(e),
                exc_info=True
            )
            
            # Update batch status
            await self._update_batch_status(batch_id, "failed", error_message=str(e))
            raise
    
    async def import_json_file(
        self,
        file_path: str,
        retailer_name: str,
        import_name: Optional[str] = None
    ) -> UUID:
        """
        Import large JSON file from retailer.
        Supports both JSON arrays and JSONL (newline-delimited JSON).
        """
        
        batch_id = uuid4()
        file_name = Path(file_path).name
        
        logger.info(
            "Starting large retailer JSON import",
            batch_id=str(batch_id),
            file_path=file_path,
            retailer_name=retailer_name,
            file_name=file_name
        )
        
        try:
            # Create import batch record
            await self._create_import_batch(
                batch_id=batch_id,
                source_type=f"retailer_{retailer_name.lower()}",
                filename=file_name,
                import_name=import_name or f"{retailer_name} Product Import (JSON)"
            )
            
            # Process using streaming processor
            context = await self.streaming_processor.process_json_stream(
                file_path=file_path,
                batch_id=batch_id,
                source_type=f"retailer_{retailer_name.lower()}"
            )
            
            logger.info(
                "Large retailer JSON import completed",
                batch_id=str(batch_id),
                processed_records=context.processed_records,
                failed_records=context.failed_records
            )
            
            return batch_id
            
        except Exception as e:
            logger.error(
                "Large retailer JSON import failed",
                batch_id=str(batch_id),
                error=str(e),
                exc_info=True
            )
            
            await self._update_batch_status(batch_id, "failed", error_message=str(e))
            raise
    
    async def import_from_api(
        self,
        api_client,  # Generic API client
        retailer_name: str,
        import_name: Optional[str] = None,
        estimated_records: Optional[int] = None
    ) -> UUID:
        """
        Import from retailer API using streaming approach.
        Handles paginated API responses efficiently.
        """
        
        batch_id = uuid4()
        
        logger.info(
            "Starting large retailer API import",
            batch_id=str(batch_id),
            retailer_name=retailer_name,
            estimated_records=estimated_records
        )
        
        try:
            # Create import batch record
            await self._create_import_batch(
                batch_id=batch_id,
                source_type=f"retailer_{retailer_name.lower()}_api",
                filename=None,
                import_name=import_name or f"{retailer_name} API Import"
            )
            
            # Create API data generator
            api_generator = self._create_api_generator(api_client)
            
            # Process using streaming processor
            context = await self.streaming_processor.process_api_stream(
                api_generator=api_generator,
                batch_id=batch_id,
                source_type=f"retailer_{retailer_name.lower()}_api",
                estimated_records=estimated_records
            )
            
            logger.info(
                "Large retailer API import completed",
                batch_id=str(batch_id),
                processed_records=context.processed_records,
                failed_records=context.failed_records
            )
            
            return batch_id
            
        except Exception as e:
            logger.error(
                "Large retailer API import failed",
                batch_id=str(batch_id),
                error=str(e),
                exc_info=True
            )
            
            await self._update_batch_status(batch_id, "failed", error_message=str(e))
            raise
    
    async def get_import_status(self, batch_id: UUID) -> Dict:
        """Get detailed import status"""
        
        batch_repo = BaseRepository(ImportBatch, self.db_session)
        batch = await batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise ValueError(f"Import batch {batch_id} not found")
        
        # Calculate progress
        progress = 0.0
        if batch.total_records and batch.total_records > 0:
            progress = (batch.processed_records or 0) / batch.total_records * 100.0
        elif batch.status in ["completed", "finished"]:
            progress = 100.0
        
        return {
            "batch_id": str(batch.id),
            "status": batch.status,
            "source_type": batch.source_type,
            "filename": batch.filename,
            "total_records": batch.total_records,
            "processed_records": batch.processed_records or 0,
            "failed_records": batch.error_records or 0,
            "progress_percentage": progress,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "error_message": batch.error_message,
        }
    
    async def cancel_import(self, batch_id: UUID) -> bool:
        """Cancel an active import"""
        
        # Try to cancel in pipeline
        cancelled = await self.pipeline.cancel_pipeline(batch_id)
        
        if cancelled:
            await self._update_batch_status(batch_id, "cancelled")
            logger.info("Import cancelled", batch_id=str(batch_id))
        
        return cancelled
    
    async def _create_import_batch(
        self,
        batch_id: UUID,
        source_type: str,
        filename: Optional[str],
        import_name: str
    ) -> ImportBatch:
        """Create import batch record"""
        
        batch_repo = BaseRepository(ImportBatch, self.db_session)
        
        batch = await batch_repo.create(
            id=batch_id,
            source_type=source_type,
            filename=filename,
            status="queued",
            import_name=import_name,
            created_at=datetime.now(timezone.utc)
        )
        
        # Publish event
        await publish_event(ImportBatchCreatedEvent(
            aggregate_id=batch_id,
            batch_id=batch_id,
            source_type=source_type,
            filename=filename,
            total_records=None
        ))
        
        return batch
    
    async def _update_batch_status(
        self,
        batch_id: UUID,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update batch status"""
        
        batch_repo = BaseRepository(ImportBatch, self.db_session)
        
        update_data = {"status": status}
        if error_message:
            update_data["error_message"] = error_message
        if status in ["completed", "failed", "cancelled"]:
            update_data["completed_at"] = datetime.now(timezone.utc)
        
        await batch_repo.update(batch_id, **update_data)
    
    async def _create_api_generator(self, api_client):
        """Create async generator from API client"""
        # This would be implemented based on the specific API client
        # For now, just a placeholder
        
        async def api_generator():
            # Example implementation
            page = 1
            while True:
                try:
                    response = await api_client.get_products(page=page, per_page=1000)
                    
                    if not response.get('data'):
                        break
                    
                    for item in response['data']:
                        yield item
                    
                    if not response.get('has_more', False):
                        break
                    
                    page += 1
                
                except Exception as e:
                    logger.error(f"API fetch error: {e}")
                    break
        
        return api_generator()


# Service factory function
def create_retailer_import_service(db_session: AsyncSession) -> LargeRetailerImportService:
    """Create retailer import service instance"""
    return LargeRetailerImportService(db_session)