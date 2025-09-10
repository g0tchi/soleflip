"""
Pricing Repository - Data access layer for pricing operations
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from shared.database.models import Brand, Product

from ..models import BrandMultiplier, MarketPrice, PriceHistory, PriceRule


class PricingRepository:
    """Repository for pricing-related database operations"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # =====================================================
    # PRICE RULES MANAGEMENT
    # =====================================================

    async def get_active_price_rules(
        self,
        brand_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        platform_id: Optional[uuid.UUID] = None,
        rule_type: Optional[str] = None,
    ) -> List[PriceRule]:
        """Get active price rules with optional filters"""
        query = (
            select(PriceRule)
            .where(
                PriceRule.active == True,
                PriceRule.effective_from <= datetime.now(),
                or_(
                    PriceRule.effective_until.is_(None), PriceRule.effective_until >= datetime.now()
                ),
            )
            .options(
                joinedload(PriceRule.brand),
                joinedload(PriceRule.category),
                joinedload(PriceRule.platform),
            )
            .order_by(PriceRule.priority.asc())
        )

        # Apply filters
        if brand_id:
            query = query.where(or_(PriceRule.brand_id == brand_id, PriceRule.brand_id.is_(None)))
        if category_id:
            query = query.where(
                or_(PriceRule.category_id == category_id, PriceRule.category_id.is_(None))
            )
        if platform_id:
            query = query.where(
                or_(PriceRule.platform_id == platform_id, PriceRule.platform_id.is_(None))
            )
        if rule_type:
            query = query.where(PriceRule.rule_type == rule_type)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_price_rule(self, rule_data: Dict[str, Any]) -> PriceRule:
        """Create new price rule"""
        rule = PriceRule(**rule_data)
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def update_price_rule(
        self, rule_id: uuid.UUID, update_data: Dict[str, Any]
    ) -> Optional[PriceRule]:
        """Update existing price rule"""
        query = select(PriceRule).where(PriceRule.id == rule_id)
        result = await self.db.execute(query)
        rule = result.scalar_one_or_none()

        if rule:
            for key, value in update_data.items():
                setattr(rule, key, value)
            await self.db.flush()

        return rule

    # =====================================================
    # BRAND MULTIPLIERS
    # =====================================================

    async def get_brand_multipliers(
        self,
        brand_id: uuid.UUID,
        multiplier_type: Optional[str] = None,
        effective_date: Optional[date] = None,
    ) -> List[BrandMultiplier]:
        """Get brand multipliers with optional filters"""
        if effective_date is None:
            effective_date = date.today()

        query = (
            select(BrandMultiplier)
            .where(
                BrandMultiplier.brand_id == brand_id,
                BrandMultiplier.active == True,
                BrandMultiplier.effective_from <= effective_date,
                or_(
                    BrandMultiplier.effective_until.is_(None),
                    BrandMultiplier.effective_until >= effective_date,
                ),
            )
            .options(joinedload(BrandMultiplier.brand))
        )

        if multiplier_type:
            query = query.where(BrandMultiplier.multiplier_type == multiplier_type)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_brand_multiplier(self, multiplier_data: Dict[str, Any]) -> BrandMultiplier:
        """Create new brand multiplier"""
        multiplier = BrandMultiplier(**multiplier_data)
        self.db.add(multiplier)
        await self.db.flush()
        return multiplier

    # =====================================================
    # PRICE HISTORY TRACKING
    # =====================================================

    async def record_price_history(self, price_data: Dict[str, Any]) -> PriceHistory:
        """Record new price history entry"""
        price_entry = PriceHistory(**price_data)
        self.db.add(price_entry)
        await self.db.flush()
        return price_entry

    async def get_price_history(
        self,
        product_id: uuid.UUID,
        days_back: int = 30,
        price_types: Optional[List[str]] = None,
        platform_id: Optional[uuid.UUID] = None,
    ) -> List[PriceHistory]:
        """Get price history for product with filters"""
        start_date = date.today() - timedelta(days=days_back)

        query = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id, PriceHistory.price_date >= start_date)
            .options(joinedload(PriceHistory.product), joinedload(PriceHistory.platform))
            .order_by(desc(PriceHistory.price_date))
        )

        if price_types:
            query = query.where(PriceHistory.price_type.in_(price_types))
        if platform_id:
            query = query.where(PriceHistory.platform_id == platform_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_latest_price(
        self,
        product_id: uuid.UUID,
        price_type: str = "listing",
        platform_id: Optional[uuid.UUID] = None,
    ) -> Optional[PriceHistory]:
        """Get latest price for product"""
        query = select(PriceHistory).where(
            PriceHistory.product_id == product_id, PriceHistory.price_type == price_type
        )

        if platform_id:
            query = query.where(PriceHistory.platform_id == platform_id)

        query = query.order_by(desc(PriceHistory.price_date), desc(PriceHistory.created_at)).limit(
            1
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # =====================================================
    # MARKET PRICE DATA
    # =====================================================

    async def get_market_prices(
        self,
        product_id: uuid.UUID,
        platform_name: Optional[str] = None,
        condition: Optional[str] = None,
        days_back: int = 7,
    ) -> List[MarketPrice]:
        """Get recent market prices for product"""
        start_date = date.today() - timedelta(days=days_back)

        query = (
            select(MarketPrice)
            .where(MarketPrice.product_id == product_id, MarketPrice.price_date >= start_date)
            .options(joinedload(MarketPrice.product))
            .order_by(desc(MarketPrice.price_date))
        )

        if platform_name:
            query = query.where(MarketPrice.platform_name == platform_name)
        if condition:
            query = query.where(MarketPrice.condition == condition)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_market_price(self, market_data: Dict[str, Any]) -> MarketPrice:
        """Create new market price entry"""
        market_price = MarketPrice(**market_data)
        self.db.add(market_price)
        await self.db.flush()
        return market_price

    async def get_competitive_pricing_data(
        self, product_id: uuid.UUID, condition: str = "new"
    ) -> Dict[str, Any]:
        """Get comprehensive competitive pricing analysis"""
        # Get recent market prices from all platforms
        query = (
            select(MarketPrice)
            .where(
                MarketPrice.product_id == product_id,
                MarketPrice.condition == condition,
                MarketPrice.price_date >= date.today() - timedelta(days=7),
            )
            .order_by(desc(MarketPrice.price_date))
        )

        result = await self.db.execute(query)
        market_prices = result.scalars().all()

        if not market_prices:
            return {}

        # Aggregate pricing data
        platform_data = {}
        for mp in market_prices:
            if mp.platform_name not in platform_data:
                platform_data[mp.platform_name] = {
                    "latest_date": mp.price_date,
                    "lowest_ask": mp.lowest_ask,
                    "highest_bid": mp.highest_bid,
                    "last_sale": mp.last_sale,
                    "average_price": mp.average_price,
                    "sales_volume": mp.sales_volume,
                }

        # Calculate competitive metrics
        all_last_sales = [float(mp.last_sale) for mp in market_prices if mp.last_sale]
        all_avg_prices = [float(mp.average_price) for mp in market_prices if mp.average_price]

        competitive_summary = {
            "platforms": platform_data,
            "market_average": sum(all_avg_prices) / len(all_avg_prices) if all_avg_prices else None,
            "market_range": {
                "min": min(all_last_sales) if all_last_sales else None,
                "max": max(all_last_sales) if all_last_sales else None,
            },
            "total_volume": sum(mp.sales_volume for mp in market_prices if mp.sales_volume),
            "data_points": len(market_prices),
        }

        return competitive_summary

    # =====================================================
    # ANALYTICS QUERIES
    # =====================================================

    async def get_pricing_performance_metrics(
        self,
        brand_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive pricing performance metrics"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Base query for price history analysis
        base_query = (
            select(
                func.count(PriceHistory.id).label("total_price_changes"),
                func.avg(PriceHistory.price_amount).label("avg_price"),
                func.min(PriceHistory.price_amount).label("min_price"),
                func.max(PriceHistory.price_amount).label("max_price"),
                func.stddev(PriceHistory.price_amount).label("price_volatility"),
            )
            .select_from(PriceHistory)
            .where(
                PriceHistory.price_date.between(start_date, end_date),
                PriceHistory.price_type == "listing",
            )
        )

        # Apply filters if provided
        if brand_id or category_id:
            base_query = base_query.join(Product, PriceHistory.product_id == Product.id)
            if brand_id:
                base_query = base_query.where(Product.brand_id == brand_id)
            if category_id:
                base_query = base_query.where(Product.category_id == category_id)

        result = await self.db.execute(base_query)
        metrics = result.first()

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_price_changes": metrics.total_price_changes or 0,
            "average_price": float(metrics.avg_price) if metrics.avg_price else 0,
            "price_range": {
                "min": float(metrics.min_price) if metrics.min_price else 0,
                "max": float(metrics.max_price) if metrics.max_price else 0,
            },
            "price_volatility": float(metrics.price_volatility) if metrics.price_volatility else 0,
        }

    async def get_top_performing_products(
        self, limit: int = 10, metric: str = "volume", days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Get top performing products by various metrics"""
        start_date = date.today() - timedelta(days=days_back)

        if metric == "volume":
            # Top products by sales volume from market data
            query = (
                select(
                    Product.id,
                    Product.name,
                    Product.sku,
                    Brand.name.label("brand_name"),
                    func.sum(MarketPrice.sales_volume).label("total_volume"),
                    func.avg(MarketPrice.last_sale).label("avg_sale_price"),
                )
                .select_from(MarketPrice)
                .join(Product, MarketPrice.product_id == Product.id)
                .join(Brand, Product.brand_id == Brand.id)
                .where(MarketPrice.price_date >= start_date, MarketPrice.sales_volume.is_not(None))
                .group_by(Product.id, Product.name, Product.sku, Brand.name)
                .order_by(desc("total_volume"))
                .limit(limit)
            )

        elif metric == "price_growth":
            # Top products by price appreciation
            subquery = (
                select(
                    PriceHistory.product_id,
                    func.first_value(PriceHistory.price_amount)
                    .over(
                        partition_by=PriceHistory.product_id, order_by=PriceHistory.price_date.asc()
                    )
                    .label("first_price"),
                    func.first_value(PriceHistory.price_amount)
                    .over(
                        partition_by=PriceHistory.product_id,
                        order_by=PriceHistory.price_date.desc(),
                    )
                    .label("latest_price"),
                )
                .where(PriceHistory.price_date >= start_date, PriceHistory.price_type == "listing")
                .subquery()
            )

            query = (
                select(
                    Product.id,
                    Product.name,
                    Product.sku,
                    Brand.name.label("brand_name"),
                    subquery.c.first_price,
                    subquery.c.latest_price,
                    (
                        (subquery.c.latest_price - subquery.c.first_price)
                        / subquery.c.first_price
                        * 100
                    ).label("price_growth_percent"),
                )
                .select_from(subquery)
                .join(Product, subquery.c.product_id == Product.id)
                .join(Brand, Product.brand_id == Brand.id)
                .where(subquery.c.first_price > 0)
                .order_by(desc("price_growth_percent"))
                .limit(limit)
            )

        result = await self.db.execute(query)
        rows = result.all()

        # Convert to list of dictionaries
        products = []
        for row in rows:
            product_dict = {
                "id": str(row.id),
                "name": row.name,
                "sku": row.sku,
                "brand": row.brand_name,
            }

            if metric == "volume":
                product_dict.update(
                    {
                        "total_volume": int(row.total_volume) if row.total_volume else 0,
                        "avg_sale_price": float(row.avg_sale_price) if row.avg_sale_price else 0,
                    }
                )
            elif metric == "price_growth":
                product_dict.update(
                    {
                        "first_price": float(row.first_price) if row.first_price else 0,
                        "latest_price": float(row.latest_price) if row.latest_price else 0,
                        "growth_percent": (
                            float(row.price_growth_percent) if row.price_growth_percent else 0
                        ),
                    }
                )

            products.append(product_dict)

        return products
