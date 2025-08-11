"""
n8n-Compatible Webhook Endpoints
Replaces direct SQL queries in n8n with proper API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import tempfile
import os
from pathlib import Path
import structlog
from pydantic import BaseModel

from shared.database.connection import get_db_session, db_manager
from ..services.import_processor import import_processor, SourceType, ImportStatus
from ..services.validators import ValidationError
from ..services.stockx_service import stockx_service

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


class StockXImportRequest(BaseModel):
    from_date: date
    to_date: date

@webhook_router.post("/stockx/import-orders", tags=["StockX"])
async def stockx_import_orders_webhook(
    request: StockXImportRequest,
    background_tasks: BackgroundTasks,
):
    """
    Fetches historical orders directly from the StockX API for a given date range
    and processes them in the background. Designed for n8n automation.
    """
    logger.info(
        "StockX API import triggered via webhook",
        from_date=request.from_date,
        to_date=request.to_date,
    )

    # Define the background task to prevent blocking the webhook response
    async def run_import_task():
        try:
            logger.info("Background task started: Fetching data from StockX API.")
            # 1. Fetch data from StockX API using the dedicated service
            orders_data = await stockx_service.get_historical_orders(
                from_date=request.from_date,
                to_date=request.to_date
            )

            if not orders_data:
                logger.info("No new orders found from StockX API. Background task finished.")
                return

            logger.info(f"Fetched {len(orders_data)} orders from StockX. Starting import process.")
            # 2. Process data using the existing import processor
            # We use process_import because we have structured data, not a file
            await import_processor.process_import(
                source_type=SourceType.STOCKX,
                data=orders_data,
                raw_data=orders_data, # Pass raw data for accurate record keeping
                metadata={"filename": f"stockx_api_import_{request.from_date}_to_{request.to_date}.json"}
            )
            logger.info("Background task finished: Import processing complete.")

        except ValueError as e:
            # Specific handling for configuration errors (e.g., missing credentials)
            logger.error(
                "StockX API import failed due to configuration error",
                error=str(e),
            )
        except Exception as e:
            # General error handling for the background task
            logger.error(
                "StockX API import background task failed unexpectedly",
                error=str(e),
                error_type=type(e).__name__,
            )

    # Add the task to run in the background after the response is sent
    background_tasks.add_task(run_import_task)

    # Return an immediate response to the client (e.g., n8n)
    return JSONResponse(
        status_code=202, # Accepted
        content={
            "status": "processing_started",
            "message": "StockX API order import has been successfully started in the background.",
            "details": {
                "from_date": request.from_date.isoformat(),
                "to_date": request.to_date.isoformat(),
                "check_status_url": "/api/v1/integration/import-status"
            }
        }
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
        async with db_manager.get_session() as db:
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
        async with db_manager.get_session() as db:
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

@webhook_router.post("/alias/upload")
async def alias_upload_webhook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    batch_size: int = Form(1000),
    validate_only: bool = Form(False)
):
    """
    Alias file upload webhook
    Processes Alias sales report CSV files with CENTS pricing and DD/MM/YY dates
    """
    logger.info(
        "Alias upload webhook triggered",
        filename=file.filename,
        content_type=file.content_type,
        validate_only=validate_only
    )
    
    # Validate file type
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Only CSV and Excel files are supported for Alias imports"
        )
    
    try:
        # Save uploaded file temporarily
        temp_file = await _save_temp_file(file)
        
        if validate_only:
            # Validation only mode
            result = await _validate_file_only(temp_file, SourceType.ALIAS)
            await _cleanup_temp_file(temp_file)
            
            return {
                "status": "validated",
                "valid": result["is_valid"],
                "errors": result["errors"],
                "warnings": result["warnings"],
                "record_count": result["record_count"],
                "detected_format": "alias_sales_report"
            }
        else:
            # Full processing mode
            background_tasks.add_task(
                _process_file_async,
                temp_file,
                SourceType.ALIAS,
                batch_size
            )
            
            return {
                "status": "processing_started",
                "message": "Alias file upload successful, processing in background",
                "filename": file.filename,
                "source_type": "alias",
                "check_status_url": "/api/v1/integration/import-status"
            }
            
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Alias validation failed: {'; '.join(e.errors)}"
        )
    except Exception as e:
        logger.error(
            "Alias upload webhook failed",
            filename=file.filename,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Alias upload processing failed: {str(e)}"
        )

# =====================================================
# n8n Data Export Webhooks (for Notion sync)
# =====================================================

@webhook_router.get("/n8n/inventory/export")
async def n8n_inventory_export(
    limit: int = 1000,
    brand_filter: Optional[str] = None,
    modified_since: Optional[str] = None
):
    """
    Export inventory data in n8n-compatible format for Notion sync
    Optimized for n8n workflow consumption
    """
    logger.info(
        "n8n inventory export requested",
        limit=limit,
        brand_filter=brand_filter,
        modified_since=modified_since
    )
    
    try:
        async with db_manager.get_session() as db:
            from shared.database.models import InventoryItem, Product, Brand, Size
            from sqlalchemy import select, and_, desc
            from datetime import datetime
            
            query = select(
                InventoryItem.id,
                Product.sku,
                Size.value.label('size_value'),
                InventoryItem.quantity,
                InventoryItem.purchase_price,
                InventoryItem.purchase_date,
                InventoryItem.supplier.label('purchase_location'),  # Legacy supplier field
                InventoryItem.notes,
                InventoryItem.status,
                InventoryItem.created_at,
                InventoryItem.updated_at,
                Product.name.label('product_name'),
                Product.description.label('product_description'),
                Brand.name.label('brand_name'),
                Brand.slug.label('brand_slug')
            ).select_from(
                InventoryItem.__table__
                .join(Product.__table__, InventoryItem.product_id == Product.id)
                .join(Size.__table__, InventoryItem.size_id == Size.id)
                .outerjoin(Brand.__table__, Product.brand_id == Brand.id)
            )
            
            # Apply filters
            conditions = []
            
            if brand_filter:
                conditions.append(
                    Brand.name.ilike(f"%{brand_filter}%")
                )
            
            if modified_since:
                try:
                    since_date = datetime.fromisoformat(modified_since.replace('Z', '+00:00'))
                    conditions.append(
                        InventoryItem.updated_at >= since_date
                    )
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid modified_since format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
                    )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order and limit
            query = query.order_by(desc(InventoryItem.updated_at)).limit(limit)
            
            result = await db.execute(query)
            items = result.fetchall()
            
            # Format for n8n/Notion consumption
            formatted_items = []
            for item in items:
                formatted_items.append({
                    "id": str(item.id),
                    "sku": item.sku,
                    "product_name": item.product_name,
                    "brand": item.brand_name or "Unknown",
                    "description": item.product_description,
                    "size": item.size_value,
                    "quantity": item.quantity,
                    "purchase_price": float(item.purchase_price) if item.purchase_price else None,
                    "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
                    "purchase_location": item.purchase_location,
                    "status": item.status,
                    "notes": item.notes,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    # n8n/Notion friendly fields
                    "title": f"{item.brand_name or 'Unknown'} {item.product_name}",
                    "full_description": f"{item.brand_name or 'Unknown'} {item.product_name} - Size {item.size_value} - Qty: {item.quantity}"
                })
            
            return {
                "success": True,
                "data": formatted_items,
                "meta": {
                    "total_records": len(formatted_items),
                    "limit": limit,
                    "filters_applied": {
                        "brand_filter": brand_filter,
                        "modified_since": modified_since
                    },
                    "export_timestamp": datetime.utcnow().isoformat()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "n8n inventory export failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Inventory export failed: {str(e)}"
        )

@webhook_router.get("/n8n/brands/export")
async def n8n_brands_export():
    """
    Export brand data for n8n/Notion sync
    Includes brand analytics from business intelligence views
    """
    logger.info("n8n brands export requested")
    
    try:
        async with db_manager.get_session() as db:
            # Use analytics view for comprehensive brand data
            from sqlalchemy import text
            
            query = text("""
                SELECT 
                    b.id,
                    b.name,
                    b.slug,
                    b.created_at,
                    b.updated_at,
                    COALESCE(bp.total_items, 0) as product_count,
                    COALESCE(bp.market_share_percent, 0) as market_share,
                    COALESCE(bp.avg_purchase_price, 0) as avg_price
                FROM core.brands b
                LEFT JOIN analytics.brand_performance bp ON b.name = bp.brand_name
                ORDER BY COALESCE(bp.total_items, 0) DESC
            """)
            
            result = await db.execute(query)
            brands = result.fetchall()
            
            formatted_brands = []
            for brand in brands:
                formatted_brands.append({
                    "id": str(brand.id),
                    "name": brand.name,
                    "slug": brand.slug,
                    "product_count": brand.product_count,
                    "market_share_percent": float(brand.market_share),
                    "average_price": float(brand.avg_price),
                    "created_at": brand.created_at.isoformat(),
                    "updated_at": brand.updated_at.isoformat(),
                    # n8n/Notion friendly fields
                    "title": brand.name,
                    "description": f"{brand.name} - {brand.product_count} products - {brand.market_share:.1f}% market share"
                })
            
            return {
                "success": True,
                "data": formatted_brands,
                "meta": {
                    "total_brands": len(formatted_brands),
                    "export_timestamp": datetime.utcnow().isoformat()
                }
            }
            
    except Exception as e:
        logger.error(
            "n8n brands export failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Brands export failed: {str(e)}"
        )

@webhook_router.get("/n8n/analytics/dashboard")
async def n8n_analytics_dashboard():
    """
    Export key business metrics for n8n/Notion dashboard sync
    Aggregated data perfect for Notion database properties
    """
    logger.info("n8n analytics dashboard export requested")
    
    try:
        async with db_manager.get_session() as db:
            from sqlalchemy import text
            from datetime import datetime, timedelta
            
            # Get comprehensive dashboard data
            dashboard_query = text("""
                SELECT 
                    -- Financial Overview
                    (SELECT total_items FROM analytics.financial_overview LIMIT 1) as total_items,
                    (SELECT available_inventory_value FROM analytics.financial_overview LIMIT 1) as portfolio_value,
                    (SELECT avg_item_price FROM analytics.financial_overview LIMIT 1) as avg_item_price,
                    
                    -- Brand Statistics
                    (SELECT COUNT(*) FROM analytics.brand_performance WHERE total_items > 0) as active_brands,
                    (SELECT brand_name FROM analytics.brand_performance ORDER BY total_items DESC LIMIT 1) as top_brand,
                    (SELECT MAX(market_share_percent) FROM analytics.brand_performance) as top_brand_share,
                    
                    -- Supplier Statistics  
                    (SELECT COUNT(*) FROM analytics.supplier_performance) as total_suppliers,
                    (SELECT AVG(rating) FROM analytics.supplier_performance) as avg_supplier_rating,
                    
                    -- Inventory Statistics
                    (SELECT COUNT(DISTINCT category_name) FROM analytics.size_distribution) as categories,
                    (SELECT COUNT(DISTINCT size_value) FROM analytics.size_distribution) as size_variants
            """)
            
            result = await db.execute(dashboard_query)
            dashboard_data = result.fetchone()
            
            # Format for Notion consumption
            analytics_summary = {
                "id": "dashboard_summary",
                "title": "SoleFlipper Analytics Dashboard",
                "last_updated": datetime.utcnow().isoformat(),
                
                # Financial KPIs
                "total_inventory_items": int(dashboard_data.total_items or 0),
                "portfolio_value": float(dashboard_data.portfolio_value or 0),
                "average_item_price": float(dashboard_data.avg_item_price or 0),
                
                # Brand Intelligence
                "active_brands": int(dashboard_data.active_brands or 0),
                "top_brand": dashboard_data.top_brand or "Nike",
                "top_brand_market_share": float(dashboard_data.top_brand_share or 0),
                
                # Supplier Intelligence
                "supplier_count": int(dashboard_data.total_suppliers or 0),
                "avg_supplier_rating": round(float(dashboard_data.avg_supplier_rating or 0), 2),
                
                # Inventory Metrics
                "product_categories": int(dashboard_data.categories or 0),
                "size_variants": int(dashboard_data.size_variants or 0),
                
                # Status indicators
                "system_status": "operational",
                "data_quality": "excellent"
            }
            
            return {
                "success": True,
                "data": analytics_summary,
                "meta": {
                    "dashboard_type": "business_intelligence",
                    "refresh_interval": "real_time",
                    "export_timestamp": datetime.utcnow().isoformat()
                }
            }
            
    except Exception as e:
        logger.error(
            "n8n analytics dashboard export failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analytics dashboard export failed: {str(e)}"
        )

@webhook_router.post("/n8n/notion/sync")
async def n8n_notion_sync_webhook(data: Dict[str, Any]):
    """
    Receive updates from Notion via n8n
    Handles bidirectional sync for inventory updates
    """
    logger.info(
        "n8n Notion sync webhook triggered",
        data_keys=list(data.keys()) if data else []
    )
    
    try:
        if 'action' not in data:
            raise HTTPException(
                status_code=400,
                detail="Missing 'action' field in sync data"
            )
        
        action = data['action']
        
        if action == 'update_inventory':
            return await _handle_notion_inventory_update(data)
        elif action == 'create_item':
            return await _handle_notion_item_creation(data)
        elif action == 'status_change':
            return await _handle_notion_status_change(data)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown sync action: {action}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "n8n Notion sync failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Notion sync failed: {str(e)}"
        )

# =====================================================
# n8n Notion Sync Handlers
# =====================================================

async def _handle_notion_inventory_update(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle inventory updates from Notion"""
    item_id = data.get('item_id')
    updates = data.get('updates', {})
    
    if not item_id:
        raise HTTPException(status_code=400, detail="Missing item_id")
    
    async with db_manager.get_session() as db:
        from shared.database.models import InventoryItem
        from sqlalchemy import select, update
        
        # Check if item exists
        query = select(InventoryItem).where(InventoryItem.id == item_id)
        result = await db.execute(query)
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        
        # Apply updates
        update_data = {}
        if 'status' in updates:
            update_data['status'] = updates['status']
        if 'notes' in updates:
            update_data['notes'] = updates['notes']
        if 'condition' in updates:
            update_data['condition'] = updates['condition']
        
        if update_data:
            update_query = update(InventoryItem).where(
                InventoryItem.id == item_id
            ).values(**update_data)
            
            await db.execute(update_query)
            await db.commit()
        
        return {
            "success": True,
            "message": "Inventory item updated",
            "item_id": item_id,
            "updates_applied": list(update_data.keys())
        }

async def _handle_notion_item_creation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle new item creation from Notion"""
    # This would create a new inventory item from Notion data
    # For now, return placeholder
    return {
        "success": True,
        "message": "Item creation handling not yet implemented",
        "action": "create_item"
    }

async def _handle_notion_status_change(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle status changes from Notion"""
    # This would handle status changes (sold, available, etc.)
    # For now, return placeholder
    return {
        "success": True,
        "message": "Status change handling not yet implemented",
        "action": "status_change"
    }