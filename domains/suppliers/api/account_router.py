"""
Supplier Account Management API Router
Comprehensive API for managing supplier accounts with statistics and import functionality
"""

import os
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Request
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.api.dependencies import get_db_session
from shared.auth.dependencies import require_authenticated_user
from shared.auth.models import User
from shared.security.api_security import get_client_ip, AuditLogger

from domains.suppliers.services.account_import_service import AccountImportService
from domains.suppliers.services.account_statistics_service import AccountStatisticsService

logger = structlog.get_logger(__name__)
audit_logger = AuditLogger()

router = APIRouter()


# Request/Response Models
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


# Dependency functions
def get_account_import_service(db: AsyncSession = Depends(get_db_session)) -> AccountImportService:
    """Dependency to get account import service"""
    return AccountImportService(db)


def get_account_statistics_service(db: AsyncSession = Depends(get_db_session)) -> AccountStatisticsService:
    """Dependency to get account statistics service"""
    return AccountStatisticsService(db)


# API Endpoints
@router.post(
    "/import-csv",
    response_model=ImportResultResponse,
    summary="Import accounts from CSV file",
    description="Import supplier accounts from CSV file with batch processing and error handling"
)
async def import_accounts_from_csv(
    file: UploadFile = File(..., description="CSV file containing account data"),
    request_data: AccountImportRequest = Depends(),
    import_service: AccountImportService = Depends(get_account_import_service),
    user: User = Depends(require_authenticated_user),
    client_ip: str = Depends(get_client_ip),
    http_request: Request = None
):
    """Import accounts from CSV file"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise ValidationError("File must be a CSV file", field="file")

        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Convert supplier mapping from names to UUIDs if provided
            supplier_mapping = None
            if request_data.supplier_mapping:
                supplier_mapping = {
                    k: UUID(v) for k, v in request_data.supplier_mapping.items()
                }

            # Audit log the import attempt
            audit_logger.log_security_event(
                "account_import_attempt",
                http_request,
                user_id=str(user.id),
                additional_data={
                    "filename": file.filename,
                    "file_size": len(content),
                    "batch_size": request_data.batch_size,
                    "client_ip": client_ip
                }
            )

            # Import accounts
            result = await import_service.import_accounts_from_csv(
                csv_file_path=temp_file_path,
                supplier_mapping=supplier_mapping,
                batch_size=request_data.batch_size
            )

            # Audit log success
            audit_logger.log_security_event(
                "account_import_completed",
                http_request,
                user_id=str(user.id),
                additional_data={
                    "successful_imports": result["successful_imports"],
                    "failed_imports": result["failed_imports"],
                    "total_rows": result["total_rows"]
                }
            )

            return ImportResultResponse(**result)

        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "Failed to import accounts from CSV",
            user_id=str(user.id),
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import accounts from CSV file"
        )


@router.get(
    "/suppliers/{supplier_id}/overview",
    response_model=SupplierOverviewResponse,
    summary="Get supplier account overview",
    description="Get comprehensive overview of all accounts for a specific supplier with statistics"
)
async def get_supplier_account_overview(
    supplier_id: UUID,
    statistics_service: AccountStatisticsService = Depends(get_account_statistics_service),
    user: User = Depends(require_authenticated_user)
):
    """Get comprehensive overview of supplier accounts"""
    try:
        overview = await statistics_service.get_supplier_account_overview(supplier_id)
        return SupplierOverviewResponse(**overview)

    except Exception as e:
        logger.error(
            "Failed to get supplier account overview",
            user_id=str(user.id),
            supplier_id=str(supplier_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supplier account overview"
        )


@router.get(
    "/accounts/{account_id}/statistics",
    response_model=AccountStatisticsResponse,
    summary="Get detailed account statistics",
    description="Get detailed statistics and performance metrics for a specific account"
)
async def get_account_statistics(
    account_id: UUID,
    statistics_service: AccountStatisticsService = Depends(get_account_statistics_service),
    user: User = Depends(require_authenticated_user)
):
    """Get detailed statistics for a specific account"""
    try:
        stats = await statistics_service.get_account_detailed_statistics(account_id)
        return AccountStatisticsResponse(**stats)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to get account statistics",
            user_id=str(user.id),
            account_id=str(account_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account statistics"
        )


@router.get(
    "/suppliers/{supplier_id}/accounts",
    response_model=List[AccountResponse],
    summary="List supplier accounts",
    description="Get paginated list of accounts for a specific supplier with filtering options"
)
async def list_supplier_accounts(
    supplier_id: UUID,
    status: Optional[str] = Query(None, description="Filter by account status"),
    verified_only: bool = Query(False, description="Show only verified accounts"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_authenticated_user)
):
    """List accounts for a specific supplier"""
    try:
        from sqlalchemy import select
        from shared.database.models import SupplierAccount

        query = select(SupplierAccount).where(SupplierAccount.supplier_id == supplier_id)

        # Apply filters
        if status:
            query = query.where(SupplierAccount.account_status == status)

        if verified_only:
            query = query.where(SupplierAccount.is_verified)

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        accounts = result.scalars().all()

        return [AccountResponse(**account.to_dict()) for account in accounts]

    except Exception as e:
        logger.error(
            "Failed to list supplier accounts",
            user_id=str(user.id),
            supplier_id=str(supplier_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supplier accounts"
        )


@router.post(
    "/accounts/{account_id}/purchase",
    summary="Record account purchase",
    description="Record a purchase transaction for an account to update statistics"
)
async def record_account_purchase(
    account_id: UUID,
    purchase_data: Dict = None,
    import_service: AccountImportService = Depends(get_account_import_service),
    user: User = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Record a purchase for an account and update statistics"""
    try:
        from shared.database.models import AccountPurchaseHistory
        from datetime import datetime

        # Validate purchase data
        if not purchase_data or not purchase_data.get('purchase_amount'):
            raise ValidationError("Purchase amount is required", field="purchase_amount")

        # Create purchase history entry
        purchase = AccountPurchaseHistory(
            account_id=account_id,
            supplier_id=purchase_data.get('supplier_id'),
            product_id=purchase_data.get('product_id'),
            order_reference=purchase_data.get('order_reference'),
            purchase_amount=Decimal(str(purchase_data['purchase_amount'])),
            purchase_date=datetime.utcnow(),
            purchase_status=purchase_data.get('status', 'completed'),
            success=purchase_data.get('success', True),
            failure_reason=purchase_data.get('failure_reason')
        )

        # Save purchase
        from shared.repositories.base_repository import BaseRepository
        purchase_repo = BaseRepository(AccountPurchaseHistory, db)
        await purchase_repo.create(purchase)

        # Update account statistics
        await import_service.update_account_statistics(account_id)

        return {"message": "Purchase recorded successfully", "purchase_id": str(purchase.id)}

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "Failed to record account purchase",
            user_id=str(user.id),
            account_id=str(account_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record account purchase"
        )


