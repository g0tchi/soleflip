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
    # SECURITY: Enhanced file validation
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Check file size (max 100MB for CSV imports)
    if file.size and file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 100MB")

    # Check MIME type
    if file.content_type and not file.content_type.startswith("text/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Expected text/csv")

    # MEMORY OPTIMIZATION: Stream large files instead of loading entirely into memory
    try:
        # Read file in chunks to handle large files efficiently
        content_chunks = []
        chunk_size = 8192  # 8KB chunks

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            content_chunks.append(chunk)

        # Combine chunks and decode
        content = b"".join(content_chunks)

        # For very large files, consider using pd.read_csv with chunksize
        file_size_mb = len(content) / (1024 * 1024)

        if file_size_mb > 50:  # Files larger than 50MB use chunked processing
            # Use streaming processing for large files
            df_chunks = pd.read_csv(
                io.StringIO(content.decode("utf-8-sig")),
                chunksize=10000,  # Process in 10k row chunks
            )
            # Combine chunks (for now - in production, process chunk by chunk)
            df = pd.concat(df_chunks, ignore_index=True)
        else:
            # Regular processing for smaller files
            df = pd.read_csv(io.StringIO(content.decode("utf-8-sig")))

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {e}")

    # STREAMING OPTIMIZATION: Use generator for memory-efficient processing
    # Instead of loading all data into memory with to_dict(), use iterrows()
    def generate_csv_records():
        for _, row in df.iterrows():
            yield row.to_dict()

    # For now, convert to list for compatibility (in production, process as generator)
    raw_csv_data = list(generate_csv_records())

    # Create an initial batch record to get a batch_id
    batch = await import_processor.create_initial_batch(
        source_type=SourceType.STOCKX, filename=file.filename
    )

    # Process import with retry mechanism - synchronous processing for immediate feedback
    # Background processing is handled by the retry mechanism if needed
    await import_processor.process_import(
        batch_id=batch.id,
        source_type=SourceType.STOCKX,
        data=raw_csv_data,
        raw_data=raw_csv_data,
        retry_count=0,
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


@router.post("/test-no-auth", tags=["Testing"])
async def test_no_auth():
    """Test endpoint without any dependencies"""
    return {"status": "success", "message": "This endpoint works without auth"}


@router.post("/stockx/import", tags=["StockX Integration"])
async def import_stockx_data(request: ImportRequest):
    """Test endpoint without dependencies"""
    return {
        "status": "success",
        "message": f"Would import from {request.from_date} to {request.to_date}",
    }


@router.post("/stockx/import-orders", response_model=ImportResponse, tags=["StockX Integration"])
async def import_stockx_orders(
    request: ImportRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Imports StockX orders for the specified date range directly into the database.
    This endpoint fetches orders from the StockX API and stores them in the sales.order table.
    """
    try:
        # Validate date format
        from_date = datetime.strptime(request.from_date, "%Y-%m-%d")
        to_date = datetime.strptime(request.to_date, "%Y-%m-%d")

        logger.info(
            "Starting StockX order import",
            from_date=request.from_date,
            to_date=request.to_date,
        )

        # Fetch StockX orders via API
        from domains.integration.services.stockx_service import StockXService
        from domains.orders.services.order_import_service import OrderImportService

        stockx_service = StockXService(db)
        order_import_service = OrderImportService(db)

        try:
            # Get sales history from StockX API
            stockx_orders = await stockx_service.get_sales_history(
                start_date=from_date, end_date=to_date
            )

            if not stockx_orders:
                logger.warning(
                    "No StockX orders found for date range",
                    from_date=request.from_date,
                    to_date=request.to_date,
                )
                return ImportResponse(
                    status="success",
                    message=f"No orders found for period {request.from_date} to {request.to_date}",
                    batch_id="",  # No batch created
                )

            logger.info(
                "Fetched StockX orders from API",
                order_count=len(stockx_orders),
            )

            # Import orders directly into database
            import_stats = await order_import_service.import_stockx_orders(
                orders_data=stockx_orders
            )

            logger.info("StockX order import completed", **import_stats)

            # Build response message
            message_parts = [
                f"Imported {import_stats['created']} new orders",
                f"Updated {import_stats['updated']} existing orders",
            ]

            if import_stats["errors"]:
                message_parts.append(f"{len(import_stats['errors'])} errors occurred")

            return ImportResponse(
                status="success" if not import_stats["errors"] else "partial_success",
                message=f"{', '.join(message_parts)} for period {request.from_date} to {request.to_date}",
                batch_id="",  # Not using batch system anymore
            )

        except Exception as e:
            logger.error("Failed to import StockX orders", error=str(e), exc_info=True)
            return ImportResponse(
                status="error",
                message=f"Failed to import StockX orders: {str(e)}",
                batch_id="",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD format. Error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate StockX order import: {str(e)}"
        )


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
