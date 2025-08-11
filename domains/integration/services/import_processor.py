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
from sqlalchemy.ext.asyncio import AsyncSession
import math

from shared.database.models import ImportBatch, ImportRecord
from .validators import StockXValidator, NotionValidator, SalesValidator, AliasValidator
from .parsers import CSVParser, JSONParser, ExcelParser
from .transformers import DataTransformer
import uuid
from decimal import Decimal

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

from domains.products.services.product_processor import ProductProcessor
from domains.sales.services.transaction_processor import TransactionProcessor

class ImportProcessor:
    """Central import processing engine"""
    
    def __init__(
        self,
        db_session: AsyncSession,
        product_processor: Optional[ProductProcessor] = None,
        transaction_processor: Optional[TransactionProcessor] = None
    ):
        self.db_session = db_session
        self.product_processor = product_processor or ProductProcessor(db_session)
        self.transaction_processor = transaction_processor or TransactionProcessor(db_session)
        self.validators = {
            SourceType.STOCKX: StockXValidator(),
            SourceType.NOTION: NotionValidator(),
            SourceType.SALES: SalesValidator(),
            SourceType.ALIAS: AliasValidator()
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
        metadata: Optional[Dict[str, Any]] = None,
        raw_data: Optional[List[Dict[str, Any]]] = None
    ) -> ImportResult:
        start_time = datetime.now(timezone.utc)
        logger.info("Starting data import", source_type=source_type.value, records=len(data), metadata=metadata)
        
        batch = None
        try:
            filename = metadata.get('filename', 'direct_upload') if metadata else 'direct_upload'
            batch = await self._create_import_batch(
                source_type=source_type.value,
                source_file=filename,
                total_records=len(data)
            )
            
            validation_result = await self._validate_data(data, source_type)
            
            if not validation_result.is_valid:
                await self._update_batch_status(batch.id, ImportStatus.FAILED, error_records=len(data))
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                return ImportResult(
                    batch_id=str(batch.id),
                    source_type=source_type.value,
                    total_records=len(data),
                    processed_records=0,
                    error_records=len(data),
                    validation_errors=validation_result.errors,
                    processing_time_ms=processing_time,
                    status=ImportStatus.FAILED
                )
            
            from .transformers import get_transformer
            transformer = get_transformer(source_type.value)
            
            if source_type == SourceType.STOCKX:
                transform_result = transformer.transform_stockx_data(validation_result.normalized_data)
            else: # Simplified for brevity
                transform_result = transformer.transform(validation_result.normalized_data, [], source_type.value)
            
            processed_count = await self._store_records(batch.id, transform_result.transformed_data, source_type, raw_data or data)
            
            await self._extract_products_from_batch(batch.id, processed_count)
            await self._create_transactions_from_batch(batch.id, processed_count)
            
            await self._update_batch_status(batch.id, ImportStatus.COMPLETED, processed_records=processed_count, error_records=len(data) - processed_count)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
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
            if batch:
                await self._update_batch_status(batch.id, ImportStatus.FAILED)
            # ... return failed ImportResult
            raise

    async def _parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        file_extension = Path(file_path).suffix.lower()
        parser = self.parsers.get(file_extension)
        if not parser:
            raise ValueError(f"Unsupported file format: {file_extension}")
        with open(file_path, 'rb') as f:
            content = f.read()
        return parser.parse(content).data

    async def _detect_source_type(self, data: List[Dict[str, Any]]) -> SourceType:
        if not data:
            raise ValueError("Cannot detect source type from empty data")
        sample = data[0]
        if all(k in sample for k in ['Order Number', 'Sale Date', 'Item']): return SourceType.STOCKX
        if all(k in sample for k in ['ORDER_NUMBER', 'NAME', 'CREDIT_DATE']): return SourceType.ALIAS
        if all(k in sample for k in ['id', 'properties', 'database_id']): return SourceType.NOTION
        if all(k in sample for k in ['SKU', 'Sale Date', 'Status']): return SourceType.SALES
        return SourceType.MANUAL

    async def _validate_data(self, data: List[Dict[str, Any]], source_type: SourceType) -> ValidationResult:
        validator = self.validators.get(source_type)
        if not validator:
            return ValidationResult(is_valid=True, errors=[], warnings=[], normalized_data=data)
        return await validator.validate_batch(data)

    async def _create_import_batch(self, source_type: str, source_file: str, total_records: int) -> ImportBatch:
        batch = ImportBatch(
            source_type=source_type,
            source_file=source_file,
            total_records=total_records,
            status=ImportStatus.PROCESSING.value,
            started_at=datetime.now(timezone.utc)
        )
        self.db_session.add(batch)
        await self.db_session.flush()
        await self.db_session.refresh(batch)
        return batch

    async def _update_batch_status(self, batch_id: uuid.UUID, status: ImportStatus, processed_records: Optional[int] = None, error_records: Optional[int] = None):
        batch = await self.db_session.get(ImportBatch, batch_id)
        if batch:
            batch.status = status.value
            if processed_records is not None: batch.processed_records = processed_records
            if error_records is not None: batch.error_records = error_records
            if status in [ImportStatus.COMPLETED, ImportStatus.FAILED]:
                batch.completed_at = datetime.now(timezone.utc)
            await self.db_session.flush()

    def _serialize_for_jsonb(self, obj: Any) -> Any:
        if isinstance(obj, datetime): return obj.isoformat()
        if isinstance(obj, Decimal): return float(obj)
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)): return None
        if isinstance(obj, dict): return {k: self._serialize_for_jsonb(v) for k, v in obj.items()}
        if isinstance(obj, list): return [self._serialize_for_jsonb(item) for item in obj]
        return obj

    async def _store_records(self, batch_id: uuid.UUID, records: List[Dict[str, Any]], source_type: SourceType, original_data: List[Dict[str, Any]]) -> int:
        stored_count = 0
        for idx, record in enumerate(records):
            try:
                original_record = original_data[idx] if idx < len(original_data) else record
                import_record = ImportRecord(
                    batch_id=batch_id,
                    source_data=self._serialize_for_jsonb(original_record),
                    processed_data=self._serialize_for_jsonb(record),
                    status="processed"
                )
                self.db_session.add(import_record)
                stored_count += 1
            except Exception as e:
                logger.warning("Failed to store record", error=str(e), record_index=idx)
        await self.db_session.flush()
        return stored_count

    async def _extract_products_from_batch(self, batch_id: uuid.UUID, processed_count: int):
        if processed_count == 0: return
        try:
            candidates = await self.product_processor.extract_products_from_batch(str(batch_id))
            if candidates:
                await self.product_processor.create_products_from_candidates(candidates)
        except Exception as e:
            logger.error("Product extraction failed", batch_id=batch_id, error=str(e))

    async def _create_transactions_from_batch(self, batch_id: uuid.UUID, processed_count: int):
        if processed_count == 0: return
        try:
            await self.transaction_processor.create_transactions_from_batch(str(batch_id))
        except Exception as e:
            logger.error("Transaction creation failed", batch_id=batch_id, error=str(e))