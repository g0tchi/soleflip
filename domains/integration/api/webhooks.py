"""
n8n-Compatible Webhook Endpoints
Replaces direct SQL queries in n8n with proper API endpoints
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session

from ..repositories.import_repository import ImportRepository
from ..services.import_processor import ImportProcessor, ImportStatus, SourceType
from ..services.stockx_service import StockXService

logger = structlog.get_logger(__name__)

router = APIRouter()

# --- Dependency Provider Functions ---


def get_import_processor(db: AsyncSession = Depends(get_db_session)) -> ImportProcessor:
    return ImportProcessor(db)


def get_stockx_service(db: AsyncSession = Depends(get_db_session)) -> StockXService:
    return StockXService(db)


def get_import_repository(db: AsyncSession = Depends(get_db_session)) -> ImportRepository:
    return ImportRepository(db)


# --- Pydantic Models for API ---


class StockXImportRequest(BaseModel):
    from_date: date
    to_date: date


class StockXImportResponse(BaseModel):
    status: str = "processing_started"
    message: str = "Import has been successfully queued."
    batch_id: UUID


class ImportStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    source_file: Optional[str] = None
    total_records: int
    processed_records: int
    error_records: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


@router.post(
    "/stockx/import-orders",
    response_model=StockXImportResponse,
    status_code=202,
    tags=["StockX Integration", "Import"],
)
async def stockx_import_orders_webhook(
    request: StockXImportRequest,
    background_tasks: BackgroundTasks,
    stockx_service: StockXService = Depends(get_stockx_service),
    import_processor: ImportProcessor = Depends(get_import_processor),
):
    """
    Triggers a background task to import historical orders from the StockX API
    for a given date range.
    """
    logger.info(
        "StockX API import triggered via webhook",
        from_date=request.from_date,
        to_date=request.to_date,
    )

    batch = await import_processor.create_initial_batch(
        source_type=SourceType.STOCKX,
        filename=f"stockx_api_import_{request.from_date}_to_{request.to_date}.json",
    )

    async def run_import_task(batch_id: UUID):
        try:
            orders_data = await stockx_service.get_historical_orders(
                from_date=request.from_date, to_date=request.to_date
            )
            if not orders_data:
                logger.info("No new orders found from StockX API.", batch_id=str(batch_id))
                await import_processor.update_batch_status(
                    batch_id, ImportStatus.COMPLETED, processed_records=0, total_records=0
                )
                return

            await import_processor.process_import(
                batch_id=batch_id,
                source_type=SourceType.STOCKX,
                data=orders_data,
                raw_data=orders_data,
            )
        except Exception as e:
            logger.error(
                "StockX API import background task failed",
                batch_id=str(batch_id),
                error=str(e),
                exc_info=True,
            )
            await import_processor.update_batch_status(batch_id, ImportStatus.FAILED)

    background_tasks.add_task(run_import_task, batch.id)

    return StockXImportResponse(batch_id=batch.id)


@router.get("/import-status/{batch_id}", response_model=ImportStatusResponse, tags=["Import"])
async def get_import_status(
    batch_id: UUID, repo: ImportRepository = Depends(get_import_repository)
):
    """
    Retrieves the current status of an import batch.
    """
    logger.info("Fetching status for import batch", batch_id=str(batch_id))

    batch = await repo.get_by_id(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    return batch
