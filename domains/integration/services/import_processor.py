"""
Import Processing Engine
Replaces the chaotic SQL-based import system with a clean,
testable, and maintainable Python implementation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
from dataclasses import dataclass
from enum import Enum
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
import math
from uuid import UUID
from decimal import Decimal

from shared.database.models import ImportBatch, ImportRecord
from .validators import StockXValidator, NotionValidator, SalesValidator, AliasValidator
from .parsers import CSVParser, JSONParser, ExcelParser
from .transformers import DataTransformer
from domains.products.services.product_processor import ProductProcessor
from domains.sales.services.transaction_processor import TransactionProcessor

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
                exc_info=True,
            )
            await self.update_batch_status(batch_id, ImportStatus.FAILED, error_records=len(data))
            # Optionally store the main error message in the batch record
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
