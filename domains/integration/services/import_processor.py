"""
Import Processing Engine
Replaces the chaotic SQL-based import system with a clean,
testable, and maintainable Python implementation.
"""

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from domains.products.services.product_processor import ProductProcessor
from domains.sales.services.transaction_processor import TransactionProcessor
from shared.database.models import ImportBatch, ImportRecord

from .parsers import CSVParser, ExcelParser, JSONParser
from .transformers import DataTransformer
from .validators import AliasValidator, NotionValidator, SalesValidator, StockXValidator

logger = structlog.get_logger(__name__)


class ImportStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class SourceType(Enum):
    STOCKX = "stockx"
    NOTION = "notion"
    SALES = "sales"
    ALIAS = "alias"
    MANUAL = "manual"


@dataclass
class ImportResult:
    batch_id: str
    # ... other fields


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_data: List[Dict[str, Any]]


class ImportProcessor:
    def __init__(
        self,
        db_session: AsyncSession,
        product_processor: Optional[ProductProcessor] = None,
        transaction_processor: Optional[TransactionProcessor] = None,
    ):
        self.db_session = db_session
        self.product_processor = product_processor or ProductProcessor(db_session)
        self.transaction_processor = transaction_processor or TransactionProcessor(db_session)
        # ... (rest of __init__ is the same)
        self.validators = {
            SourceType.STOCKX: StockXValidator(db_session),
            SourceType.NOTION: NotionValidator(db_session),
            SourceType.SALES: SalesValidator(db_session),
            SourceType.ALIAS: AliasValidator(db_session),
        }
        self.parsers = {
            ".csv": CSVParser(),
            ".json": JSONParser(),
            ".xlsx": ExcelParser(),
            ".xls": ExcelParser(),
        }
        self.transformer = DataTransformer()

    async def create_initial_batch(
        self, source_type: SourceType, filename: Optional[str] = None
    ) -> ImportBatch:
        """
        Creates an initial ImportBatch record with a 'pending' status.
        This is called before the background processing begins.
        """
        logger.info(
            "Creating initial import batch record", source_type=source_type.value, filename=filename
        )
        batch = ImportBatch(
            source_type=source_type.value,
            source_file=filename or "api_import",
            status=ImportStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
        )
        self.db_session.add(batch)
        await self.db_session.flush()
        await self.db_session.refresh(batch)
        logger.info("Batch record created", batch_id=str(batch.id))
        return batch

    async def process_import(
        self,
        batch_id: UUID,
        source_type: SourceType,
        data: List[Dict[str, Any]],
        raw_data: Optional[List[Dict[str, Any]]] = None,
        retry_count: int = 0,
    ):
        """
        Processes a given dataset for an existing import batch.
        This method is designed to be run in a background task.
        """
        logger.info("Starting data processing for batch", batch_id=str(batch_id), records=len(data))

        batch = await self.db_session.get(ImportBatch, batch_id)
        if not batch:
            logger.error("Batch not found for processing", batch_id=str(batch_id))
            return

        try:
            # Update batch status to 'processing'
            await self.update_batch_status(
                batch_id, ImportStatus.PROCESSING, total_records=len(data)
            )

            logger.info(
                "Starting validation",
                batch_id=str(batch_id),
                source_type=source_type.value,
                data_sample=str(data[0])[:200] if data else "empty",
            )
            validation_result = await self._validate_data(data, source_type)

            if not validation_result.is_valid:
                logger.error(
                    "Validation failed", batch_id=str(batch_id), errors=validation_result.errors
                )
                await self.update_batch_status(
                    batch_id, ImportStatus.FAILED, error_records=len(data)
                )
                return

            from .transformers import get_transformer

            transformer = get_transformer(source_type.value)

            transform_result = transformer.transform(
                validation_result.normalized_data, [], source_type.value
            )

            processed_count = await self._store_records(
                batch_id, transform_result.transformed_data, source_type, raw_data or data
            )

            await self._extract_products_from_batch(batch_id, processed_count)
            await self._create_transactions_from_batch(batch_id, processed_count)

            await self.update_batch_status(
                batch_id,
                ImportStatus.COMPLETED,
                processed_records=processed_count,
                error_records=len(data) - processed_count,
            )
            logger.info("Successfully processed batch", batch_id=str(batch_id))

        except Exception as e:
            logger.error(
                "Import processing failed for batch",
                batch_id=str(batch_id),
                error=str(e),
                retry_count=retry_count,
                exc_info=True,
            )
            
            # Determine if we should retry based on error type and source
            should_retry = await self._should_retry_batch(batch_id, e, retry_count, source_type)
            
            if should_retry:
                await self._schedule_retry(batch_id, source_type, data, raw_data, retry_count)
            else:
                await self.update_batch_status(batch_id, ImportStatus.FAILED, error_records=len(data))
                # Store error details in batch record
                batch = await self.db_session.get(ImportBatch, batch_id)
                if batch:
                    batch.error_message = str(e)[:1000]  # Truncate long error messages
                    await self.db_session.commit()
                raise

    async def update_batch_status(
        self,
        batch_id: UUID,
        status: ImportStatus,
        total_records: Optional[int] = None,
        processed_records: Optional[int] = None,
        error_records: Optional[int] = None,
    ):
        batch = await self.db_session.get(ImportBatch, batch_id)
        if batch:
            batch.status = status.value
            if total_records is not None:
                batch.total_records = total_records
            if processed_records is not None:
                batch.processed_records = processed_records
            if error_records is not None:
                batch.error_records = error_records
            if status in [ImportStatus.COMPLETED, ImportStatus.FAILED]:
                batch.completed_at = datetime.now(timezone.utc)
            await self.db_session.commit()

    # ... (other private methods like _validate_data, _store_records, etc. remain the same) ...

    async def _validate_data(
        self, data: List[Dict[str, Any]], source_type: SourceType
    ) -> ValidationResult:
        validator = self.validators.get(source_type)
        if not validator:
            return ValidationResult(is_valid=True, errors=[], warnings=[], normalized_data=data)
        return await validator.validate_batch(data)

    def _serialize_for_jsonb(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: self._serialize_for_jsonb(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._serialize_for_jsonb(item) for item in obj]
        return obj

    async def _store_records(
        self,
        batch_id: UUID,
        records: List[Dict[str, Any]],
        source_type: SourceType,
        original_data: List[Dict[str, Any]],
    ) -> int:
        stored_count = 0
        for idx, record in enumerate(records):
            try:
                original_record = original_data[idx] if idx < len(original_data) else record
                import_record = ImportRecord(
                    batch_id=batch_id,
                    source_data=self._serialize_for_jsonb(original_record),
                    processed_data=self._serialize_for_jsonb(record),
                    status="processed",
                )
                self.db_session.add(import_record)
                stored_count += 1
            except Exception as e:
                logger.warning("Failed to store record", error=str(e), record_index=idx)
        await self.db_session.commit()
        return stored_count

    async def _extract_products_from_batch(self, batch_id: UUID, processed_count: int):
        if processed_count == 0:
            return
        try:
            candidates = await self.product_processor.extract_products_from_batch(str(batch_id))
            if candidates:
                await self.product_processor.create_products_from_candidates(candidates)
        except Exception as e:
            logger.error("Product extraction failed", batch_id=batch_id, error=str(e))

    async def _create_transactions_from_batch(self, batch_id: UUID, processed_count: int):
        if processed_count == 0:
            return
        try:
            await self.transaction_processor.create_transactions_from_batch(str(batch_id))
        except Exception as e:
            logger.error("Transaction creation failed", batch_id=batch_id, error=str(e))

    async def _should_retry_batch(
        self, 
        batch_id: UUID, 
        error: Exception, 
        retry_count: int, 
        source_type: SourceType
    ) -> bool:
        """Determine if a failed batch should be retried based on error type and retry count"""
        
        # Maximum retry attempts based on source type
        max_retries = {
            SourceType.STOCKX: 3,  # StockX API can be flaky
            SourceType.NOTION: 2,  # Notion API less flaky
            SourceType.SALES: 1,   # Local processing, rarely needs retry
            SourceType.ALIAS: 1,   # Local processing
            SourceType.MANUAL: 0   # Manual uploads shouldn't auto-retry
        }.get(source_type, 1)
        
        if retry_count >= max_retries:
            logger.info(
                "Maximum retry attempts reached", 
                batch_id=str(batch_id), 
                retry_count=retry_count, 
                max_retries=max_retries
            )
            return False
        
        # Determine if error is retryable
        retryable_errors = [
            "timeout",
            "connection",
            "503",  # Service Unavailable
            "502",  # Bad Gateway
            "500",  # Internal Server Error
            "429",  # Rate Limited
            "401",  # Unauthorized (token might have expired)
            "network",
            "temporary"
        ]
        
        error_str = str(error).lower()
        is_retryable = any(retryable_error in error_str for retryable_error in retryable_errors)
        
        # Special handling for StockX-specific errors
        if source_type == SourceType.STOCKX:
            stockx_retryable = [
                "token",
                "authentication", 
                "rate limit",
                "api key",
                "quota exceeded"
            ]
            is_retryable = is_retryable or any(sx_error in error_str for sx_error in stockx_retryable)
        
        logger.info(
            "Retry eligibility check",
            batch_id=str(batch_id),
            error_type=type(error).__name__,
            error_message=str(error)[:200],
            is_retryable=is_retryable,
            retry_count=retry_count,
            max_retries=max_retries
        )
        
        return is_retryable

    async def _schedule_retry(
        self,
        batch_id: UUID,
        source_type: SourceType,
        data: List[Dict[str, Any]],
        raw_data: Optional[List[Dict[str, Any]]],
        retry_count: int
    ):
        """Schedule a retry for a failed import batch with exponential backoff"""
        
        # Update batch status to RETRYING
        await self.update_batch_status(batch_id, ImportStatus.RETRYING)
        batch = await self.db_session.get(ImportBatch, batch_id)
        if batch:
            batch.retry_count = retry_count + 1
            batch.last_error = f"Retry #{retry_count + 1} scheduled"
            await self.db_session.commit()
        
        # Calculate backoff delay: 30s, 2min, 5min, 15min
        backoff_delays = [30, 120, 300, 900]
        delay = backoff_delays[min(retry_count, len(backoff_delays) - 1)]
        
        logger.info(
            "Scheduling import retry",
            batch_id=str(batch_id),
            retry_count=retry_count + 1,
            delay_seconds=delay
        )
        
        # Schedule retry as background task
        asyncio.create_task(self._execute_retry(batch_id, source_type, data, raw_data, retry_count, delay))

    async def _execute_retry(
        self,
        batch_id: UUID,
        source_type: SourceType,
        data: List[Dict[str, Any]],
        raw_data: Optional[List[Dict[str, Any]]],
        retry_count: int,
        delay: int
    ):
        """Execute a retry after the specified delay"""
        try:
            await asyncio.sleep(delay)
            
            logger.info(
                "Executing import retry",
                batch_id=str(batch_id),
                retry_attempt=retry_count + 1
            )
            
            # Re-attempt the import with incremented retry count
            await self.process_import(batch_id, source_type, data, raw_data, retry_count + 1)
            
        except Exception as e:
            logger.error(
                "Retry execution failed",
                batch_id=str(batch_id),
                retry_attempt=retry_count + 1,
                error=str(e),
                exc_info=True
            )
            # The process_import method will handle further retries or final failure
