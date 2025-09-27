"""
Business Intelligence Service
Implements Notion-style analytics with ROI, PAS, and Shelf Life calculations
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Union
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import InventoryItem, Product, Supplier, SupplierPerformance

logger = structlog.get_logger(__name__)


class BusinessIntelligenceService:
    """Enhanced business intelligence with Notion feature parity"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_inventory_analytics(
        self, inventory_item: InventoryItem, sale_price: Optional[Decimal] = None, sale_date: Optional[date] = None
    ) -> Dict[str, Union[int, float, str]]:
        """
        Calculate comprehensive analytics for inventory item (Notion feature parity)

        Returns:
        - shelf_life_days: Days in inventory
        - roi_percentage: Return on investment
        - profit_per_shelf_day: PAS metric
        - sale_overview: Notion-style summary
        """

        # Calculate shelf life
        end_date = sale_date if sale_date else datetime.now().date()
        purchase_date = inventory_item.purchase_date.date() if inventory_item.purchase_date else datetime.now().date()
        shelf_life_days = (end_date - purchase_date).days

        # Calculate financial metrics
        purchase_price = inventory_item.purchase_price or Decimal('0')
        current_sale_price = sale_price or Decimal('0')

        profit = current_sale_price - purchase_price if current_sale_price > 0 else Decimal('0')
        roi_percentage = (profit / purchase_price * 100) if purchase_price > 0 else Decimal('0')
        profit_per_shelf_day = (profit / shelf_life_days) if shelf_life_days > 0 else Decimal('0')

        # Generate Notion-style sale overview
        size_info = inventory_item.size.value if inventory_item.size else "N/A"
        if sale_date:
            sale_overview = f"{size_info} - SOLD - Sold {shelf_life_days} days ago"
        else:
            sale_overview = f"{size_info} - In stock for {shelf_life_days} days"

        analytics = {
            "shelf_life_days": shelf_life_days,
            "roi_percentage": float(roi_percentage),
            "profit_per_shelf_day": float(profit_per_shelf_day),
            "profit": float(profit),
            "sale_overview": sale_overview
        }

        logger.info("Calculated inventory analytics",
                   item_id=str(inventory_item.id),
                   analytics=analytics)

        return analytics

    async def get_dead_stock_analysis(self, days_threshold: int = 90) -> List[Dict]:
        """
        Identify dead stock using shelf life analysis (Notion feature)
        Items in stock longer than threshold are considered dead stock
        """

        current_date = datetime.now().date()

        query = select(InventoryItem, Product).join(Product).where(
            and_(
                InventoryItem.status == "in_stock",
                InventoryItem.shelf_life_days > days_threshold
            )
        ).order_by(desc(InventoryItem.shelf_life_days))

        result = await self.db.execute(query)
        items = result.fetchall()

        dead_stock = []
        for item, product in items:
            analytics = await self.calculate_inventory_analytics(item)
            dead_stock.append({
                "item_id": str(item.id),
                "product_name": product.name,
                "sku": product.sku,
                "purchase_price": float(item.purchase_price or 0),
                "days_in_stock": analytics["shelf_life_days"],
                "profit_per_day": analytics["profit_per_shelf_day"],
                "total_cost": float(item.purchase_price or 0),
                "size": item.size.value if item.size else None,
                "supplier": item.supplier,
                "status": item.status
            })

        logger.info("Dead stock analysis completed",
                   threshold_days=days_threshold,
                   dead_stock_count=len(dead_stock))

        return dead_stock

    async def get_roi_performance_report(self, limit: int = 100) -> Dict[str, Union[List, Dict]]:
        """
        Generate ROI performance report (Notion-style analytics)
        Shows best and worst performing items by ROI
        """

        # Best performers (highest ROI)
        best_query = select(InventoryItem, Product).join(Product).where(
            and_(
                InventoryItem.roi_percentage.isnot(None),
                InventoryItem.roi_percentage > 0
            )
        ).order_by(desc(InventoryItem.roi_percentage)).limit(limit)

        best_result = await self.db.execute(best_query)
        best_performers = []

        for item, product in best_result.fetchall():
            best_performers.append({
                "item_id": str(item.id),
                "product_name": product.name,
                "sku": product.sku,
                "roi_percentage": float(item.roi_percentage or 0),
                "profit_per_shelf_day": float(item.profit_per_shelf_day or 0),
                "shelf_life_days": item.shelf_life_days,
                "purchase_price": float(item.purchase_price or 0),
                "size": item.size.value if item.size else None
            })

        # Worst performers (lowest/negative ROI)
        worst_query = select(InventoryItem, Product).join(Product).where(
            InventoryItem.roi_percentage.isnot(None)
        ).order_by(InventoryItem.roi_percentage).limit(limit)

        worst_result = await self.db.execute(worst_query)
        worst_performers = []

        for item, product in worst_result.fetchall():
            worst_performers.append({
                "item_id": str(item.id),
                "product_name": product.name,
                "sku": product.sku,
                "roi_percentage": float(item.roi_percentage or 0),
                "profit_per_shelf_day": float(item.profit_per_shelf_day or 0),
                "shelf_life_days": item.shelf_life_days,
                "purchase_price": float(item.purchase_price or 0),
                "size": item.size.value if item.size else None
            })

        # Summary statistics
        avg_roi_query = select(func.avg(InventoryItem.roi_percentage)).where(
            InventoryItem.roi_percentage.isnot(None)
        )
        avg_roi_result = await self.db.execute(avg_roi_query)
        avg_roi = avg_roi_result.scalar() or 0

        summary = {
            "average_roi": float(avg_roi),
            "best_performers_count": len(best_performers),
            "worst_performers_count": len(worst_performers),
            "analysis_date": datetime.now().isoformat()
        }

        logger.info("ROI performance report generated", summary=summary)

        return {
            "summary": summary,
            "best_performers": best_performers,
            "worst_performers": worst_performers
        }

    async def get_shelf_life_distribution(self) -> Dict[str, Union[List, int]]:
        """
        Analyze shelf life distribution for inventory optimization
        """

        query = select(
            InventoryItem.shelf_life_days,
            func.count(InventoryItem.id).label('count')
        ).where(
            InventoryItem.shelf_life_days.isnot(None)
        ).group_by(InventoryItem.shelf_life_days).order_by(InventoryItem.shelf_life_days)

        result = await self.db.execute(query)
        distribution_data = result.fetchall()

        distribution = []
        total_items = 0

        for days, count in distribution_data:
            distribution.append({
                "shelf_life_days": days,
                "item_count": count,
                "category": self._categorize_shelf_life(days)
            })
            total_items += count

        # Calculate category summaries
        fast_moving = sum(item["item_count"] for item in distribution if item["category"] == "fast_moving")
        medium_moving = sum(item["item_count"] for item in distribution if item["category"] == "medium_moving")
        slow_moving = sum(item["item_count"] for item in distribution if item["category"] == "slow_moving")
        dead_stock = sum(item["item_count"] for item in distribution if item["category"] == "dead_stock")

        summary = {
            "total_items": total_items,
            "fast_moving": fast_moving,
            "medium_moving": medium_moving,
            "slow_moving": slow_moving,
            "dead_stock": dead_stock,
            "fast_moving_percentage": (fast_moving / total_items * 100) if total_items > 0 else 0,
            "dead_stock_percentage": (dead_stock / total_items * 100) if total_items > 0 else 0
        }

        logger.info("Shelf life distribution analyzed", summary=summary)

        return {
            "summary": summary,
            "distribution": distribution
        }

    def _categorize_shelf_life(self, days: int) -> str:
        """Categorize inventory items by shelf life (Notion logic)"""
        if days <= 30:
            return "fast_moving"
        elif days <= 60:
            return "medium_moving"
        elif days <= 90:
            return "slow_moving"
        else:
            return "dead_stock"

    async def update_inventory_analytics(self, inventory_item_id: UUID, sale_price: Optional[Decimal] = None,
                                       sale_date: Optional[date] = None) -> Dict:
        """
        Update analytics for a specific inventory item
        """

        # Get inventory item
        query = select(InventoryItem).where(InventoryItem.id == inventory_item_id)
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            raise ValueError(f"Inventory item {inventory_item_id} not found")

        # Calculate new analytics
        analytics = await self.calculate_inventory_analytics(item, sale_price, sale_date)

        # Update database fields
        item.shelf_life_days = analytics["shelf_life_days"]
        item.roi_percentage = Decimal(str(analytics["roi_percentage"]))
        item.profit_per_shelf_day = Decimal(str(analytics["profit_per_shelf_day"]))
        item.sale_overview = analytics["sale_overview"]

        await self.db.commit()

        logger.info("Inventory analytics updated",
                   item_id=str(inventory_item_id),
                   analytics=analytics)

        return analytics

    async def get_supplier_performance_summary(self, supplier_id: Optional[UUID] = None) -> List[Dict]:
        """
        Get supplier performance analytics (45+ supplier intelligence)
        """

        query = select(SupplierPerformance, Supplier).join(Supplier)

        if supplier_id:
            query = query.where(SupplierPerformance.supplier_id == supplier_id)

        query = query.order_by(desc(SupplierPerformance.month_year))

        result = await self.db.execute(query)
        performance_data = result.fetchall()

        performance_summary = []
        for perf, supplier in performance_data:
            performance_summary.append({
                "supplier_id": str(supplier.id),
                "supplier_name": supplier.name,
                "month_year": perf.month_year.isoformat() if perf.month_year else None,
                "total_orders": perf.total_orders,
                "avg_delivery_time": float(perf.avg_delivery_time or 0),
                "return_rate": float(perf.return_rate or 0),
                "avg_roi": float(perf.avg_roi or 0),
                "supplier_category": supplier.supplier_category,
                "vat_rate": float(supplier.vat_rate or 0),
                "default_email": supplier.default_email
            })

        logger.info("Supplier performance summary generated",
                   count=len(performance_summary))

        return performance_summary