@router.post(
    "/accounts/recalculate-statistics",
    summary="Recalculate account statistics",
    description="Recalculate statistics for all accounts or accounts of a specific supplier"
)
async def recalculate_account_statistics(
    supplier_id: Optional[UUID] = Query(None, description="Supplier ID to recalculate (all if not provided)"),
    statistics_service: AccountStatisticsService = Depends(get_account_statistics_service),
    user: User = Depends(require_authenticated_user),
    client_ip: str = Depends(get_client_ip),
    http_request: Request = None
):
    """Recalculate statistics for accounts"""
    try:
        # Audit log the recalculation attempt
        audit_logger.log_security_event(
            "statistics_recalculation_attempt",
            http_request,
            user_id=str(user.id),
            additional_data={
                "supplier_id": str(supplier_id) if supplier_id else "all",
                "client_ip": client_ip
            }
        )

        result = await statistics_service.recalculate_all_account_statistics(supplier_id)

        # Audit log success
        audit_logger.log_security_event(
            "statistics_recalculation_completed",
            http_request,
            user_id=str(user.id),
            additional_data={
                "total_accounts": result["total_accounts"],
                "updated_count": result["updated_count"],
                "failed_count": result["failed_count"]
            }
        )

        return {
            "message": "Statistics recalculation completed",
            "total_accounts": result["total_accounts"],
            "updated_count": result["updated_count"],
            "failed_count": result["failed_count"]
        }

    except Exception as e:
        logger.error(
            "Failed to recalculate account statistics",
            user_id=str(user.id),
            supplier_id=str(supplier_id) if supplier_id else "all",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recalculate account statistics"
        )


@router.get(
    "/import-summary",
    summary="Get import summary",
    description="Get summary statistics of all imported accounts"
)
async def get_import_summary(
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier ID"),
    import_service: AccountImportService = Depends(get_account_import_service),
    user: User = Depends(require_authenticated_user)
):
    """Get summary of imported accounts"""
    try:
        summary = await import_service.get_import_summary(supplier_id)
        return summary

    except Exception as e:
        logger.error(
            "Failed to get import summary",
            user_id=str(user.id),
            supplier_id=str(supplier_id) if supplier_id else "all",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve import summary"
        )


@router.get(
    "/health",
    summary="Account service health check",
    description="Check the health of the account management service"
)
async def health_check(
    db: AsyncSession = Depends(get_db_session)
):
    """Health check for account management service"""
    try:
        from sqlalchemy import text, select, func
        from shared.database.models import SupplierAccount
        from datetime import datetime

        # Test database connectivity
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        # Test model access
        account_count = await db.scalar(
            select(func.count(SupplierAccount.id))
        )

        return {
            "status": "healthy",
            "service": "account_management",
            "database_connected": True,
            "total_accounts": account_count or 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Account service health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Account service unhealthy: {str(e)}"
        )