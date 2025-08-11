"""
n8n-Compatible Webhook Endpoints
Replaces direct SQL queries in n8n with proper API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import date
import tempfile
import os
from pathlib import Path
import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from ..services.import_processor import ImportProcessor, SourceType
from ..services.validators import ValidationError
from ..services.stockx_service import StockXService

logger = structlog.get_logger(__name__)

router = APIRouter()

# Dependency provider functions
def get_import_processor(db: AsyncSession = Depends(get_db_session)) -> ImportProcessor:
    return ImportProcessor(db)

def get_stockx_service(db: AsyncSession = Depends(get_db_session)) -> StockXService:
    return StockXService(db)

class StockXImportRequest(BaseModel):
    from_date: date
    to_date: date

@router.post("/stockx/import-orders", tags=["StockX Integration"])
async def stockx_import_orders_webhook(
    request: StockXImportRequest,
    background_tasks: BackgroundTasks,
    stockx_service: StockXService = Depends(get_stockx_service),
    import_processor: ImportProcessor = Depends(get_import_processor)
):
    logger.info("StockX API import triggered via webhook", from_date=request.from_date, to_date=request.to_date)

    async def run_import_task():
        try:
            orders_data = await stockx_service.get_historical_orders(from_date=request.from_date, to_date=request.to_date)
            if not orders_data:
                logger.info("No new orders found from StockX API.")
                return

            await import_processor.process_import(
                source_type=SourceType.STOCKX,
                data=orders_data,
                raw_data=orders_data,
                metadata={"filename": f"stockx_api_import_{request.from_date}_to_{request.to_date}.json"}
            )
        except Exception as e:
            logger.error("StockX API import background task failed", error=str(e))

    background_tasks.add_task(run_import_task)

    return JSONResponse(
        status_code=202,
        content={"status": "processing_started"}
    )