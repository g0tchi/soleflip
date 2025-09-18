"""
QuickFlip Detection Service
Identifies arbitrage opportunities by comparing market prices with StockX selling prices
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Product, MarketPrice
from shared.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


@dataclass
class QuickFlipOpportunity:
    """Data class for QuickFlip opportunities"""

    product_id: UUID
    product_name: str
    product_sku: str
    brand_name: str

    # Market price info (where to buy)
    buy_price: Decimal
    buy_source: str
    buy_supplier: str
    buy_url: Optional[str]
    buy_stock_qty: Optional[int]

    # StockX info (where to sell)
    sell_price: Decimal
    stockx_listing_id: Optional[str]

    # Profit calculations
    gross_profit: Decimal
    profit_margin: float
    roi: float  # Return on Investment

    # Risk factors
    days_since_last_sale: Optional[int]
    stockx_demand_score: Optional[float]

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "product_id": str(self.product_id),
            "product_name": self.product_name,
            "product_sku": self.product_sku,
            "brand_name": self.brand_name,
            "buy_price": float(self.buy_price),
            "buy_source": self.buy_source,
            "buy_supplier": self.buy_supplier,
            "buy_url": self.buy_url,
            "buy_stock_qty": self.buy_stock_qty,
            "sell_price": float(self.sell_price),
            "stockx_listing_id": self.stockx_listing_id,
            "gross_profit": float(self.gross_profit),
            "profit_margin": self.profit_margin,
            "roi": self.roi,
            "days_since_last_sale": self.days_since_last_sale,
            "stockx_demand_score": self.stockx_demand_score,
        }


class QuickFlipDetectionService:
    """Service for detecting profitable arbitrage opportunities"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.market_price_repo = BaseRepository(MarketPrice, db_session)
        self.product_repo = BaseRepository(Product, db_session)
        self.logger = logger.bind(service="quickflip_detection")

    async def find_opportunities(
        self,
        min_profit_margin: float = 10.0,  # Minimum 10% profit margin
        min_gross_profit: Decimal = Decimal("20.00"),  # Minimum €20 gross profit
        max_buy_price: Optional[Decimal] = None,
        sources: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[QuickFlipOpportunity]:
        """
        Find QuickFlip opportunities based on specified criteria

        Args:
            min_profit_margin: Minimum profit margin percentage
            min_gross_profit: Minimum absolute profit amount
            max_buy_price: Maximum buy price filter
            sources: Specific sources to consider (e.g., ['awin', 'webgains'])
            limit: Maximum number of opportunities to return
        """
        self.logger.info(
            "Starting QuickFlip opportunity search",
            min_profit_margin=min_profit_margin,
            min_gross_profit=float(min_gross_profit),
            max_buy_price=float(max_buy_price) if max_buy_price else None,
            sources=sources,
            limit=limit
        )

        # Build the main query with JOINs
        query = (
            select(MarketPrice)
            .options(
                selectinload(MarketPrice.product).selectinload(Product.brand)
            )
            .join(Product, MarketPrice.product_id == Product.id)
        )

        # Apply filters
        conditions = []

        # Only products with resale price data
        conditions.append(Product.avg_resale_price.isnot(None))
        conditions.append(Product.avg_resale_price > 0)

        # Source filter
        if sources:
            conditions.append(MarketPrice.source.in_(sources))

        # Max buy price filter
        if max_buy_price:
            conditions.append(MarketPrice.buy_price <= max_buy_price)

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Order by most recent prices first
        query = query.order_by(desc(MarketPrice.last_updated))

        # Execute query
        result = await self.db_session.execute(query)
        market_prices = result.scalars().all()

        opportunities = []
        for market_price in market_prices:
            try:
                opportunity = await self._calculate_opportunity(market_price)

                # Apply profit filters
                if (opportunity.profit_margin >= min_profit_margin and
                    opportunity.gross_profit >= min_gross_profit):
                    opportunities.append(opportunity)

            except Exception as e:
                self.logger.warning(
                    "Error calculating opportunity",
                    product_id=str(market_price.product_id),
                    error=str(e)
                )

        # Sort by profit margin (highest first)
        opportunities.sort(key=lambda x: x.profit_margin, reverse=True)

        # Apply limit
        opportunities = opportunities[:limit]

        self.logger.info(
            "QuickFlip opportunity search completed",
            total_found=len(opportunities),
            avg_profit_margin=sum(o.profit_margin for o in opportunities) / len(opportunities) if opportunities else 0
        )

        return opportunities

    async def _calculate_opportunity(self, market_price: MarketPrice) -> QuickFlipOpportunity:
        """Calculate opportunity metrics from MarketPrice object"""

        product = market_price.product
        if not product or not product.avg_resale_price:
            raise ValueError("Product or resale price not available")

        buy_price = market_price.buy_price
        sell_price = product.avg_resale_price

        # Basic profit calculations
        gross_profit = sell_price - buy_price
        profit_margin = float((gross_profit / buy_price) * 100) if buy_price > 0 else 0
        roi = float((gross_profit / buy_price) * 100) if buy_price > 0 else 0

        # Get brand name
        brand_name = product.brand.name if product.brand else "Unknown"

        return QuickFlipOpportunity(
            product_id=market_price.product_id,
            product_name=product.name,
            product_sku=product.sku,
            brand_name=brand_name,
            buy_price=buy_price,
            buy_source=market_price.source,
            buy_supplier=market_price.supplier_name,
            buy_url=market_price.product_url,
            buy_stock_qty=market_price.stock_qty,
            sell_price=sell_price,
            stockx_listing_id=None,  # TODO: Add StockX listing ID when available
            gross_profit=gross_profit,
            profit_margin=profit_margin,
            roi=roi,
            days_since_last_sale=None,  # TODO: Calculate from transaction history
            stockx_demand_score=None   # TODO: Calculate demand score
        )

    async def get_opportunity_by_product(
        self,
        product_id: UUID
    ) -> List[QuickFlipOpportunity]:
        """Get all opportunities for a specific product"""

        opportunities = await self.find_opportunities(
            min_profit_margin=0,  # No minimum to see all
            min_gross_profit=Decimal("0"),
            limit=1000
        )

        return [opp for opp in opportunities if opp.product_id == product_id]

    async def get_best_opportunities_by_source(
        self,
        source: str,
        limit: int = 20
    ) -> List[QuickFlipOpportunity]:
        """Get best opportunities from a specific source"""

        return await self.find_opportunities(
            sources=[source],
            limit=limit
        )

    async def get_opportunities_summary(self) -> Dict:
        """Get summary statistics about opportunities"""

        # Get all opportunities without filters
        all_opportunities = await self.find_opportunities(
            min_profit_margin=0,
            min_gross_profit=Decimal("0"),
            limit=10000
        )

        if not all_opportunities:
            return {
                "total_opportunities": 0,
                "avg_profit_margin": 0,
                "avg_gross_profit": 0,
                "best_opportunity": None,
                "sources_breakdown": {}
            }

        # Calculate summary stats
        profit_margins = [opp.profit_margin for opp in all_opportunities]
        gross_profits = [float(opp.gross_profit) for opp in all_opportunities]

        # Group by source
        sources_breakdown = {}
        for opp in all_opportunities:
            source = opp.buy_source
            if source not in sources_breakdown:
                sources_breakdown[source] = {
                    "count": 0,
                    "avg_profit_margin": 0,
                    "best_margin": 0
                }

            sources_breakdown[source]["count"] += 1
            sources_breakdown[source]["best_margin"] = max(
                sources_breakdown[source]["best_margin"],
                opp.profit_margin
            )

        # Calculate average profit margins by source
        for source in sources_breakdown:
            source_opportunities = [opp for opp in all_opportunities if opp.buy_source == source]
            avg_margin = sum(opp.profit_margin for opp in source_opportunities) / len(source_opportunities)
            sources_breakdown[source]["avg_profit_margin"] = round(avg_margin, 2)

        return {
            "total_opportunities": len(all_opportunities),
            "avg_profit_margin": round(sum(profit_margins) / len(profit_margins), 2),
            "avg_gross_profit": round(sum(gross_profits) / len(gross_profits), 2),
            "best_opportunity": all_opportunities[0].to_dict() if all_opportunities else None,
            "sources_breakdown": sources_breakdown
        }

    async def mark_opportunity_as_acted(
        self,
        product_id: UUID,
        source: str,
        action: str = "purchased"
    ) -> bool:
        """Mark an opportunity as acted upon (for tracking)"""

        # TODO: Implement tracking table for acted opportunities
        # This could store when opportunities were acted upon to avoid suggesting the same ones

        self.logger.info(
            "Opportunity marked as acted upon",
            product_id=str(product_id),
            source=source,
            action=action
        )

        return True