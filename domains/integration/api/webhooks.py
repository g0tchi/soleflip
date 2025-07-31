"""
n8n-Compatible Webhook Endpoints
Replaces direct SQL queries in n8n with proper API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import tempfile
import os
from pathlib import Path
import structlog

from shared.database.connection import get_db_session
from ..services.import_processor import import_processor, SourceType, ImportStatus
from ..services.validators import ValidationError

logger = structlog.get_logger(__name__)

webhook_router = APIRouter()

# =====================================================
# File Upload Webhooks (replaces direct SQL inserts)
# =====================================================

@webhook_router.post("/stockx/upload")
async def stockx_upload_webhook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    batch_size: int = Form(1000),
    validate_only: bool = Form(False)
):
    """
    StockX file upload webhook
    Replaces the broken n8n workflow that tried to insert into non-existent tables
    """
    logger.info(
        "StockX upload webhook triggered",
        filename=file.filename,
        content_type=file.content_type,
        validate_only=validate_only
    )
    
    # Validate file type
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Only CSV and Excel files are supported for StockX imports"
        )
    
    try:
        # Save uploaded file temporarily
        temp_file = await _save_temp_file(file)
        
        if validate_only:
            # Validation only mode
            result = await _validate_file_only(temp_file, SourceType.STOCKX)
            await _cleanup_temp_file(temp_file)
            
            return {
                "status": "validated",
                "valid": result["is_valid"],
                "errors": result["errors"],
                "warnings": result["warnings"],
                "record_count": result["record_count"]
            }
        else:
            # Full processing mode
            background_tasks.add_task(
                _process_file_async,
                temp_file,
                SourceType.STOCKX,
                batch_size
            )
            
            return {
                "status": "processing_started",
                "message": "File upload successful, processing in background",
                "filename": file.filename,
                "check_status_url": "/api/v1/integration/import-status"
            }
            
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {'; '.join(e.errors)}"
        )
    except Exception as e:
        logger.error(
            "StockX upload webhook failed",
            filename=file.filename,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Upload processing failed: {str(e)}"
        )

@webhook_router.post("/notion/import")
async def notion_import_webhook(
    background_tasks: BackgroundTasks,
    data: Dict[str, Any],
    batch_size: int = 1000
):
    """
    Notion data import webhook (for n8n Notion API integration)
    Accepts JSON payload directly from Notion API
    """
    logger.info(
        "Notion import webhook triggered",
        data_type=type(data).__name__,
        has_results=bool(data.get('results'))
    )
    
    try:
        # Extract results from Notion API response
        if 'results' not in data:
            raise HTTPException(
                status_code=400,
                detail="Invalid Notion API response: missing 'results' field"
            )
        
        results = data['results']
        if not isinstance(results, list):
            raise HTTPException(
                status_code=400,
                detail="Invalid Notion API response: 'results' must be an array"
            )
        
        if len(results) == 0:
            return {
                "status": "completed",
                "message": "No records to import",
                "record_count": 0
            }
        
        # Create temporary JSON file for processing
        temp_file = await _create_temp_json_file(results)
        
        # Process asynchronously
        background_tasks.add_task(
            _process_file_async,
            temp_file,
            SourceType.NOTION,
            batch_size
        )
        
        return {
            "status": "processing_started",
            "message": "Notion data import started",
            "record_count": len(results),
            "check_status_url": "/api/v1/integration/import-status"
        }
        
    except Exception as e:
        logger.error(
            "Notion import webhook failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Notion import failed: {str(e)}"
        )

@webhook_router.post("/manual/upload")
async def manual_upload_webhook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("auto"),
    batch_size: int = Form(1000)
):
    """
    Manual file upload webhook (for any CSV/Excel file)
    Auto-detects source type or accepts explicit type
    """
    logger.info(
        "Manual upload webhook triggered",
        filename=file.filename,
        source_type=source_type,
        content_type=file.content_type
    )
    
    try:
        # Save uploaded file temporarily
        temp_file = await _save_temp_file(file)
        
        # Determine source type
        if source_type == "auto":
            detected_source = None  # Will auto-detect during processing
        else:
            try:
                detected_source = SourceType(source_type.lower())
            except ValueError:
                await _cleanup_temp_file(temp_file)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source type: {source_type}"
                )
        
        # Process asynchronously
        background_tasks.add_task(
            _process_file_async,
            temp_file,
            detected_source,
            batch_size
        )
        
        return {
            "status": "processing_started",
            "message": "File upload successful, processing in background",
            "filename": file.filename,
            "source_type": source_type,
            "check_status_url": "/api/v1/integration/import-status"
        }
        
    except Exception as e:
        logger.error(
            "Manual upload webhook failed",
            filename=file.filename,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Upload processing failed: {str(e)}"
        )

# =====================================================
# Status and Monitoring Webhooks
# =====================================================

@webhook_router.get("/import-status")
async def get_recent_import_status():
    """
    Get status of recent imports (for n8n monitoring)
    """
    try:
        async with get_db_session() as db:
            # Get recent import batches (last 24 hours)
            from shared.database.models import ImportBatch
            from sqlalchemy import select, desc
            from datetime import datetime, timedelta
            
            since = datetime.utcnow() - timedelta(hours=24)
            
            query = select(ImportBatch).where(
                ImportBatch.created_at >= since
            ).order_by(desc(ImportBatch.created_at)).limit(20)
            
            result = await db.execute(query)
            batches = result.scalars().all()
            
            status_data = []
            for batch in batches:
                status_data.append({
                    "batch_id": str(batch.id),
                    "source_type": batch.source_type,
                    "source_file": batch.source_file,
                    "status": batch.status,
                    "total_records": batch.total_records,
                    "processed_records": batch.processed_records,
                    "error_records": batch.error_records,
                    "started_at": batch.started_at.isoformat() if batch.started_at else None,
                    "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                    "processing_time_seconds": (
                        (batch.completed_at - batch.started_at).total_seconds()
                        if batch.started_at and batch.completed_at else None
                    )
                })
            
            # Summary statistics
            total_batches = len(batches)
            completed_batches = len([b for b in batches if b.status == ImportStatus.COMPLETED.value])
            failed_batches = len([b for b in batches if b.status == ImportStatus.FAILED.value])
            processing_batches = len([b for b in batches if b.status == ImportStatus.PROCESSING.value])
            
            return {
                "summary": {
                    "total_batches": total_batches,
                    "completed": completed_batches,
                    "failed": failed_batches,
                    "processing": processing_batches,
                    "success_rate": (completed_batches / total_batches * 100) if total_batches > 0 else 0
                },
                "recent_imports": status_data
            }
            
    except Exception as e:
        logger.error(
            "Failed to get import status",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get import status: {str(e)}"
        )

@webhook_router.get("/import-status/{batch_id}")
async def get_import_batch_status(batch_id: str):
    """
    Get detailed status of a specific import batch
    """
    try:
        async with get_db_session() as db:
            from shared.database.models import ImportBatch, ImportRecord
            from sqlalchemy import select, func
            
            # Get batch info
            batch_query = select(ImportBatch).where(ImportBatch.id == batch_id)
            batch_result = await db.execute(batch_query)
            batch = batch_result.scalar_one_or_none()
            
            if not batch:
                raise HTTPException(status_code=404, detail="Import batch not found")
            
            # Get record details
            record_query = select(
                func.count(ImportRecord.id).label('total_records'),
                func.count(ImportRecord.id).filter(ImportRecord.processed == True).label('processed'),
                func.count(ImportRecord.id).filter(ImportRecord.error_message != None).label('errors')
            ).where(ImportRecord.batch_id == batch_id)
            
            record_result = await db.execute(record_query)
            record_stats = record_result.fetchone()
            
            return {
                "batch_id": str(batch.id),
                "source_type": batch.source_type,
                "source_file": batch.source_file,
                "status": batch.status,
                "started_at": batch.started_at.isoformat() if batch.started_at else None,
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                "processing_time_seconds": (
                    (batch.completed_at - batch.started_at).total_seconds()
                    if batch.started_at and batch.completed_at else None
                ),
                "records": {
                    "total": record_stats.total_records,
                    "processed": record_stats.processed,
                    "errors": record_stats.errors,
                    "success_rate": (
                        record_stats.processed / record_stats.total_records * 100
                        if record_stats.total_records > 0 else 0
                    )
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get batch status",
            batch_id=batch_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch status: {str(e)}"
        )

# =====================================================
# Helper Functions
# =====================================================

async def _save_temp_file(file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    suffix = Path(file.filename).suffix if file.filename else '.tmp'
    
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name

async def _create_temp_json_file(data: List[Dict]) -> str:
    """Create temporary JSON file from data"""
    import json
    
    with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as tmp:
        json.dump(data, tmp, indent=2)
        return tmp.name

async def _cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        os.unlink(file_path)
    except OSError:
        pass  # File might already be deleted

async def _validate_file_only(file_path: str, source_type: SourceType) -> Dict[str, Any]:
    """Validate file without importing"""
    # This would use our validators to check the file
    # For now, return a placeholder
    return {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "record_count": 0
    }

async def _process_file_async(file_path: str, source_type: Optional[SourceType], batch_size: int):
    """Background task for file processing"""
    try:
        result = await import_processor.process_file(
            file_path=file_path,
            source_type=source_type,
            batch_size=batch_size
        )
        
        logger.info(
            "Background file processing completed",
            batch_id=result.batch_id,
            status=result.status.value,
            processed_records=result.processed_records,
            error_records=result.error_records
        )
        
    except Exception as e:
        logger.error(
            "Background file processing failed",
            file_path=file_path,
            error=str(e),
            error_type=type(e).__name__
        )
    finally:
        # Clean up temporary file
        await _cleanup_temp_file(file_path)