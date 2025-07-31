"""
Import Processing Engine
Replaces the chaotic SQL-based import system with a clean,
testable, and maintainable Python implementation.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
import json
import asyncio
from dataclasses import dataclass
from enum import Enum
import structlog
from pathlib import Path

from shared.database.connection import get_db_session
from shared.database.models import ImportBatch, ImportRecord
from .validators import StockXValidator, NotionValidator, SalesValidator, ValidationResult
from .parsers import CSVParser, JSONParser, ExcelParser
from .transformers import DataTransformer
import uuid

logger = structlog.get_logger(__name__)

class ImportStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SourceType(Enum):
    STOCKX = "stockx"
    NOTION = "notion"
    SALES = "sales"
    MANUAL = "manual"

@dataclass
class ImportResult:
    """Result of an import operation"""
    batch_id: str
    source_type: str
    total_records: int
    processed_records: int
    error_records: int
    validation_errors: List[str]
    processing_time_ms: float
    status: ImportStatus

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_data: List[Dict[str, Any]]

class ImportProcessor:
    """Central import processing engine"""
    
    def __init__(self):
        self.validators = {
            SourceType.STOCKX: StockXValidator(),
            SourceType.NOTION: NotionValidator(),
            SourceType.SALES: SalesValidator()
        }
        
        self.parsers = {
            '.csv': CSVParser(),
            '.json': JSONParser(),
            '.xlsx': ExcelParser(),
            '.xls': ExcelParser()
        }
        
        self.transformer = DataTransformer()
    
    async def process_import(
        self,
        source_type: SourceType,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ImportResult:
        """
        Process pre-parsed data through the import pipeline
        
        Args:
            source_type: Type of data source
            data: Pre-parsed data records
            metadata: Optional metadata about the import
            
        Returns:
            ImportResult with processing statistics
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(
            "Starting data import",
            source_type=source_type.value,
            records=len(data),
            metadata=metadata
        )
        
        try:
            # Create import batch
            filename = metadata.get('filename', 'direct_upload') if metadata else 'direct_upload'
            batch = await self._create_import_batch(
                source_type=source_type.value,
                source_file=filename,
                total_records=len(data)
            )
            
            # Validate data
            validation_result = await self._validate_data(data, source_type)
            
            logger.info("Validation completed", 
                       is_valid=validation_result.is_valid,
                       errors=len(validation_result.errors),
                       normalized_records=len(validation_result.normalized_data))
            
            if not validation_result.is_valid:
                await self._update_batch_status(batch.id, ImportStatus.FAILED)
                return ImportResult(
                    batch_id=str(batch.id),
                    source_type=source_type.value,
                    total_records=len(data),
                    processed_records=0,
                    error_records=len(data),
                    validation_errors=validation_result.errors,
                    processing_time_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
                    status=ImportStatus.FAILED
                )
            
            # Transform data
            from .transformers import get_transformer
            transformer = get_transformer(source_type.value)
            
            logger.info("About to transform data", 
                       records_to_transform=len(validation_result.normalized_data))
            
            if source_type == SourceType.STOCKX:
                transform_result = transformer.transform_stockx_data(validation_result.normalized_data)
            else:
                # Generic transformation
                transform_result = transformer.transform(validation_result.normalized_data, [], source_type.value)
            
            # Store transformed data
            processed_count = await self._store_records(
                batch_id=batch.id,
                records=transform_result.transformed_data,
                source_type=source_type
            )
            
            # Update batch status
            await self._update_batch_status(
                batch.id, 
                ImportStatus.COMPLETED,
                processed_records=processed_count,
                error_records=len(data) - processed_count
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                "Data import completed",
                batch_id=str(batch.id),
                processed=processed_count,
                errors=len(data) - processed_count,
                time_ms=processing_time
            )
            
            return ImportResult(
                batch_id=str(batch.id),
                source_type=source_type.value,
                total_records=len(data),
                processed_records=processed_count,
                error_records=len(data) - processed_count,
                validation_errors=validation_result.errors + transform_result.errors,
                processing_time_ms=processing_time,
                status=ImportStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error("Import processing failed", error=str(e))
            
            # Try to update batch status if batch was created
            try:
                if 'batch' in locals():
                    await self._update_batch_status(batch.id, ImportStatus.FAILED)
            except:
                pass
            
            return ImportResult(
                batch_id=str(uuid.uuid4()),  # Fallback ID
                source_type=source_type.value,
                total_records=len(data),
                processed_records=0,
                error_records=len(data),
                validation_errors=[f"Processing failed: {str(e)}"],
                processing_time_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
                status=ImportStatus.FAILED
            )
    
    async def process_file(
        self, 
        file_path: str, 
        source_type: Optional[SourceType] = None,
        batch_size: int = 1000
    ) -> ImportResult:
        """
        Process a data file through the complete import pipeline
        
        Args:
            file_path: Path to the data file
            source_type: Optional source type (auto-detected if None)
            batch_size: Number of records to process per batch
            
        Returns:
            ImportResult with processing statistics
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(
            "Starting file import",
            file_path=file_path,
            source_type=source_type.value if source_type else "auto-detect"
        )
        
        try:
            # 1. Parse the file
            raw_data = await self._parse_file(file_path)
            
            # 2. Auto-detect source type if not provided
            if not source_type:
                source_type = await self._detect_source_type(raw_data)
            
            # 3. Validate data
            validation_result = await self._validate_data(raw_data, source_type)
            
            # 4. Create import batch record
            batch = await self._create_import_batch(
                source_type=source_type.value,
                source_file=file_path,
                total_records=len(validation_result.normalized_data)
            )
            
            # 5. Process data in batches
            processed_count, error_count = await self._process_data_batches(
                batch.id,
                validation_result.normalized_data,
                batch_size
            )
            
            # 6. Update batch status
            await self._complete_import_batch(
                batch.id,
                processed_count,
                error_count,
                ImportStatus.COMPLETED
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                "File import completed successfully",
                batch_id=str(batch.id),
                total_records=len(raw_data),
                processed_records=processed_count,
                error_records=error_count,
                processing_time_ms=processing_time
            )
            
            return ImportResult(
                batch_id=str(batch.id),
                source_type=source_type.value,
                total_records=len(raw_data),
                processed_records=processed_count,
                error_records=error_count,
                validation_errors=validation_result.errors,
                processing_time_ms=processing_time,
                status=ImportStatus.COMPLETED
            )
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.error(
                "File import failed",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=processing_time
            )
            
            # Create failed batch record
            try:
                batch = await self._create_import_batch(
                    source_type=source_type.value if source_type else "unknown",
                    source_file=file_path,
                    total_records=0
                )
                await self._complete_import_batch(
                    batch.id, 0, 0, ImportStatus.FAILED
                )
                batch_id = str(batch.id)
            except:
                batch_id = "unknown"
            
            return ImportResult(
                batch_id=batch_id,
                source_type=source_type.value if source_type else "unknown",
                total_records=0,
                processed_records=0,
                error_records=1,
                validation_errors=[str(e)],
                processing_time_ms=processing_time,
                status=ImportStatus.FAILED
            )
    
    async def _parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse file based on extension"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension not in self.parsers:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        parser = self.parsers[file_extension]
        return await parser.parse(file_path)
    
    async def _detect_source_type(self, data: List[Dict[str, Any]]) -> SourceType:
        """Auto-detect the source type based on data structure"""
        if not data:
            raise ValueError("Cannot detect source type from empty data")
        
        sample = data[0]
        
        # StockX detection patterns
        stockx_patterns = ['Order Number', 'Sale Date', 'Item', 'Listing Price']
        if all(field in sample for field in stockx_patterns):
            return SourceType.STOCKX
        
        # Notion detection patterns  
        notion_patterns = ['id', 'properties', 'database_id']
        if all(field in sample for field in notion_patterns):
            return SourceType.NOTION
        
        # Sales CSV detection patterns
        sales_patterns = ['SKU', 'Sale Date', 'Status']
        if all(field in sample for field in sales_patterns):
            return SourceType.SALES
        
        # Default to manual import
        logger.warning(
            "Could not auto-detect source type, defaulting to manual",
            sample_fields=list(sample.keys())
        )
        return SourceType.MANUAL
    
    async def _validate_data(
        self, 
        data: List[Dict[str, Any]], 
        source_type: SourceType
    ) -> ValidationResult:
        """Validate and normalize data"""
        if source_type not in self.validators:
            # For unknown source types, perform basic validation
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["Unknown source type - minimal validation performed"],
                normalized_data=data
            )
        
        validator = self.validators[source_type]
        return await validator.validate_batch(data)
    
    async def _create_import_batch(
        self,
        source_type: str,
        source_file: str,
        total_records: int
    ) -> ImportBatch:
        """Create import batch database record"""
        from shared.database.connection import db_manager
        
        # Ensure database is initialized
        if not db_manager.session_factory:
            await db_manager.initialize()
            await db_manager.run_migrations()
            
        async with db_manager.get_session() as db:
            batch = ImportBatch(
                source_type=source_type,
                source_file=source_file,
                total_records=total_records,
                status=ImportStatus.PROCESSING.value,
                started_at=datetime.now(timezone.utc)
            )
            
            db.add(batch)
            await db.commit()
            await db.refresh(batch)
            
            return batch
    
    async def _update_batch_status(
        self,
        batch_id: str,
        status: ImportStatus,
        processed_records: int = None,
        error_records: int = None
    ):
        """Update import batch status"""
        from shared.database.connection import db_manager
        
        async with db_manager.get_session() as db:
            # Get the batch
            batch = await db.get(ImportBatch, batch_id)
            if batch:
                batch.status = status.value
                if processed_records is not None:
                    batch.processed_records = processed_records
                if error_records is not None:
                    batch.error_records = error_records
                if status == ImportStatus.COMPLETED:
                    batch.completed_at = datetime.now(timezone.utc)
                
                await db.commit()
    
    async def _store_records(
        self,
        batch_id: str,
        records: List[Dict[str, Any]],
        source_type: SourceType
    ) -> int:
        """Store transformed records in database"""
        from shared.database.connection import db_manager
        import json
        from datetime import datetime
        from decimal import Decimal
        
        def serialize_for_jsonb(obj):
            """Convert Python objects to JSON-serializable format for JSONB"""
            import math
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None  # Convert NaN and Inf to null
            elif isinstance(obj, dict):
                return {k: serialize_for_jsonb(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_for_jsonb(item) for item in obj]
            else:
                return obj
        
        stored_count = 0
        
        async with db_manager.get_session() as db:
            for record in records:
                try:
                    # Serialize the record for JSONB storage
                    serialized_record = serialize_for_jsonb(record)
                    
                    # Create import record
                    import_record = ImportRecord(
                        batch_id=batch_id,
                        source_data=serialized_record,
                        processed_data=serialized_record,
                        status="processed"
                    )
                    
                    db.add(import_record)
                    stored_count += 1
                    
                except Exception as e:
                    logger.warning("Failed to store record", error=str(e))
                    continue
            
            await db.commit()
        
        return stored_count
    
    async def _process_data_batches(
        self,
        batch_id: str,
        data: List[Dict[str, Any]],
        batch_size: int
    ) -> Tuple[int, int]:
        """Process data in manageable batches"""
        processed_count = 0
        error_count = 0
        
        # Process in chunks
        for i in range(0, len(data), batch_size):
            chunk = data[i:i + batch_size]
            
            try:
                # Create import records for this chunk
                await self._create_import_records(batch_id, chunk)
                processed_count += len(chunk)
                
                logger.debug(
                    "Processed data chunk",
                    batch_id=batch_id,
                    chunk_size=len(chunk),
                    total_processed=processed_count
                )
                
            except Exception as e:
                error_count += len(chunk)
                logger.error(
                    "Failed to process data chunk",
                    batch_id=batch_id,
                    chunk_size=len(chunk),
                    error=str(e)
                )
        
        return processed_count, error_count
    
    async def _create_import_records(
        self,
        batch_id: str,
        data_chunk: List[Dict[str, Any]]
    ):
        """Create import record entries in database"""
        async with get_db_session() as db:
            records = []
            
            for record_data in data_chunk:
                # Transform data using our transformer
                normalized_data = await self.transformer.transform(record_data)
                
                record = ImportRecord(
                    batch_id=batch_id,
                    raw_data=record_data,
                    normalized_data=normalized_data,
                    processed=True,
                    processing_started_at=datetime.now(timezone.utc),
                    processing_completed_at=datetime.now(timezone.utc),
                )
                records.append(record)
            
            db.add_all(records)
            await db.commit()
    
    async def _complete_import_batch(
        self,
        batch_id: str,
        processed_count: int,
        error_count: int,
        status: ImportStatus
    ):
        """Update import batch with final status"""
        async with get_db_session() as db:
            batch = await db.get(ImportBatch, batch_id)
            if batch:
                batch.processed_records = processed_count
                batch.error_records = error_count
                batch.status = status.value
                batch.completed_at = datetime.now(timezone.utc)
                
                await db.commit()

# Singleton instance
import_processor = ImportProcessor()