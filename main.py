"""
SoleFlipper API - Main Application Entry Point
Production-ready FastAPI application with proper error handling,
logging, and monitoring.
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import pandas as pd
import io
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

from shared.database.connection import get_db_session, db_manager
from domains.integration.services.import_processor import ImportProcessor, SourceType
from domains.inventory.services.inventory_service import InventoryService

# Dependency provider functions
def get_import_processor(db: AsyncSession = Depends(get_db_session)) -> ImportProcessor:
    return ImportProcessor(db)

def get_inventory_service(db: AsyncSession = Depends(get_db_session)) -> InventoryService:
    return InventoryService(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] SoleFlipper API starting up...")
    await db_manager.initialize()
    await db_manager.run_migrations()
    print("[SUCCESS] Database connection initialized and tables created")
    yield
    print("[SHUTDOWN] SoleFlipper API shutting down...")
    await db_manager.close()
    print("[SUCCESS] Database connections closed")

class APIInfo(BaseModel):
    name: str
    version: str

app = FastAPI(
    title="SoleFlipper API",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
from domains.integration.api.webhooks import router as webhook_router
from domains.orders.api.router import router as orders_router
app.include_router(webhook_router, prefix="/api/v1/integration", tags=["Integration"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])


@app.get("/", response_model=APIInfo, tags=["System"])
async def root():
    return APIInfo(name="SoleFlipper API", version="2.1.0")

class UploadResponse(BaseModel):
    filename: str
    total_records: int
    validation_errors: List[str]
    status: str
    message: str
    imported: Optional[bool] = None
    batch_id: Optional[str] = None

@app.post("/api/v1/integration/webhooks/stockx/upload", response_model=UploadResponse, tags=["StockX Integration"])
async def upload_stockx_file(
    file: UploadFile = File(...),
    validate_only: bool = Form(False),
    batch_size: int = Form(1000),
    import_processor: ImportProcessor = Depends(get_import_processor)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8-sig')))

    raw_csv_data = df.to_dict('records')

    import_result = await import_processor.process_import(
        source_type=SourceType.STOCKX,
        data=raw_csv_data,
        metadata={'filename': file.filename, 'batch_size': batch_size},
        raw_data=raw_csv_data
    )

    return UploadResponse(
        filename=file.filename,
        total_records=import_result.total_records,
        validation_errors=import_result.validation_errors,
        status=import_result.status.value,
        message=f"Processed {import_result.processed_records} records.",
        imported=not validate_only,
        batch_id=import_result.batch_id
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)