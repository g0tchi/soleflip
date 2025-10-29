"""
Unified Supplier API Router
Comprehensive API for managing suppliers, accounts, and business intelligence.
"""

import os
import tempfile
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import (APIRouter, Depends, File, HTTPException, Query, Request,
                     UploadFile, status)
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from domains.suppliers.services.supplier_service import SupplierService

from shared.api.dependencies import get_db_session, ResponseFormatter
from shared.security.api_security import AuditLogger, get_client_ip

# Initialize loggers and utilities
logger = structlog.get_logger(__name__)
audit_logger = AuditLogger()
router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


# region Response Models
class SupplierCreateResponse(BaseModel):
    supplier_id: str
    name: str
    category: str
    message: str


class SupplierPerformanceMetrics(BaseModel):
    total_orders: int
    avg_delivery_time: float
    return_rate: float
    avg_roi: float


class SupplierIntelligenceDashboard(BaseModel):
    summary: Dict
    category_distribution: Dict[str, int]
    country_distribution: Dict[str, int]
    top_performers: List[Dict]
    analysis_date: str


class SupplierRecommendation(BaseModel):
    supplier_id: str
    name: str
    category: str
    country: str
    vat_rate: float
    performance_score: float
    avg_roi: float
    recommendation_reason: str


class AccountResponse(BaseModel):
    id: str
    supplier_id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    address_line_1: Optional[str]
    city: Optional[str]
    country_code: Optional[str]
    account_status: str
    is_verified: bool
    total_purchases: int
    total_spent: float
    success_rate: float
    average_order_value: float
    last_used_at: Optional[str]
    created_at: Optional[str]


class AccountStatisticsResponse(BaseModel):
    account_info: Dict
    purchase_statistics: Dict
    performance_metrics: Dict
    usage_patterns: Dict


class SupplierOverviewResponse(BaseModel):
    overview: Dict
    top_performing_accounts: List[Dict]
    recent_activity: Dict
    status_distribution: Dict
    monthly_trends: List[Dict]


class ImportResultResponse(BaseModel):
    total_rows: int
    successful_imports: int
    failed_imports: int
    skipped_rows: int
    duplicate_accounts: int
    errors: List[Dict]
# endregion


# region Request Models
class CreateSupplierRequest(BaseModel):
    name: str = Field(..., description="Supplier name")
    email: Optional[str] = Field(None, description="Default email address")
    vat_rate: Optional[float] = Field(19.0, description="VAT rate percentage")
    return_policy: Optional[str] = Field(None, description="Return policy description")
    contact_person: Optional[str] = Field(None, description="Contact person name")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    address: Optional[str] = Field(None, description="Address")
    city: Optional[str] = Field("Unknown", description="City")
    country: Optional[str] = Field("Germany", description="Country")
    return_days: Optional[int] = Field(14, description="Return policy days")
    payment_terms: Optional[str] = Field("Net 30", description="Payment terms")
    min_order: Optional[float] = Field(50.0, description="Minimum order amount")


class AccountImportRequest(BaseModel):
    supplier_mapping: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of list names to supplier IDs. If not provided, default supplier will be used."
    )
    batch_size: int = Field(
        50,
        ge=1,
        le=500,
        description="Number of accounts to process in each batch"
    )

    @validator('batch_size')
    def validate_batch_size(cls, v):
        if v < 1 or v > 500:
            raise ValueError('Batch size must be between 1 and 500')
        return v
# endregion


# region Dependencies
def get_supplier_service(db: AsyncSession = Depends(get_db_session)) -> SupplierService:
    return SupplierService(db)
# endregion


# region Endpoints

# Supplier Management
@router.post(
    "/",
    response_model=SupplierCreateResponse,
    summary="Create a new supplier",
    tags=["Supplier Management"]
)
async def create_supplier(
    supplier_request: CreateSupplierRequest,
    service: SupplierService = Depends(get_supplier_service)
):
    try:
        supplier_data = supplier_request.dict()
        supplier = await service.create_supplier(supplier_data)
        return SupplierCreateResponse(
            supplier_id=str(supplier.id),
            name=supplier.name,
            category=supplier.supplier_category,
            message=f"Supplier '{supplier.name}' created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create supplier: {str(e)}")


