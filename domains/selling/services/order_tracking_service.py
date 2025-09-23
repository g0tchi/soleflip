"""
Order Tracking Service - StockX Order Management & Analytics
Handles order synchronization, profit calculations, and sales analytics
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

import httpx
from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import StockXOrder, StockXListing, Product
from shared.utils.financial import FinancialCalculator
from shared.database.transaction_manager import TransactionMixin, transactional
from domains.selling.services.stockx_api_client import StockXAPIClient

logger = logging.getLogger(__name__)


class OrderTrackingService(TransactionMixin):
    """Service for tracking StockX orders and calculating profits with transaction safety"""

    def __init__(self, db: AsyncSession, api_token: str):
        super().__init__(db_session=db)
        self.api_client = StockXAPIClient(api_token)

    async def get_active_orders(self, limit: int = 100) -> List[StockXOrder]:
        """Get all active orders that are not yet completed"""
        try:
            from sqlalchemy import select

            query = (
                select(StockXOrder)
                .where(StockXOrder.order_status.in_(["pending", "authenticated", "shipped"]))
                .order_by(desc(StockXOrder.sold_at))
                .limit(limit)
                .options(selectinload(StockXOrder.listing))
            )

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get active orders: {str(e)}")
            raise

    async def get_order_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[StockXOrder]:
        """Get order history with optional filtering"""
        try:
            from sqlalchemy import select

            query = select(StockXOrder).options(selectinload(StockXOrder.listing))

            # Apply filters
            conditions = []
            if start_date:
                conditions.append(StockXOrder.sold_at >= start_date)
            if end_date:
                conditions.append(StockXOrder.sold_at <= end_date)
            if status:
                conditions.append(StockXOrder.order_status == status)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(desc(StockXOrder.sold_at)).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get order history: {str(e)}")
            raise

    async def calculate_profit_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Calculate comprehensive profit analytics for a period"""
        try:
            since_date = datetime.utcnow().date() - timedelta(days=days)
            orders = await self.get_order_history(start_date=since_date, limit=1000)

            if not orders:
                return self._empty_analytics(days)

            # Calculate totals using safe financial operations
            total_sales = len(orders)

            # Extract values for safe calculation
            sale_prices = [o.sale_price for o in orders if o.sale_price]
            seller_fees = [o.seller_fee for o in orders if o.seller_fee]
            processing_fees = [o.processing_fee for o in orders if o.processing_fee]
            buyer_premiums = [o.buyer_premium for o in orders if o.buyer_premium]
            net_proceeds_list = [o.net_proceeds for o in orders if o.net_proceeds]
            gross_profits = [o.gross_profit for o in orders if o.gross_profit]
            net_profits = [o.net_profit for o in orders if o.net_profit]
            rois = [o.roi for o in orders if o.roi]

            # Use FinancialCalculator for safe calculations
            gross_revenue = FinancialCalculator.safe_sum(sale_prices)
            total_fees = (FinancialCalculator.safe_sum(seller_fees) +
                         FinancialCalculator.safe_sum(processing_fees) +
                         FinancialCalculator.safe_sum(buyer_premiums))
            net_revenue = FinancialCalculator.safe_sum(net_proceeds_list)
            gross_profit = FinancialCalculator.safe_sum(gross_profits)
            net_profit = FinancialCalculator.safe_sum(net_profits)

            # Calculate profit margin safely
            profit_margin = FinancialCalculator.calculate_margin(
                cost=gross_revenue - net_profit,
                sale_price=gross_revenue
            ) if gross_revenue > 0 else FinancialCalculator.to_percentage(0)

            # Calculate average ROI safely
            avg_roi = FinancialCalculator.safe_average(rois)

            # Find best and worst sales using safe comparison
            profit_orders = [o for o in orders if o.net_profit]
            best_sale = max(profit_orders, key=lambda x: FinancialCalculator.to_decimal(x.net_profit)) if profit_orders else None
            worst_sale = min(profit_orders, key=lambda x: FinancialCalculator.to_decimal(x.net_profit)) if profit_orders else None

            # Daily breakdown
            daily_breakdown = await self._calculate_daily_breakdown(orders, days)

            return {
                "total_sales": total_sales,
                "gross_revenue": float(gross_revenue),
                "net_revenue": float(net_revenue),
                "total_fees": float(total_fees),
                "gross_profit": float(gross_profit),
                "net_profit": float(net_profit),
                "profit_margin": float(profit_margin),
                "avg_roi": float(avg_roi),
                "best_sale": best_sale,
                "worst_sale": worst_sale,
                "daily_breakdown": daily_breakdown
            }

        except Exception as e:
            logger.error(f"Failed to calculate profit analytics: {str(e)}")
            raise

    async def generate_tax_report(self, year: int) -> Dict[str, Any]:
        """Generate comprehensive tax report for a year"""
        try:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            orders = await self.get_order_history(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )

            if not orders:
                return self._empty_tax_report(year)

            # Calculate totals
            total_sales = len(orders)
            total_gross_revenue = sum(float(o.sale_price) for o in orders if o.sale_price)
            total_cost_basis = sum(float(o.original_buy_price or 0) for o in orders)
            total_gross_profit = sum(float(o.gross_profit or 0) for o in orders)
            total_fees = sum(
                float(o.seller_fee or 0) + float(o.processing_fee or 0)
                for o in orders
            )
            total_net_profit = sum(float(o.net_profit or 0) for o in orders)

            # Separate short-term vs long-term
            short_term_sales = 0
            long_term_sales = 0
            entries = []

            for order in orders:
                # Calculate holding period (simplified - would need listing creation date)
                holding_days = 30  # Default assumption, should be calculated from actual data

                if holding_days <= 365:
                    short_term_sales += 1
                else:
                    long_term_sales += 1

                # Get product name (would need to join with products table)
                product_name = f"Product {order.listing.product_id}" if order.listing else "Unknown Product"

                entries.append({
                    "order_id": str(order.id),
                    "stockx_order_number": order.stockx_order_number,
                    "sale_date": order.sold_at.strftime("%Y-%m-%d"),
                    "product_name": product_name,
                    "sale_price": float(order.sale_price or 0),
                    "cost_basis": float(order.original_buy_price or 0),
                    "gross_profit": float(order.gross_profit or 0),
                    "fees_paid": float((order.seller_fee or 0) + (order.processing_fee or 0)),
                    "net_profit": float(order.net_profit or 0),
                    "holding_period_days": holding_days
                })

            return {
                "total_sales": total_sales,
                "total_gross_revenue": total_gross_revenue,
                "total_cost_basis": total_cost_basis,
                "total_gross_profit": total_gross_profit,
                "total_fees": total_fees,
                "total_net_profit": total_net_profit,
                "short_term_sales": short_term_sales,
                "long_term_sales": long_term_sales,
                "entries": entries
            }

        except Exception as e:
            logger.error(f"Failed to generate tax report: {str(e)}")
            raise

    @transactional()
    async def sync_orders_from_stockx(self) -> Dict[str, int]:
        """Sync new orders from StockX API"""
        start_time = datetime.utcnow()
        new_orders = 0
        updated_orders = 0

        # Get recent orders from StockX API
        orders_data = await self._fetch_stockx_orders()

        for order_data in orders_data:
            stockx_order_number = order_data.get("orderNumber")
            if not stockx_order_number:
                continue

            # Check if order already exists
            existing_order = await self._get_order_by_stockx_number(stockx_order_number)

            if existing_order:
                # Update existing order
                await self._update_order_from_api_data(existing_order, order_data)
                updated_orders += 1
            else:
                # Create new order
                await self._create_order_from_api_data(order_data)
                new_orders += 1

        # No need to commit manually - @transactional handles it
        sync_duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            "new_orders": new_orders,
            "updated_orders": updated_orders,
            "total_synced": new_orders + updated_orders,
            "sync_duration_seconds": sync_duration
        }

    @transactional()
    async def update_order_tracking(self, order_id: UUID, tracking_number: str) -> StockXOrder:
        """Update tracking information for an order"""
        from sqlalchemy import select

        query = select(StockXOrder).where(StockXOrder.id == order_id)
        result = await self.db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        # Update tracking information
        order.tracking_number = tracking_number
        order.shipping_status = "shipped"
        if not order.shipped_at:
            order.shipped_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        # No need to commit manually - @transactional handles it
        return order

    async def _fetch_stockx_orders(self) -> List[Dict[str, Any]]:
        """Fetch recent orders from StockX API"""
        try:
            # This would use the actual StockX orders API endpoint
            # For now, return mock data structure
            response = await self.api_client.get("/selling/orders", params={
                "limit": 100,
                "includes": "listing,product"
            })

            return response.get("orders", [])

        except Exception as e:
            logger.warning(f"Failed to fetch orders from StockX API: {str(e)}")
            return []

    async def _get_order_by_stockx_number(self, stockx_order_number: str) -> Optional[StockXOrder]:
        """Get existing order by StockX order number"""
        try:
            from sqlalchemy import select

            query = select(StockXOrder).where(
                StockXOrder.stockx_order_number == stockx_order_number
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get order by StockX number: {str(e)}")
            return None

    async def _create_order_from_api_data(self, order_data: Dict[str, Any]) -> StockXOrder:
        """Create new order from StockX API data"""
        try:
            # Find matching listing
            listing = await self._find_listing_for_order(order_data)
            if not listing:
                logger.warning(f"No matching listing found for order {order_data.get('orderNumber')}")
                return None

            # Calculate profit metrics using safe financial operations
            sale_price = FinancialCalculator.to_currency(order_data.get("salePrice", 0))
            seller_fee = FinancialCalculator.to_currency(order_data.get("sellerFee", 0))
            processing_fee = FinancialCalculator.to_currency(order_data.get("processingFee", 0))

            # Calculate net proceeds using financial calculator
            net_proceeds = FinancialCalculator.calculate_net_proceeds(
                sale_price=sale_price,
                seller_fee=seller_fee,
                processing_fee=processing_fee
            )

            original_buy_price = FinancialCalculator.to_currency(listing.buy_price or 0)

            # Calculate profits using financial calculator
            gross_profit = FinancialCalculator.calculate_gross_profit(
                sale_price=sale_price,
                cost=original_buy_price
            )
            net_profit = FinancialCalculator.calculate_net_profit(
                net_proceeds=net_proceeds,
                cost=original_buy_price
            )

            # Calculate margin and ROI using financial calculator
            actual_margin = FinancialCalculator.calculate_margin(
                cost=original_buy_price,
                sale_price=sale_price
            )
            roi = FinancialCalculator.calculate_roi(
                cost=original_buy_price,
                profit=net_profit
            )

            # Create order
            order = StockXOrder(
                listing_id=listing.id,
                stockx_order_number=order_data["orderNumber"],
                sale_price=sale_price,
                seller_fee=seller_fee,
                processing_fee=processing_fee,
                net_proceeds=net_proceeds,
                original_buy_price=original_buy_price,
                gross_profit=gross_profit,
                net_profit=net_profit,
                actual_margin=actual_margin,
                roi=roi,
                order_status=order_data.get("status", "pending"),
                sold_at=datetime.fromisoformat(order_data["soldAt"].replace("Z", "+00:00"))
            )

            self.db.add(order)
            await self.db.flush()

            # Update listing status to sold
            listing.status = "sold"
            listing.is_active = False
            listing.updated_at = datetime.utcnow()

            return order

        except Exception as e:
            logger.error(f"Failed to create order from API data: {str(e)}")
            raise

    async def _update_order_from_api_data(self, order: StockXOrder, order_data: Dict[str, Any]):
        """Update existing order with latest API data"""
        try:
            # Update status and tracking info
            order.order_status = order_data.get("status", order.order_status)
            order.shipping_status = order_data.get("shippingStatus", order.shipping_status)

            if order_data.get("trackingNumber"):
                order.tracking_number = order_data["trackingNumber"]

            if order_data.get("shippedAt") and not order.shipped_at:
                order.shipped_at = datetime.fromisoformat(order_data["shippedAt"].replace("Z", "+00:00"))

            if order_data.get("completedAt") and not order.completed_at:
                order.completed_at = datetime.fromisoformat(order_data["completedAt"].replace("Z", "+00:00"))

            order.updated_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to update order from API data: {str(e)}")
            raise

    async def _find_listing_for_order(self, order_data: Dict[str, Any]) -> Optional[StockXListing]:
        """Find the listing that corresponds to this order"""
        try:
            from sqlalchemy import select

            # Try to match by StockX listing ID if available
            stockx_listing_id = order_data.get("listingId")
            if stockx_listing_id:
                query = select(StockXListing).where(
                    StockXListing.stockx_listing_id == stockx_listing_id
                )
                result = await self.db.execute(query)
                listing = result.scalar_one_or_none()
                if listing:
                    return listing

            # Fallback: match by product and price (less reliable)
            stockx_product_id = order_data.get("productId")
            sale_price = Decimal(str(order_data.get("salePrice", 0)))

            if stockx_product_id:
                query = select(StockXListing).where(
                    and_(
                        StockXListing.stockx_product_id == stockx_product_id,
                        StockXListing.ask_price == sale_price,
                        StockXListing.status == "active"
                    )
                ).order_by(StockXListing.created_at)

                result = await self.db.execute(query)
                return result.scalar_one_or_none()

            return None

        except Exception as e:
            logger.error(f"Failed to find listing for order: {str(e)}")
            return None

    async def _calculate_daily_breakdown(self, orders: List[StockXOrder], days: int) -> List[Dict[str, float]]:
        """Calculate daily profit breakdown"""
        try:
            daily_data = {}

            # Initialize all days with zero values
            for i in range(days):
                day = (datetime.utcnow().date() - timedelta(days=i)).strftime("%Y-%m-%d")
                daily_data[day] = {
                    "date": day,
                    "sales_count": 0,
                    "gross_revenue": 0.0,
                    "net_profit": 0.0
                }

            # Aggregate order data by day
            for order in orders:
                day = order.sold_at.strftime("%Y-%m-%d")
                if day in daily_data:
                    daily_data[day]["sales_count"] += 1
                    daily_data[day]["gross_revenue"] += float(order.sale_price or 0)
                    daily_data[day]["net_profit"] += float(order.net_profit or 0)

            # Return sorted by date
            return sorted(daily_data.values(), key=lambda x: x["date"])

        except Exception as e:
            logger.error(f"Failed to calculate daily breakdown: {str(e)}")
            return []

    def _empty_analytics(self, days: int) -> Dict[str, Any]:
        """Return empty analytics structure"""
        return {
            "total_sales": 0,
            "gross_revenue": 0.0,
            "net_revenue": 0.0,
            "total_fees": 0.0,
            "gross_profit": 0.0,
            "net_profit": 0.0,
            "profit_margin": 0.0,
            "avg_roi": 0.0,
            "best_sale": None,
            "worst_sale": None,
            "daily_breakdown": []
        }

    def _empty_tax_report(self, year: int) -> Dict[str, Any]:
        """Return empty tax report structure"""
        return {
            "total_sales": 0,
            "total_gross_revenue": 0.0,
            "total_cost_basis": 0.0,
            "total_gross_profit": 0.0,
            "total_fees": 0.0,
            "total_net_profit": 0.0,
            "short_term_sales": 0,
            "long_term_sales": 0,
            "entries": []
        }