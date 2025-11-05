"""
Unified Order Service - Facade Pattern
Routes order imports to appropriate service (Order or Transaction) based on source

This is a TEMPORARY solution to provide a single interface while we consolidate
the Sales and Orders domains. See context/code_refactor/sales_vs_orders_analysis.md
for the full consolidation plan.

Usage:
    unified_service = UnifiedOrderService(db_session)

    # For API-based imports (StockX, eBay, GOAT)
    result = await unified_service.import_orders(
        orders_data,
        source="stockx"
    )

    # For CSV/Excel imports
    result = await unified_service.import_orders(
        orders_data,
        source="csv"
    )
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from domains.orders.services.order_import_service import OrderImportService
from domains.sales.services.transaction_processor import TransactionProcessor

logger = structlog.get_logger(__name__)


class OrderSource:
    """Supported order sources"""

    # Modern API-based platforms (use Order table)
    STOCKX = "stockx"
    EBAY = "ebay"
    GOAT = "goat"
    ALIAS = "alias"

    # Legacy import sources (use Transaction table)
    CSV = "csv"
    EXCEL = "excel"
    NOTION = "notion"

    # All API-based sources
    API_SOURCES = {STOCKX, EBAY, GOAT, ALIAS}

    # All file-based sources
    FILE_SOURCES = {CSV, EXCEL, NOTION}


class UnifiedOrderService:
    """
    Facade service that provides a unified interface for order imports
    regardless of the source platform.

    **Architecture Note**: This is a transitional service created to address
    the Sales vs Orders domain overlap. The long-term plan is to consolidate
    everything into the Orders domain using the Order table.

    Current routing logic:
    - API-based sources (StockX, eBay, GOAT, Alias) → OrderImportService (Order table)
    - File-based sources (CSV, Excel, Notion) → TransactionProcessor (Transaction table)

    Future state (post-consolidation):
    - All sources → OrderImportService (Order table only)
    - TransactionProcessor deprecated
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.order_import_service = OrderImportService(db_session)
        self.transaction_processor = TransactionProcessor(db_session)
        self._logger = logger.bind(service="UnifiedOrderService")

    async def import_orders(
        self,
        orders_data: List[Dict[str, Any]],
        source: str,
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import orders from any source with automatic routing to the appropriate service.

        Args:
            orders_data: List of order dictionaries to import
            source: Source platform (stockx, ebay, csv, etc.)
            batch_id: Optional batch ID for tracking imports

        Returns:
            Dictionary with import statistics:
            {
                "total_orders": int,
                "created": int,
                "updated": int,
                "skipped": int,
                "errors": List[str]
            }

        Raises:
            ValueError: If source is not recognized

        Example:
            >>> service = UnifiedOrderService(db_session)
            >>> result = await service.import_orders(
            ...     orders_data=[{"orderNumber": "123", ...}],
            ...     source="stockx"
            ... )
            >>> print(f"Created {result['created']} orders")
        """
        source_lower = source.lower()

        self._logger.info(
            "Importing orders via unified service",
            source=source_lower,
            order_count=len(orders_data),
            batch_id=batch_id,
        )

        # Route to appropriate service
        if source_lower in OrderSource.API_SOURCES:
            return await self._import_via_order_service(orders_data, source_lower, batch_id)
        elif source_lower in OrderSource.FILE_SOURCES:
            return await self._import_via_transaction_processor(orders_data, batch_id)
        else:
            raise ValueError(
                f"Unsupported order source: {source}. "
                f"Supported sources: {OrderSource.API_SOURCES | OrderSource.FILE_SOURCES}"
            )

    async def _import_via_order_service(
        self,
        orders_data: List[Dict[str, Any]],
        source: str,
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import orders using OrderImportService (creates Order records)

        This is used for modern API-based platforms that provide rich order data.
        """
        self._logger.debug(
            "Routing to OrderImportService",
            source=source,
            order_count=len(orders_data),
        )

        if source == OrderSource.STOCKX:
            return await self.order_import_service.import_stockx_orders(orders_data, batch_id)
        elif source == OrderSource.EBAY:
            # TODO: Implement eBay-specific import when ready
            self._logger.warning(
                "eBay import not yet implemented, using generic order import",
                source=source,
            )
            return await self._generic_order_import(orders_data, source, batch_id)
        elif source in [OrderSource.GOAT, OrderSource.ALIAS]:
            # Generic multi-platform import
            return await self._generic_order_import(orders_data, source, batch_id)
        else:
            raise ValueError(f"Unexpected API source: {source}")

    async def _import_via_transaction_processor(
        self,
        orders_data: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import orders using TransactionProcessor (creates Transaction records)

        This is used for legacy file-based imports (CSV, Excel).
        """
        self._logger.debug(
            "Routing to TransactionProcessor (legacy)",
            order_count=len(orders_data),
        )

        # TransactionProcessor expects a batch_id
        if not batch_id:
            raise ValueError("batch_id is required for file-based imports")

        return await self.transaction_processor.create_transactions_from_batch(batch_id)

    async def _generic_order_import(
        self,
        orders_data: List[Dict[str, Any]],
        platform: str,
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generic order import for platforms without platform-specific logic.

        This creates Order records with platform-specific data stored in JSONB.
        """
        self._logger.info(
            "Generic order import",
            platform=platform,
            order_count=len(orders_data),
        )

        stats = {
            "total_orders": len(orders_data),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        from shared.database.models import Order

        for order_data in orders_data:
            try:
                # Extract common fields
                order_number = (
                    order_data.get("orderNumber")
                    or order_data.get("order_number")
                    or order_data.get("id")
                )

                if not order_number:
                    stats["skipped"] += 1
                    stats["errors"].append("Missing order number")
                    continue

                # Create Order with platform-specific data in JSONB
                order = Order(
                    stockx_order_number=f"{platform}_{order_number}",  # Prefix with platform
                    status=order_data.get("status", "unknown"),
                    amount=order_data.get("amount") or order_data.get("total"),
                    currency_code=order_data.get("currency", "USD"),
                    platform_specific_data={
                        "platform": platform,
                        "raw_order_data": order_data,
                    },
                    raw_data=order_data,
                )

                self.db_session.add(order)
                stats["created"] += 1

            except Exception as e:
                error_msg = f"Failed to import order: {str(e)}"
                stats["errors"].append(error_msg)
                self._logger.error(
                    "Order import failed",
                    error=str(e),
                    order_data=order_data,
                    exc_info=True,
                )

        await self.db_session.commit()

        self._logger.info(
            "Generic order import completed",
            platform=platform,
            **stats,
        )

        return stats

    async def get_order_by_external_id(
        self,
        external_id: str,
        source: str,
    ) -> Optional[Any]:
        """
        Get an order by external ID, searching in the appropriate table based on source.

        Args:
            external_id: External order ID (e.g., StockX order number)
            source: Source platform (stockx, csv, etc.)

        Returns:
            Order or Transaction object, or None if not found

        Example:
            >>> order = await service.get_order_by_external_id("STX-123", "stockx")
        """
        source_lower = source.lower()

        if source_lower in OrderSource.API_SOURCES:
            # Search in Order table
            from sqlalchemy import select
            from shared.database.models import Order

            query = select(Order).where(Order.stockx_order_number == external_id)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

        elif source_lower in OrderSource.FILE_SOURCES:
            # Search in Transaction table
            from sqlalchemy import select
            from shared.database.models import Transaction

            query = select(Transaction).where(Transaction.external_id == external_id)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

        else:
            raise ValueError(f"Unsupported source: {source}")

    def get_recommended_source(self, platform_name: str) -> str:
        """
        Get recommended source identifier for a platform name.

        This helps standardize platform names across the application.

        Args:
            platform_name: Platform name (case-insensitive)

        Returns:
            Standardized source identifier

        Example:
            >>> service.get_recommended_source("StockX")
            'stockx'
            >>> service.get_recommended_source("CSV Import")
            'csv'
        """
        platform_lower = platform_name.lower()

        # Map common variations to standard sources
        source_mapping = {
            "stockx": OrderSource.STOCKX,
            "stock x": OrderSource.STOCKX,
            "stock-x": OrderSource.STOCKX,
            "ebay": OrderSource.EBAY,
            "e-bay": OrderSource.EBAY,
            "goat": OrderSource.GOAT,
            "alias": OrderSource.ALIAS,
            "csv": OrderSource.CSV,
            "excel": OrderSource.EXCEL,
            "xls": OrderSource.EXCEL,
            "xlsx": OrderSource.EXCEL,
            "notion": OrderSource.NOTION,
        }

        # Check for partial matches
        for key, value in source_mapping.items():
            if key in platform_lower:
                return value

        # Default to CSV for unknown file-based imports
        if any(ext in platform_lower for ext in [".csv", ".xls", ".xlsx"]):
            return OrderSource.CSV

        # Default to stockx for API-based
        return OrderSource.STOCKX

    def is_api_source(self, source: str) -> bool:
        """Check if source is API-based (uses Order table)"""
        return source.lower() in OrderSource.API_SOURCES

    def is_file_source(self, source: str) -> bool:
        """Check if source is file-based (uses Transaction table)"""
        return source.lower() in OrderSource.FILE_SOURCES


# Convenience function for backward compatibility
async def import_orders(
    db_session: AsyncSession,
    orders_data: List[Dict[str, Any]],
    source: str,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to import orders without creating a service instance.

    Example:
        >>> from domains.orders.services.unified_order_service import import_orders
        >>> result = await import_orders(db_session, orders_data, "stockx")
    """
    service = UnifiedOrderService(db_session)
    return await service.import_orders(orders_data, source, batch_id)