@router.post(
    "/bulk-create-from-notion",
    summary="Bulk create suppliers from Notion analysis",
    tags=["Supplier Management"]
)
async def bulk_create_notion_suppliers(
    service: SupplierService = Depends(get_supplier_service)
):
    try:
        supplier_ids = await service.bulk_create_notion_suppliers()
        return ResponseFormatter.format_success_response(
            f"Successfully created/verified {len(supplier_ids)} suppliers",
            {"created_supplier_ids": [str(sid) for sid in supplier_ids]},
            "bulk_supplier_creation"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk create suppliers: {str(e)}")


# Account Management
@router.post(
    "/accounts/import-csv",
    response_model=ImportResultResponse,
    summary="Import accounts from CSV",
    tags=["Account Management"]
)
async def import_accounts_from_csv(
    file: UploadFile = File(...),
    request_data: AccountImportRequest = Depends(),
    service: SupplierService = Depends(get_supplier_service),
    client_ip: str = Depends(get_client_ip),
    http_request: Request = None
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV.")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    try:
        supplier_mapping = {k: UUID(v) for k, v in request_data.supplier_mapping.items()} if request_data.supplier_mapping else None
        audit_logger.log_security_event(
            "account_import_attempt", http_request, user_id="system",
            additional_data={"filename": file.filename, "client_ip": client_ip}
        )
        result = await service.import_accounts_from_csv(
            csv_file_path=temp_file_path,
            supplier_mapping=supplier_mapping,
            batch_size=request_data.batch_size
        )
        audit_logger.log_security_event(
            "account_import_completed", http_request, user_id="system",
            additional_data={"successful_imports": result["successful_imports"], "failed_imports": result["failed_imports"]}
        )
        return ImportResultResponse(**result)
    finally:
        os.unlink(temp_file_path)


@router.get(
    "/{supplier_id}/accounts",
    response_model=List[AccountResponse],
    summary="List supplier accounts",
    tags=["Account Management"]
)
async def list_supplier_accounts(
    supplier_id: UUID,
    status: Optional[str] = Query(None, description="Filter by account status"),
    verified_only: bool = Query(False, description="Show only verified accounts"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: SupplierService = Depends(get_supplier_service),
):
    accounts = await service.list_supplier_accounts(
        supplier_id=supplier_id,
        status=status,
        verified_only=verified_only,
        limit=limit,
        offset=offset
    )
    return [AccountResponse(**account.to_dict()) for account in accounts]


@router.post(
    "/accounts/{account_id}/purchase",
    summary="Record account purchase",
    tags=["Account Management"]
)
async def record_account_purchase(
    account_id: UUID,
    purchase_data: Dict,
    service: SupplierService = Depends(get_supplier_service)
):
    if not purchase_data or 'purchase_amount' not in purchase_data:
        raise HTTPException(status_code=400, detail="Purchase amount is required.")

    purchase = await service.record_account_purchase(account_id, purchase_data)
    return {"message": "Purchase recorded successfully", "purchase_id": str(purchase.id)}


# Supplier Intelligence
@router.get(
    "/intelligence/dashboard",
    response_model=SupplierIntelligenceDashboard,
    summary="Get supplier intelligence dashboard",
    tags=["Supplier Intelligence"]
)
async def get_supplier_intelligence_dashboard(
    service: SupplierService = Depends(get_supplier_service)
):
    dashboard = await service.get_supplier_intelligence_dashboard()
    return SupplierIntelligenceDashboard(**dashboard)


@router.get(
    "/intelligence/recommendations",
    response_model=List[SupplierRecommendation],
    summary="Get supplier recommendations",
    tags=["Supplier Intelligence"]
)
async def get_supplier_recommendations(
    category: Optional[str] = Query(None),
    service: SupplierService = Depends(get_supplier_service)
):
    recommendations = await service.get_supplier_recommendations(category)
    return [SupplierRecommendation(**rec) for rec in recommendations]


@router.get(
    "/intelligence/categories",
    summary="Get all supplier categories",
    tags=["Supplier Intelligence"]
)
async def get_supplier_categories(
    service: SupplierService = Depends(get_supplier_service)
):
    return ResponseFormatter.format_success_response(
        "Supplier categories retrieved successfully",
        {"categories": service.SUPPLIER_CATEGORIES}
    )


@router.get(
    "/intelligence/category-analytics/{category}",
    summary="Get analytics for a specific category",
    tags=["Supplier Intelligence"]
)
async def get_category_analytics(
    category: str,
    service: SupplierService = Depends(get_supplier_service)
):
    analytics = await service.get_category_analytics(category)
    return ResponseFormatter.format_success_response(
        f"Category analytics for '{category}' retrieved",
        analytics, "category_analytics"
    )


# Statistics and Health
@router.get(
    "/{supplier_id}/overview",
    response_model=SupplierOverviewResponse,
    summary="Get supplier account overview",
    tags=["Statistics"]
)
async def get_supplier_account_overview(
    supplier_id: UUID,
    service: SupplierService = Depends(get_supplier_service),
):
    overview = await service.get_supplier_account_overview(supplier_id)
    return SupplierOverviewResponse(**overview)


@router.get(
    "/accounts/{account_id}/statistics",
    response_model=AccountStatisticsResponse,
    summary="Get detailed account statistics",
    tags=["Statistics"]
)
async def get_account_statistics(
    account_id: UUID,
    service: SupplierService = Depends(get_supplier_service),
):
    try:
        stats = await service.get_account_detailed_statistics(account_id)
        return AccountStatisticsResponse(**stats)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/accounts/recalculate-statistics",
    summary="Recalculate account statistics",
    tags=["Statistics"]
)
async def recalculate_account_statistics(
    supplier_id: Optional[UUID] = Query(None),
    service: SupplierService = Depends(get_supplier_service),
    http_request: Request = None,
    client_ip: str = Depends(get_client_ip)
):
    audit_logger.log_security_event(
        "statistics_recalculation_attempt", http_request, user_id="system",
        additional_data={"supplier_id": str(supplier_id) if supplier_id else "all", "client_ip": client_ip}
    )
    result = await service.recalculate_all_account_statistics(supplier_id)
    audit_logger.log_security_event(
        "statistics_recalculation_completed", http_request, user_id="system",
        additional_data={"updated_count": result["updated_count"], "failed_count": result["failed_count"]}
    )
    return result


@router.get(
    "/health",
    summary="Service health check",
    tags=["Health"]
)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import text
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "service": "supplier_service"}
    except Exception as e:
        logger.error("Supplier service health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

# endregion
