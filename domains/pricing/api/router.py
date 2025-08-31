"""
Pricing API Router - Smart pricing recommendations and market analysis
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domains.inventory.services.inventory_service import InventoryService
from shared.database.connection import get_db_session

from ..repositories.pricing_repository import PricingRepository
from ..services.pricing_engine import PricingContext, PricingEngine, PricingStrategy

logger = structlog.get_logger(__name__)

router = APIRouter()


# Pydantic models for API requests/responses
class PricingRequest(BaseModel):
    product_id: UUID
    inventory_id: Optional[UUID] = None
    strategy: Optional[PricingStrategy] = PricingStrategy.DYNAMIC
    target_margin: Optional[Decimal] = None
    condition: str = "new"
    size: Optional[str] = None


class PricingRecommendation(BaseModel):
    product_id: UUID
    suggested_price: Decimal
    strategy_used: str
    confidence_score: Decimal
    margin_percent: Decimal
    markup_percent: Decimal
    reasoning: List[str]
    market_position: Optional[str] = None
    price_range: Optional[Dict[str, Decimal]] = None


class MarketAnalysis(BaseModel):
    product_id: UUID
    current_market_price: Optional[Decimal]
    price_trend: str  # "increasing", "decreasing", "stable"
    market_position: str  # "below", "at", "above" market
    competitor_count: int
    demand_score: Decimal
    supply_score: Decimal
    recommended_action: str


def get_pricing_repository(db: AsyncSession = Depends(get_db_session)) -> PricingRepository:
    return PricingRepository(db)


def get_pricing_engine(db: AsyncSession = Depends(get_db_session)) -> PricingEngine:
    pricing_repo = PricingRepository(db)
    return PricingEngine(pricing_repo, db)


@router.post(
    "/recommend",
    summary="Get Pricing Recommendation",
    description="Get AI-powered pricing recommendations for a product using advanced algorithms",
    response_model=PricingRecommendation,
)
async def get_pricing_recommendation(
    request: PricingRequest,
    pricing_engine: PricingEngine = Depends(get_pricing_engine),
    db: AsyncSession = Depends(get_db_session),
):
    """Get intelligent pricing recommendation for a product"""
    logger.info(
        "Received pricing recommendation request",
        product_id=str(request.product_id),
        strategy=request.strategy.value,
    )

    try:
        # Get product and inventory data
        from sqlalchemy import select

        from shared.database.models import InventoryItem, Product

        # Fetch product
        product_result = await db.execute(select(Product).where(Product.id == request.product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Fetch inventory item if provided
        inventory_item = None
        if request.inventory_id:
            inventory_result = await db.execute(
                select(InventoryItem).where(InventoryItem.id == request.inventory_id)
            )
            inventory_item = inventory_result.scalar_one_or_none()

        # Create pricing context
        context = PricingContext(
            product=product,
            inventory_item=inventory_item,
            condition=request.condition,
            size=request.size,
            target_margin=request.target_margin,
        )

        # Get pricing recommendation
        result = await pricing_engine.calculate_optimal_price(
            context=context, strategy=request.strategy
        )

        return PricingRecommendation(
            product_id=request.product_id,
            suggested_price=result.suggested_price,
            strategy_used=result.strategy_used.value,
            confidence_score=result.confidence_score,
            margin_percent=result.margin_percent,
            markup_percent=result.markup_percent,
            reasoning=result.reasoning,
            market_position=result.market_position,
            price_range=result.price_range,
        )

    except Exception as e:
        logger.error(
            "Failed to generate pricing recommendation",
            product_id=str(request.product_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate pricing recommendation: {str(e)}"
        )


@router.get(
    "/market-analysis/{product_id}",
    summary="Get Market Analysis",
    description="Analyze market conditions and competitive landscape for a product",
    response_model=MarketAnalysis,
)
async def get_market_analysis(
    product_id: UUID,
    pricing_engine: PricingEngine = Depends(get_pricing_engine),
    db: AsyncSession = Depends(get_db_session),
):
    """Get comprehensive market analysis for a product"""
    logger.info("Fetching market analysis", product_id=str(product_id))

    try:
        # Get product
        from sqlalchemy import select

        from shared.database.models import Product

        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Get market analysis from pricing engine
        market_data = await pricing_engine.analyze_market_conditions(product)

        return MarketAnalysis(
            product_id=product_id,
            current_market_price=market_data.get("current_price"),
            price_trend=market_data.get("trend", "stable"),
            market_position=market_data.get("position", "unknown"),
            competitor_count=market_data.get("competitors", 0),
            demand_score=market_data.get("demand_score", Decimal("0.5")),
            supply_score=market_data.get("supply_score", Decimal("0.5")),
            recommended_action=market_data.get("recommended_action", "monitor"),
        )

    except Exception as e:
        logger.error(
            "Failed to fetch market analysis",
            product_id=str(product_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch market analysis: {str(e)}")


@router.get(
    "/strategies",
    summary="Get Available Pricing Strategies",
    description="List all available pricing strategies with descriptions",
)
async def get_pricing_strategies():
    """Get list of available pricing strategies"""
    strategies = {
        "cost_plus": {
            "name": "Cost Plus",
            "description": "Add fixed margin to product cost",
            "use_case": "Simple, predictable pricing",
        },
        "market_based": {
            "name": "Market Based",
            "description": "Price based on current market conditions",
            "use_case": "Competitive positioning",
        },
        "competitive": {
            "name": "Competitive",
            "description": "Price to beat or match competitors",
            "use_case": "Market penetration",
        },
        "value_based": {
            "name": "Value Based",
            "description": "Price based on perceived customer value",
            "use_case": "Premium positioning",
        },
        "dynamic": {
            "name": "Dynamic",
            "description": "AI-powered adaptive pricing",
            "use_case": "Maximum profit optimization",
        },
    }
    return strategies


@router.get(
    "/rules",
    summary="Get Pricing Rules",
    description="Get all active pricing rules and brand multipliers",
)
async def get_pricing_rules(pricing_repo: PricingRepository = Depends(get_pricing_repository)):
    """Get active pricing rules"""
    try:
        rules = await pricing_repo.get_active_rules()
        multipliers = await pricing_repo.get_brand_multipliers()

        return {
            "rules": [
                {
                    "id": str(rule.id),
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "conditions": rule.conditions,
                    "actions": rule.actions,
                    "priority": rule.priority,
                    "is_active": rule.is_active,
                }
                for rule in rules
            ],
            "brand_multipliers": [
                {
                    "brand_id": str(mult.brand_id),
                    "brand_name": mult.brand.name if mult.brand else "Unknown",
                    "multiplier": float(mult.multiplier),
                    "category": mult.category,
                    "condition": mult.condition,
                }
                for mult in multipliers
            ],
        }

    except Exception as e:
        logger.error("Failed to fetch pricing rules", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pricing rules: {str(e)}")


@router.get(
    "/insights",
    summary="Get Pricing Insights",
    description="Get overall pricing performance and insights",
)
async def get_pricing_insights(
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    db: AsyncSession = Depends(get_db_session),
):
    """Get pricing performance insights"""
    try:
        from sqlalchemy import text

        # Get pricing performance metrics
        insights_query = text(
            """
            SELECT 
                COUNT(DISTINCT p.id) as total_products_analyzed,
                AVG(ph.price) as avg_price,
                AVG(CASE 
                    WHEN i.purchase_price IS NOT NULL AND i.purchase_price > 0 
                    THEN ((ph.price - i.purchase_price) / i.purchase_price) * 100 
                END) as avg_margin_percent,
                COUNT(ph.id) as total_price_updates,
                COUNT(CASE WHEN ph.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as recent_updates
            FROM pricing.price_history ph
            LEFT JOIN products.products p ON ph.product_id = p.id
            LEFT JOIN products.inventory i ON p.id = i.product_id
            WHERE ph.created_at >= NOW() - INTERVAL '90 days'
        """
        )

        result = await db.execute(insights_query)
        metrics = result.fetchone()

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_products_analyzed": metrics.total_products_analyzed or 0,
                "average_price": float(metrics.avg_price or 0),
                "average_margin_percent": float(metrics.avg_margin_percent or 0),
                "total_price_updates": metrics.total_price_updates or 0,
                "recent_updates_30d": metrics.recent_updates or 0,
            },
            "recommendations": [
                "Monitor margin trends weekly",
                "Update pricing rules based on market conditions",
                "Consider dynamic pricing for high-value items",
            ],
        }

    except Exception as e:
        logger.error("Failed to fetch pricing insights", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pricing insights: {str(e)}")
