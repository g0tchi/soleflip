import io
from datetime import datetime
from typing import List, Optional

import pandas as pd
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domains.integration.services.import_processor import ImportProcessor, SourceType
from shared.database.connection import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


# This response model is specific to the upload endpoint
class UploadResponse(BaseModel):
    filename: str
    total_records: int
    validation_errors: List[str]
    status: str
    message: str
    imported: Optional[bool] = None
    batch_id: Optional[str] = None


# Models for StockX API Import (expected by Tauri GUI)
class ImportRequest(BaseModel):
    from_date: str
    to_date: str


class ImportResponse(BaseModel):
    status: str
    message: str
    batch_id: str


class ImportStatus(BaseModel):
    id: str
    source_type: str
    status: str
    progress: float
    records_processed: int
    records_failed: int
    created_at: str
    completed_at: Optional[str] = None


# This dependency provider is also specific to this endpoint's logic
def get_import_processor(db: AsyncSession = Depends(get_db_session)) -> ImportProcessor:
    # We define a new function here to avoid circular imports if it were in main
    return ImportProcessor(db)


@router.post("/webhooks/stockx/upload", response_model=UploadResponse, tags=["StockX Integration"])
async def upload_stockx_file(
    file: UploadFile = File(...),
    validate_only: bool = Form(False),
    batch_size: int = Form(1000),
    import_processor: ImportProcessor = Depends(get_import_processor),
):
    """
    Handles the upload of a StockX sales history CSV file.
    It validates the data and initiates an import process.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()

    # Use utf-8-sig to handle potential BOM (Byte Order Mark) from Excel exports
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8-sig")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {e}")

    raw_csv_data = df.to_dict("records")

    # Create an initial batch record to get a batch_id
    batch = await import_processor.create_initial_batch(
        source_type=SourceType.STOCKX, filename=file.filename
    )

    # TODO: In a production system, this should trigger a background task.
    # For now, we process it synchronously.
    await import_processor.process_import(
        batch_id=batch.id, source_type=SourceType.STOCKX, data=raw_csv_data, raw_data=raw_csv_data
    )

    # Refetch batch to get final status
    final_batch_status = await import_processor.db_session.get(type(batch), batch.id)

    return UploadResponse(
        filename=file.filename,
        total_records=final_batch_status.total_records or 0,
        validation_errors=[],  # This should be populated properly from the batch result
        status=final_batch_status.status,
        message=f"Processed {final_batch_status.processed_records} records.",
        imported=not validate_only,
        batch_id=str(final_batch_status.id),
    )


@router.post("/stockx/import", response_model=ImportResponse, tags=["StockX Integration"])
async def import_stockx_data(
    request: ImportRequest, import_processor: ImportProcessor = Depends(get_import_processor)
):
    """
    Initiates a StockX data import for the specified date range.
    This endpoint is expected by the Tauri GUI.
    """
    try:
        # Validate date format
        from_date = datetime.strptime(request.from_date, "%Y-%m-%d")
        to_date = datetime.strptime(request.to_date, "%Y-%m-%d")

        # Create an import batch for the date range
        batch = await import_processor.create_initial_batch(
            source_type=SourceType.STOCKX,
            filename=f"stockx_import_{request.from_date}_to_{request.to_date}",
        )

        # Fetch real StockX data for the specified date range
        from domains.integration.services.stockx_service import StockXService

        stockx_service = StockXService(import_processor.db_session)

        try:
            # Get sales history from StockX API
            stockx_data = await stockx_service.get_sales_history(
                start_date=from_date, end_date=to_date
            )

            if not stockx_data:
                return ImportResponse(
                    status="error",
                    message=f"No StockX data found for period {request.from_date} to {request.to_date}",
                    batch_id=str(batch.id),
                )

            # Process the real StockX import
            try:
                await import_processor.process_import(
                    batch_id=batch.id,
                    source_type=SourceType.STOCKX,
                    data=stockx_data,
                    raw_data=stockx_data,
                )
                logger.info("Import processing completed successfully", batch_id=str(batch.id))
            except Exception as e:
                logger.error(
                    "Import processing failed", batch_id=str(batch.id), error=str(e), exc_info=True
                )
                return ImportResponse(
                    status="error",
                    message=f"Import processing failed: {str(e)}",
                    batch_id=str(batch.id),
                )

        except Exception as e:
            logger.error("Failed to fetch StockX data", error=str(e), exc_info=True)
            return ImportResponse(
                status="error",
                message=f"Failed to fetch StockX data: {str(e)}",
                batch_id=str(batch.id),
            )

        return ImportResponse(
            status="success",
            message=f"StockX import initiated for period {request.from_date} to {request.to_date}",
            batch_id=str(batch.id),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD format. Error: {e}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate StockX import: {str(e)}")


@router.get("/import/{batch_id}/status", response_model=ImportStatus, tags=["Import Status"])
async def get_import_status(
    batch_id: str, import_processor: ImportProcessor = Depends(get_import_processor)
):
    """
    Get the status of an import batch by ID.
    This endpoint is expected by the Tauri GUI for tracking import progress.
    """
    try:
        from uuid import UUID

        batch_uuid = UUID(batch_id)

        # Get batch from database
        from shared.database.models import ImportBatch

        batch = await import_processor.db_session.get(ImportBatch, batch_uuid)

        if not batch:
            raise HTTPException(
                status_code=404, detail=f"Import batch with ID {batch_id} not found"
            )

        # Calculate progress
        progress = 0.0
        if batch.total_records and batch.total_records > 0:
            progress = (batch.processed_records or 0) / batch.total_records * 100.0
        elif batch.status in ["completed", "finished"]:
            progress = 100.0
        elif batch.status == "failed":
            progress = 0.0

        return ImportStatus(
            id=str(batch.id),
            source_type=batch.source_type or "stockx",
            status=batch.status or "pending",
            progress=progress,
            records_processed=batch.processed_records or 0,
            records_failed=batch.error_records or 0,
            created_at=(
                batch.created_at.isoformat() if batch.created_at else datetime.utcnow().isoformat()
            ),
            completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid batch ID format: {batch_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get import status: {str(e)}")
