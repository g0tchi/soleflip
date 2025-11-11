"""
n8n-Compatible Webhook Endpoints
Replaces direct SQL queries in n8n with proper API endpoints
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domains.orders.services.order_import_service import OrderImportService
from shared.database.connection import get_db_session
from shared.database.models import SystemConfig

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


def get_order_import_service(db: AsyncSession = Depends(get_db_session)) -> OrderImportService:
    return OrderImportService(db)


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
    "/stockx/import-orders-background",
    response_model=StockXImportResponse,
    status_code=202,
    tags=["StockX Integration", "Import"],
)
async def stockx_import_orders_webhook_background(
    request: StockXImportRequest,
    background_tasks: BackgroundTasks,
    stockx_service: StockXService = Depends(get_stockx_service),
    order_import_service: OrderImportService = Depends(get_order_import_service),
    import_processor: ImportProcessor = Depends(get_import_processor),
):
    """
    Triggers a background task to import historical orders from the StockX API
    for a given date range. Uses OrderImportService for proper API JSON handling.
    """
    logger.info(
        "StockX API import triggered via webhook",
        from_date=request.from_date,
        to_date=request.to_date,
    )

    # Create tracking batch for monitoring
    batch = await import_processor.create_initial_batch(
        source_type=SourceType.STOCKX,
        filename=f"stockx_api_import_{request.from_date}_to_{request.to_date}.json",
    )

    async def run_import_task(batch_id: UUID):
        try:
            # Fetch orders from StockX API
            orders_data = await stockx_service.get_historical_orders(
                from_date=request.from_date, to_date=request.to_date
            )

            if not orders_data:
                logger.info("No new orders found from StockX API.", batch_id=str(batch_id))
                await import_processor.update_batch_status(
                    batch_id, ImportStatus.COMPLETED, processed_records=0, total_records=0
                )
                return

            # Update batch status to processing
            await import_processor.update_batch_status(
                batch_id, ImportStatus.PROCESSING, total_records=len(orders_data)
            )

            # Import orders using OrderImportService (handles API JSON structure)
            import_stats = await order_import_service.import_stockx_orders(
                orders_data=orders_data, batch_id=str(batch_id)
            )

            # Update batch with results
            await import_processor.update_batch_status(
                batch_id,
                ImportStatus.COMPLETED,
                processed_records=import_stats["created"] + import_stats["updated"],
                error_records=len(import_stats.get("errors", [])),
            )

            logger.info(
                "StockX API import completed successfully", batch_id=str(batch_id), **import_stats
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


class SystemConfigStatusResponse(BaseModel):
    """Response model for system config status."""

    key: str
    has_value: bool
    created_at: datetime
    updated_at: datetime


@router.get(
    "/stockx/credentials/status",
    response_model=list[SystemConfigStatusResponse],
    tags=["StockX Integration"],
)
async def get_stockx_credentials_status(db: AsyncSession = Depends(get_db_session)):
    """
    Get current status of StockX credentials in core.system_config.
    Shows updated_at timestamps to verify when credentials were last modified.
    """
    logger.info("Fetching StockX credentials status from core.system_config")

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key.like("stockx%")).order_by(SystemConfig.key)
    )
    configs = result.scalars().all()

    if not configs:
        logger.warning("No StockX credentials found in database")
        raise HTTPException(status_code=404, detail="No StockX credentials found in database")

    return [
        SystemConfigStatusResponse(
            key=config.key,
            has_value=bool(config.value_encrypted),
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        for config in configs
    ]


@router.post("/stockx/credentials/update-timestamps", tags=["StockX Integration"])
async def update_stockx_credentials_timestamps(db: AsyncSession = Depends(get_db_session)):
    """
    Update the updated_at timestamps for all StockX credentials in core.system_config.
    This does NOT modify the actual credential values (client_id, client_secret, refresh_token, api_key).
    Only updates the metadata timestamp to reflect current time.
    """
    logger.info("Updating updated_at timestamps for StockX credentials")

    # Get current credentials before update
    result = await db.execute(select(SystemConfig).where(SystemConfig.key.like("stockx%")))
    configs = result.scalars().all()

    if not configs:
        raise HTTPException(status_code=404, detail="No StockX credentials found in database")

    credential_count = len(configs)
    current_time = datetime.utcnow()

    # Update timestamps using raw SQL for efficiency
    await db.execute(
        text(
            """
            UPDATE core.system_config
            SET updated_at = :now
            WHERE key LIKE 'stockx%'
        """
        ),
        {"now": current_time},
    )

    await db.commit()

    logger.info(
        "Successfully updated StockX credentials timestamps",
        credential_count=credential_count,
        new_timestamp=current_time.isoformat(),
    )

    # Verify update
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key.like("stockx%")).order_by(SystemConfig.key)
    )
    updated_configs = result.scalars().all()

    return {
        "status": "success",
        "message": f"Updated {credential_count} StockX credential timestamps",
        "updated_at": current_time.isoformat(),
        "credentials": [
            {"key": config.key, "updated_at": config.updated_at.isoformat()}
            for config in updated_configs
        ],
    }
