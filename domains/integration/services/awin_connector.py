import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import ImportBatch, ImportRecord


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

        df = pd.read_csv(file_path)

        batch = ImportBatch(
            source_type=self.SOURCE_TYPE,
            source_file=str(file_path),
            total_records=len(df),
            status="processing",
            started_at=datetime.utcnow()
        )
        self.session.add(batch)
        # We need to flush to get the batch ID for the records
        await self.session.flush()

        processed_count = 0
        error_count = 0

        for index, row in df.iterrows():
            source_data = row.to_dict()
            validation_errors = self._validate_row(row)

            if validation_errors:
                status = "error"
                error_count += 1
            else:
                status = "pending"
                processed_count += 1

            record = ImportRecord(
                batch_id=batch.id,
                source_data=json.loads(row.to_json()), # ensure it's a serializable dict
                status=status,
                validation_errors=validation_errors if validation_errors else None
            )
            self.session.add(record)

        batch.processed_records = processed_count
        batch.error_records = error_count
        batch.status = "completed"
        batch.completed_at = datetime.utcnow()

        await self.session.commit()
        print(f"Import complete for batch {batch.id}. "
              f"Total: {batch.total_records}, "
              f"Processed: {batch.processed_records}, "
              f"Errors: {batch.error_records}")

        return batch

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
