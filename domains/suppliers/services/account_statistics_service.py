"""
Account Statistics Service
Calculate and analyze supplier account performance metrics
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from shared.database.models import SupplierAccount, AccountPurchaseHistory, Supplier
from shared.repositories.base_repository import BaseRepository
from shared.utils.financial import FinancialCalculator

logger = structlog.get_logger(__name__)


class AccountStatisticsService:
    """Service for calculating and analyzing account performance statistics"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.account_repo = BaseRepository(SupplierAccount, db)
        self.purchase_repo = BaseRepository(AccountPurchaseHistory, db)
        self.supplier_repo = BaseRepository(Supplier, db)

    async def get_supplier_account_overview(self, supplier_id: UUID) -> Dict[str, Any]:
        """Get comprehensive overview of all accounts for a supplier"""
        try:
            # Get basic account statistics
            stats_query = select(
                func.count(SupplierAccount.id).label('total_accounts'),
                func.count(SupplierAccount.id).filter(
                    SupplierAccount.account_status == 'active'
                ).label('active_accounts'),
                func.count(SupplierAccount.id).filter(
                    SupplierAccount.is_verified == True
                ).label('verified_accounts'),
                func.sum(SupplierAccount.total_purchases).label('total_purchases'),
                func.sum(SupplierAccount.total_spent).label('total_revenue'),
                func.avg(SupplierAccount.success_rate).label('avg_success_rate'),
                func.avg(SupplierAccount.average_order_value).label('avg_order_value'),
                func.max(SupplierAccount.last_used_at).label('last_activity')
            ).where(SupplierAccount.supplier_id == supplier_id)

            result = await self.db.execute(stats_query)
            stats = result.first()

            # Get top performing accounts
            top_accounts = await self._get_top_performing_accounts(supplier_id, limit=5)

            # Get recent purchase activity
            recent_activity = await self._get_recent_purchase_activity(supplier_id, days=30)

            # Get account status distribution
            status_distribution = await self._get_account_status_distribution(supplier_id)

            # Get monthly performance trends
            monthly_trends = await self._get_monthly_performance_trends(supplier_id, months=6)

            return {
                "overview": {
                    "total_accounts": stats.total_accounts or 0,
                    "active_accounts": stats.active_accounts or 0,
                    "verified_accounts": stats.verified_accounts or 0,
                    "total_purchases": stats.total_purchases or 0,
                    "total_revenue": float(stats.total_revenue or 0),
                    "average_success_rate": float(stats.avg_success_rate or 0),
                    "average_order_value": float(stats.avg_order_value or 0),
                    "last_activity": stats.last_activity.isoformat() if stats.last_activity else None
                },
                "top_performing_accounts": top_accounts,
                "recent_activity": recent_activity,
                "status_distribution": status_distribution,
                "monthly_trends": monthly_trends
            }

        except Exception as e:
            logger.error(
                "Failed to get supplier account overview",
                supplier_id=str(supplier_id),
                error=str(e)
            )
            raise

    async def _get_top_performing_accounts(
        self,
        supplier_id: UUID,
        limit: int = 5,
        metric: str = "total_spent"
    ) -> List[Dict[str, Any]]:
        """Get top performing accounts by specified metric"""
        try:
            order_column = getattr(SupplierAccount, metric, SupplierAccount.total_spent)

            query = select(SupplierAccount).where(
                SupplierAccount.supplier_id == supplier_id
            ).order_by(desc(order_column)).limit(limit)

            result = await self.db.execute(query)
            accounts = result.scalars().all()

            return [
                {
                    "id": str(account.id),
                    "email": account.email,
                    "total_purchases": account.total_purchases,
                    "total_spent": float(account.total_spent),
                    "success_rate": float(account.success_rate),
                    "average_order_value": float(account.average_order_value),
                    "last_used": account.last_used_at.isoformat() if account.last_used_at else None
                }
                for account in accounts
            ]

        except Exception as e:
            logger.error("Failed to get top performing accounts", error=str(e))
            return []

    async def _get_recent_purchase_activity(
        self,
        supplier_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get recent purchase activity statistics"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)

            activity_query = select(
                func.count(AccountPurchaseHistory.id).label('total_purchases'),
                func.count(AccountPurchaseHistory.id).filter(
                    AccountPurchaseHistory.success == True
                ).label('successful_purchases'),
                func.sum(AccountPurchaseHistory.purchase_amount).label('total_amount'),
                func.count(func.distinct(AccountPurchaseHistory.account_id)).label('active_accounts')
            ).where(
                and_(
                    AccountPurchaseHistory.supplier_id == supplier_id,
                    AccountPurchaseHistory.purchase_date >= since_date
                )
            )

            result = await self.db.execute(activity_query)
            activity = result.first()

            success_rate = 0
            if activity.total_purchases and activity.total_purchases > 0:
                success_rate = (activity.successful_purchases / activity.total_purchases) * 100

            return {
                "period_days": days,
                "total_purchases": activity.total_purchases or 0,
                "successful_purchases": activity.successful_purchases or 0,
                "success_rate": round(success_rate, 2),
                "total_amount": float(activity.total_amount or 0),
                "active_accounts": activity.active_accounts or 0
            }

        except Exception as e:
            logger.error("Failed to get recent purchase activity", error=str(e))
            return {"period_days": days, "total_purchases": 0, "successful_purchases": 0,
                    "success_rate": 0, "total_amount": 0, "active_accounts": 0}

    async def _get_account_status_distribution(self, supplier_id: UUID) -> Dict[str, int]:
        """Get distribution of account statuses"""
        try:
            status_query = select(
                SupplierAccount.account_status,
                func.count(SupplierAccount.id).label('count')
            ).where(
                SupplierAccount.supplier_id == supplier_id
            ).group_by(SupplierAccount.account_status)

            result = await self.db.execute(status_query)
            status_data = result.all()

            return {status: count for status, count in status_data}

        except Exception as e:
            logger.error("Failed to get account status distribution", error=str(e))
            return {}

    async def _get_monthly_performance_trends(
        self,
        supplier_id: UUID,
        months: int = 6
    ) -> List[Dict[str, Any]]:
        """Get monthly performance trends"""
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=months * 30)

            # PostgreSQL specific query for monthly aggregation
            if hasattr(self.db.get_bind(), 'dialect') and 'postgresql' in str(self.db.get_bind().dialect):
                monthly_query = select(
                    text("DATE_TRUNC('month', purchase_date) as month"),
                    func.count(AccountPurchaseHistory.id).label('total_purchases'),
                    func.count(AccountPurchaseHistory.id).filter(
                        AccountPurchaseHistory.success == True
                    ).label('successful_purchases'),
                    func.sum(AccountPurchaseHistory.purchase_amount).label('total_amount'),
                    func.count(func.distinct(AccountPurchaseHistory.account_id)).label('active_accounts')
                ).where(
                    and_(
                        AccountPurchaseHistory.supplier_id == supplier_id,
                        AccountPurchaseHistory.purchase_date >= start_date
                    )
                ).group_by(text("DATE_TRUNC('month', purchase_date)")).order_by(text("month"))
            else:
                # SQLite fallback
                monthly_query = select(
                    text("strftime('%Y-%m', purchase_date) as month"),
                    func.count(AccountPurchaseHistory.id).label('total_purchases'),
                    func.count(AccountPurchaseHistory.id).filter(
                        AccountPurchaseHistory.success == True
                    ).label('successful_purchases'),
                    func.sum(AccountPurchaseHistory.purchase_amount).label('total_amount'),
                    func.count(func.distinct(AccountPurchaseHistory.account_id)).label('active_accounts')
                ).where(
                    and_(
                        AccountPurchaseHistory.supplier_id == supplier_id,
                        AccountPurchaseHistory.purchase_date >= start_date
                    )
                ).group_by(text("strftime('%Y-%m', purchase_date)")).order_by(text("month"))

            result = await self.db.execute(monthly_query)
            monthly_data = result.all()

            trends = []
            for row in monthly_data:
                success_rate = 0
                if row.total_purchases and row.total_purchases > 0:
                    success_rate = (row.successful_purchases / row.total_purchases) * 100

                trends.append({
                    "month": str(row.month),
                    "total_purchases": row.total_purchases or 0,
                    "successful_purchases": row.successful_purchases or 0,
                    "success_rate": round(success_rate, 2),
                    "total_amount": float(row.total_amount or 0),
                    "active_accounts": row.active_accounts or 0
                })

            return trends

        except Exception as e:
            logger.error("Failed to get monthly performance trends", error=str(e))
            return []

    async def get_account_detailed_statistics(self, account_id: UUID) -> Dict[str, Any]:
        """Get detailed statistics for a specific account"""
        try:
            # Get account with purchase history
            account_query = select(SupplierAccount).options(
                selectinload(SupplierAccount.purchase_history)
            ).where(SupplierAccount.id == account_id)

            result = await self.db.execute(account_query)
            account = result.scalar_one_or_none()

            if not account:
                raise ValueError(f"Account not found: {account_id}")

            # Calculate detailed statistics
            purchase_stats = await self._calculate_account_purchase_stats(account_id)
            performance_metrics = await self._calculate_account_performance_metrics(account_id)
            usage_patterns = await self._analyze_account_usage_patterns(account_id)

            return {
                "account_info": account.to_dict(),
                "purchase_statistics": purchase_stats,
                "performance_metrics": performance_metrics,
                "usage_patterns": usage_patterns
            }

        except Exception as e:
            logger.error(
                "Failed to get account detailed statistics",
                account_id=str(account_id),
                error=str(e)
            )
            raise

    async def _calculate_account_purchase_stats(self, account_id: UUID) -> Dict[str, Any]:
        """Calculate detailed purchase statistics for an account"""
        try:
            stats_query = select(
                func.count(AccountPurchaseHistory.id).label('total_purchases'),
                func.count(AccountPurchaseHistory.id).filter(
                    AccountPurchaseHistory.success == True
                ).label('successful_purchases'),
                func.sum(AccountPurchaseHistory.purchase_amount).label('total_spent'),
                func.avg(AccountPurchaseHistory.purchase_amount).label('avg_order_value'),
                func.min(AccountPurchaseHistory.purchase_amount).label('min_order_value'),
                func.max(AccountPurchaseHistory.purchase_amount).label('max_order_value'),
                func.avg(AccountPurchaseHistory.response_time_ms).label('avg_response_time'),
                func.min(AccountPurchaseHistory.purchase_date).label('first_purchase'),
                func.max(AccountPurchaseHistory.purchase_date).label('last_purchase')
            ).where(AccountPurchaseHistory.account_id == account_id)

            result = await self.db.execute(stats_query)
            stats = result.first()

            success_rate = 0
            if stats.total_purchases and stats.total_purchases > 0:
                success_rate = (stats.successful_purchases / stats.total_purchases) * 100

            return {
                "total_purchases": stats.total_purchases or 0,
                "successful_purchases": stats.successful_purchases or 0,
                "failed_purchases": (stats.total_purchases or 0) - (stats.successful_purchases or 0),
                "success_rate": round(success_rate, 2),
                "total_spent": float(stats.total_spent or 0),
                "average_order_value": float(stats.avg_order_value or 0),
                "min_order_value": float(stats.min_order_value or 0),
                "max_order_value": float(stats.max_order_value or 0),
                "average_response_time_ms": float(stats.avg_response_time or 0),
                "first_purchase": stats.first_purchase.isoformat() if stats.first_purchase else None,
                "last_purchase": stats.last_purchase.isoformat() if stats.last_purchase else None
            }

        except Exception as e:
            logger.error("Failed to calculate purchase stats", error=str(e))
            return {}

    async def _calculate_account_performance_metrics(self, account_id: UUID) -> Dict[str, Any]:
        """Calculate performance metrics for an account"""
        try:
            # Get recent performance (last 30 days)
            recent_date = datetime.utcnow() - timedelta(days=30)

            recent_query = select(
                func.count(AccountPurchaseHistory.id).label('recent_purchases'),
                func.count(AccountPurchaseHistory.id).filter(
                    AccountPurchaseHistory.success == True
                ).label('recent_successful'),
                func.avg(AccountPurchaseHistory.response_time_ms).label('recent_avg_response_time')
            ).where(
                and_(
                    AccountPurchaseHistory.account_id == account_id,
                    AccountPurchaseHistory.purchase_date >= recent_date
                )
            )

            result = await self.db.execute(recent_query)
            recent = result.first()

            recent_success_rate = 0
            if recent.recent_purchases and recent.recent_purchases > 0:
                recent_success_rate = (recent.recent_successful / recent.recent_purchases) * 100

            # Calculate purchase frequency
            frequency = await self._calculate_purchase_frequency(account_id)

            return {
                "recent_activity": {
                    "purchases_last_30_days": recent.recent_purchases or 0,
                    "success_rate_last_30_days": round(recent_success_rate, 2),
                    "avg_response_time_last_30_days": float(recent.recent_avg_response_time or 0)
                },
                "purchase_frequency": frequency
            }

        except Exception as e:
            logger.error("Failed to calculate performance metrics", error=str(e))
            return {}

    async def _calculate_purchase_frequency(self, account_id: UUID) -> Dict[str, Any]:
        """Calculate purchase frequency patterns"""
        try:
            # Get all purchase dates
            dates_query = select(AccountPurchaseHistory.purchase_date).where(
                AccountPurchaseHistory.account_id == account_id
            ).order_by(AccountPurchaseHistory.purchase_date)

            result = await self.db.execute(dates_query)
            dates = [row[0] for row in result.all()]

            if len(dates) < 2:
                return {
                    "purchases_per_week": 0,
                    "purchases_per_month": 0,
                    "average_days_between_purchases": 0
                }

            # Calculate time differences
            time_diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            avg_days_between = sum(time_diffs) / len(time_diffs) if time_diffs else 0

            # Calculate frequency rates
            total_days = (dates[-1] - dates[0]).days if len(dates) > 1 else 1
            total_purchases = len(dates)

            purchases_per_week = (total_purchases / max(total_days, 1)) * 7
            purchases_per_month = (total_purchases / max(total_days, 1)) * 30

            return {
                "purchases_per_week": round(purchases_per_week, 2),
                "purchases_per_month": round(purchases_per_month, 2),
                "average_days_between_purchases": round(avg_days_between, 1)
            }

        except Exception as e:
            logger.error("Failed to calculate purchase frequency", error=str(e))
            return {}

    async def _analyze_account_usage_patterns(self, account_id: UUID) -> Dict[str, Any]:
        """Analyze usage patterns for an account"""
        try:
            # Get hourly distribution
            hourly_query = select(
                text("EXTRACT(hour FROM purchase_date) as hour"),
                func.count(AccountPurchaseHistory.id).label('count')
            ).where(
                AccountPurchaseHistory.account_id == account_id
            ).group_by(text("EXTRACT(hour FROM purchase_date)"))

            result = await self.db.execute(hourly_query)
            hourly_data = {int(row.hour): row.count for row in result.all()}

            # Get status distribution
            status_query = select(
                AccountPurchaseHistory.purchase_status,
                func.count(AccountPurchaseHistory.id).label('count')
            ).where(
                AccountPurchaseHistory.account_id == account_id
            ).group_by(AccountPurchaseHistory.purchase_status)

            result = await self.db.execute(status_query)
            status_data = {status: count for status, count in result.all()}

            return {
                "hourly_distribution": hourly_data,
                "status_distribution": status_data,
                "peak_hour": max(hourly_data.items(), key=lambda x: x[1])[0] if hourly_data else None
            }

        except Exception as e:
            logger.error("Failed to analyze usage patterns", error=str(e))
            return {}

    async def recalculate_all_account_statistics(self, supplier_id: Optional[UUID] = None) -> Dict[str, int]:
        """Recalculate statistics for all accounts (or accounts for a specific supplier)"""
        try:
            # Get accounts to update
            query = select(SupplierAccount.id)
            if supplier_id:
                query = query.where(SupplierAccount.supplier_id == supplier_id)

            result = await self.db.execute(query)
            account_ids = [row[0] for row in result.all()]

            updated_count = 0
            from domains.suppliers.services.account_import_service import AccountImportService

            import_service = AccountImportService(self.db)

            for account_id in account_ids:
                try:
                    await import_service.update_account_statistics(account_id)
                    updated_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to update statistics for account",
                        account_id=str(account_id),
                        error=str(e)
                    )

            logger.info(
                "Recalculated account statistics",
                total_accounts=len(account_ids),
                updated_count=updated_count,
                supplier_id=str(supplier_id) if supplier_id else "all"
            )

            return {
                "total_accounts": len(account_ids),
                "updated_count": updated_count,
                "failed_count": len(account_ids) - updated_count
            }

        except Exception as e:
            logger.error("Failed to recalculate account statistics", error=str(e))
            raise