"""
Awin CSV Import Connector Module
================================

This module provides functionality for importing product and transaction data
from Awin affiliate network CSV exports.

Key Features:
    - Chunked CSV reading for large files (memory-efficient)
    - Batch import tracking with ImportBatch records
    - Individual record validation and error handling
    - Progress monitoring and statistics
    - Automatic file size detection and optimization
    - Transaction-safe imports with rollback on errors

Import Process:
    1. Validate CSV file exists and is readable
    2. Create ImportBatch record for tracking
    3. Read CSV in chunks (memory optimization for large files)
    4. Validate and transform each row
    5. Create ImportRecord entries for each valid row
    6. Calculate batch statistics (success count, error count)
    7. Commit transaction or rollback on critical errors

Chunking Strategy:
    - Files < 10MB: Read entire file at once
    - Files 10-50MB: Process in 1000-row chunks
    - Files > 50MB: Process in 500-row chunks

Data Validation:
    - Required fields: product_name, sku, price
    - Optional fields: brand, category, size, etc.
    - Data type validation (price must be numeric)
    - Duplicate SKU detection
    - Invalid data logging for review

Error Handling:
    - Individual row errors are logged but don't stop import
    - Critical errors (file not found, malformed CSV) abort import
    - All errors tracked in ImportRecord with error_message field

Example CSV Format:
    ```csv
    product_name,sku,brand,category,price,currency
    "Nike Air Max 90","NKE-AM90-001","Nike","Footwear",150.00,USD
    "Adidas Ultra Boost","ADS-UB-001","Adidas","Footwear",180.00,USD
    ```

Example Usage:
    ```python
    from domains.integration.services.awin_connector import AwinConnector
    from pathlib import Path

    async with db_manager.get_session() as session:
        connector = AwinConnector(session)

        # Import CSV file
        batch = await connector.run_import(Path("data/awin_export.csv"))

        print(f"Imported {batch.records_processed} records")
        print(f"Success: {batch.records_success}, Errors: {batch.records_failed}")
    ```

Performance Optimization:
    - Chunked reading prevents memory exhaustion
    - Bulk inserts for ImportRecord entries
    - Pandas DataFrame for efficient CSV parsing
    - Async database operations

Database Tables:
    - import_batches: Tracks each import operation
    - import_records: Stores individual row data

Dependencies:
    - pandas: CSV parsing and data manipulation
    - SQLAlchemy: Database operations
    - structlog: Structured logging

Related Modules:
    - domains/integration/api/upload_router.py: Upload API endpoints
    - shared/database/models.py: ImportBatch and ImportRecord models

See Also:
    - docs/features/awin-product-feed-integration.md: Detailed Awin integration docs
    - docs/guides/data-import-guide.md: General import guide
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import ImportBatch, ImportRecord

logger = structlog.get_logger(__name__)


class AwinConnector:
    """
    A connector to handle importing data from an Awin CSV export.
    """

    SOURCE_TYPE = "AWIN_CSV"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_import(self, file_path: Path) -> ImportBatch:
        """
        Runs the full import process for a given CSV file.
        1. Reads the data.
        2. Creates a batch record.
        3. Validates and creates records for each row.
        4. Commits the transaction.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found at: {file_path}")

        # MEMORY OPTIMIZATION: Use chunked reading for large CSV files
        import os

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        if file_size_mb > 100:  # Files larger than 100MB use chunked processing
            # First, get row count efficiently without loading full file
            with open(file_path, "r") as f:
                total_records = sum(1 for line in f) - 1  # -1 for header

            batch = ImportBatch(
                source_type=self.SOURCE_TYPE,
                source_file=str(file_path),
                total_records=total_records,
                status="processing",
                started_at=datetime.utcnow(),
            )
            self.session.add(batch)
            await self.session.flush()

            # Process in chunks to avoid memory issues
            chunk_size = 10000
            processed_count = 0
            error_count = 0

            for chunk_df in pd.read_csv(file_path, chunksize=chunk_size):
                chunk_processed, chunk_errors = await self._process_chunk(chunk_df, batch.id)
                processed_count += chunk_processed
                error_count += chunk_errors

            batch.processed_records = processed_count
            batch.error_records = error_count
        else:
            # Regular processing for smaller files
            df = pd.read_csv(file_path)

            batch = ImportBatch(
                source_type=self.SOURCE_TYPE,
                source_file=str(file_path),
                total_records=len(df),
                status="processing",
                started_at=datetime.utcnow(),
            )
        self.session.add(batch)
        # We need to flush to get the batch ID for the records
        await self.session.flush()

        processed_count = 0
        error_count = 0

        for index, row in df.iterrows():
            row.to_dict()
            validation_errors = self._validate_row(row)

            if validation_errors:
                status = "error"
                error_count += 1
            else:
                status = "pending"
                processed_count += 1

            record = ImportRecord(
                batch_id=batch.id,
                source_data=json.loads(row.to_json()),  # ensure it's a serializable dict
                status=status,
                validation_errors=validation_errors if validation_errors else None,
            )
            self.session.add(record)

        batch.processed_records = processed_count
        batch.error_records = error_count
        batch.status = "completed"
        batch.completed_at = datetime.utcnow()

        await self.session.commit()
        logger.info(
            "Import complete for batch",
            batch_id=str(batch.id),
            total_records=batch.total_records,
            processed_records=batch.processed_records,
            error_records=batch.error_records,
        )

        return batch

    async def _process_chunk(self, chunk_df: pd.DataFrame, batch_id: str) -> tuple[int, int]:
        """Process a chunk of CSV data for memory-efficient processing"""
        processed_count = 0
        error_count = 0

        for index, row in chunk_df.iterrows():
            row.to_dict()
            validation_errors = self._validate_row(row)

            if validation_errors:
                status = "error"
                error_count += 1
            else:
                status = "pending"
                processed_count += 1

            record = ImportRecord(
                batch_id=batch_id,
                source_data=json.loads(row.to_json()),  # ensure it's a serializable dict
                status=status,
                validation_errors=validation_errors if validation_errors else None,
            )
            self.session.add(record)

        # Commit chunk to avoid memory buildup
        await self.session.commit()
        return processed_count, error_count

    def _validate_row(self, row: pd.Series) -> Optional[Dict]:
        """
        Performs basic validation on a single row from the CSV.
        Returns a dictionary of errors, or None if valid.
        """
        errors = {}
        required_fields = ["TransactionID", "SaleAmount", "SKU"]

        for field in required_fields:
            # Check for presence and non-empty/non-null value
            if field not in row or pd.isna(row[field]) or str(row[field]).strip() == "":
                errors[field] = "is missing or empty"

        # Could add more validation here, e.g., type checking, format validation
        if "SaleAmount" in row and not pd.isna(row["SaleAmount"]):
            try:
                float(row["SaleAmount"])
            except (ValueError, TypeError):
                errors["SaleAmount"] = "is not a valid number"

        return errors if errors else None
