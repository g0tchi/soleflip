from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import io
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from domains.integration.services.import_processor import ImportProcessor, SourceType

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

# This dependency provider is also specific to this endpoint's logic
def get_import_processor(db: AsyncSession = Depends(get_db_session)) -> ImportProcessor:
    # We define a new function here to avoid circular imports if it were in main
    return ImportProcessor(db)

@router.post("/webhooks/stockx/upload", response_model=UploadResponse, tags=["StockX Integration"])
async def upload_stockx_file(
    file: UploadFile = File(...),
    validate_only: bool = Form(False),
    batch_size: int = Form(1000),
    import_processor: ImportProcessor = Depends(get_import_processor)
):
    """
    Handles the upload of a StockX sales history CSV file.
    It validates the data and initiates an import process.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()

    # Use utf-8-sig to handle potential BOM (Byte Order Mark) from Excel exports
    try:
        df = pd.read_csv(io.StringIO(content.decode('utf-8-sig')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {e}")

    raw_csv_data = df.to_dict('records')

    # Create an initial batch record to get a batch_id
    batch = await import_processor.create_initial_batch(
        source_type=SourceType.STOCKX,
        filename=file.filename
    )

    # TODO: In a production system, this should trigger a background task.
    # For now, we process it synchronously.
    await import_processor.process_import(
        batch_id=batch.id,
        source_type=SourceType.STOCKX,
        data=raw_csv_data,
        raw_data=raw_csv_data
    )

    # Refetch batch to get final status
    final_batch_status = await import_processor.db_session.get(type(batch), batch.id)

    return UploadResponse(
        filename=file.filename,
        total_records=final_batch_status.total_records or 0,
        validation_errors=[], # This should be populated properly from the batch result
        status=final_batch_status.status,
        message=f"Processed {final_batch_status.processed_records} records.",
        imported=not validate_only,
        batch_id=str(final_batch_status.id)
    )
