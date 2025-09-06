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
from ..services.smart_pricing_service import SmartPricingService

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


# =====================================================
# SMART PRICING ENDPOINTS
# =====================================================

@router.post(
    "/smart/optimize-inventory",
    summary="Smart Inventory Pricing Optimization", 
    description="Optimize pricing for entire inventory using AI and real-time StockX market data"
)
async def optimize_inventory_pricing(
    strategy: str = Query("profit_maximization", description="Repricing strategy: profit_maximization, market_competitive, quick_turnover, premium_positioning"),
    limit: int = Query(50, description="Maximum items to optimize (1-100)"),
    db_session: AsyncSession = Depends(get_db_session)
):
    """Optimize pricing for inventory using smart algorithms"""
    logger.info("Starting smart inventory pricing optimization", strategy=strategy, limit=limit)
    
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    try:
        smart_pricing = SmartPricingService(db_session)
        
        # Get inventory items to optimize
        inventory_service = InventoryService(db_session)
        items = await inventory_service.get_items_for_repricing(limit=limit)
        
        # Run optimization
        optimization_result = await smart_pricing.optimize_inventory_pricing(
            inventory_items=items,
            repricing_strategy=strategy
        )
        
        return {
            "success": True,
            "message": f"Optimized pricing for {optimization_result['successful_optimizations']} items",
            "data": optimization_result
        }
        
    except Exception as e:
        logger.error("Smart pricing optimization failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get(
    "/smart/recommend/{item_id}",
    summary="Get Smart Price Recommendation",
    description="Get AI-powered price recommendation for specific inventory item with market analysis"
)
async def get_smart_price_recommendation(
    item_id: UUID,
    target_days: Optional[int] = Query(None, description="Target sell timeframe in days"),
    db_session: AsyncSession = Depends(get_db_session)
):
    """Get intelligent price recommendation for specific item"""
    logger.info("Getting smart price recommendation", item_id=str(item_id))
    
    try:
        inventory_service = InventoryService(db_session)
        inventory_item = await inventory_service.get_item_by_id(item_id)
        
        if not inventory_item:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        
        smart_pricing = SmartPricingService(db_session)
        recommendation = await smart_pricing.get_dynamic_price_recommendation(
            inventory_item=inventory_item,
            target_sell_timeframe=target_days
        )
        
        return {
            "success": True,
            "message": "Price recommendation generated successfully", 
            "data": recommendation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get price recommendation", item_id=str(item_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.post(
    "/smart/auto-reprice",
    summary="Implement Automatic Repricing",
    description="Automatically reprice inventory based on market movements and custom rules"
)
async def implement_auto_repricing(
    dry_run: bool = Query(True, description="Run simulation without actual price changes"),
    price_drop_threshold: float = Query(5.0, description="Price drop % to trigger repricing"),
    max_increase: float = Query(10.0, description="Maximum price increase % per adjustment"),
    min_margin: float = Query(15.0, description="Minimum profit margin to maintain"),
    db_session: AsyncSession = Depends(get_db_session)
):
    """Implement automatic repricing based on market conditions"""
    logger.info("Starting auto-repricing", dry_run=dry_run)
    
    try:
        repricing_rules = {
            "price_drop_threshold": price_drop_threshold,
            "max_price_increase": max_increase,
            "min_margin_percent": min_margin,
            "check_interval_hours": 6,
            "enabled_categories": ["footwear", "streetwear", "accessories"]
        }
        
        smart_pricing = SmartPricingService(db_session)
        repricing_result = await smart_pricing.implement_auto_repricing(
            repricing_rules=repricing_rules,
            dry_run=dry_run
        )
        
        return {
            "success": True,
            "message": f"Auto-repricing {'simulated' if dry_run else 'completed'}: {repricing_result['total_adjustments']} adjustments made",
            "data": repricing_result
        }
        
    except Exception as e:
        logger.error("Auto-repricing failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Auto-repricing failed: {str(e)}")


@router.get(
    "/smart/market-trends",
    summary="Analyze Market Trends",
    description="Analyze market trends for pricing insights and investment opportunities"
)
async def analyze_market_trends(
    days: int = Query(30, description="Time horizon in days (7-90)"),
    limit: int = Query(20, description="Number of products to analyze (1-50)"),
    db_session: AsyncSession = Depends(get_db_session)
):
    """Analyze market trends for strategic pricing insights"""
    logger.info("Analyzing market trends", days=days, limit=limit)
    
    if days < 7 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 7 and 90")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
    
    try:
        smart_pricing = SmartPricingService(db_session)
        trends_analysis = await smart_pricing.analyze_market_trends(
            time_horizon_days=days
        )
        
        return {
            "success": True,
            "message": f"Market trends analyzed for {len(trends_analysis['product_trends'])} products",
            "data": trends_analysis
        }
        
    except Exception as e:
        logger.error("Market trends analysis failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trends analysis failed: {str(e)}")


@router.get(
    "/smart/profit-forecast",
    summary="Profit Optimization Forecast",
    description="Forecast potential profit improvements with smart pricing strategies"
)
async def get_profit_forecast(
    strategy: str = Query("profit_maximization", description="Optimization strategy"),
    timeframe_days: int = Query(30, description="Forecast timeframe in days"),
    db_session: AsyncSession = Depends(get_db_session)
):
    """Generate profit optimization forecast"""
    logger.info("Generating profit forecast", strategy=strategy, timeframe=timeframe_days)
    
    try:
        smart_pricing = SmartPricingService(db_session)
        inventory_service = InventoryService(db_session)
        
        # Get current inventory value
        inventory_summary = await inventory_service.get_detailed_summary()
        current_value = inventory_summary.get("total_value", 0)
        
        # Simulate optimization on sample of inventory
        sample_items = await inventory_service.get_items_for_repricing(limit=20)
        optimization_sample = await smart_pricing.optimize_inventory_pricing(
            inventory_items=sample_items,
            repricing_strategy=strategy
        )
        
        # Extrapolate results
        if optimization_sample["total_items_processed"] > 0:
            avg_improvement = optimization_sample["potential_profit_increase"] / optimization_sample["total_items_processed"]
            total_inventory_items = inventory_summary.get("total_items", 1)
            projected_improvement = avg_improvement * total_inventory_items
        else:
            projected_improvement = 0
        
        forecast = {
            "current_inventory_value": float(current_value),
            "projected_profit_increase": float(projected_improvement),
            "projected_improvement_percent": round((projected_improvement / max(current_value, 1)) * 100, 2),
            "strategy_used": strategy,
            "forecast_timeframe_days": timeframe_days,
            "confidence_level": "medium",  # Based on sample size
            "sample_results": optimization_sample
        }
        
        return {
            "success": True,
            "message": f"Profit forecast generated: ${projected_improvement:.2f} potential increase",
            "data": forecast
        }
        
    except Exception as e:
        logger.error("Profit forecast failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


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


# Smart Pricing Auto-Repricing Status and Control Endpoints
@router.get(
    "/smart/auto-repricing/status",
    summary="Get Auto-Repricing Status",
    description="Get current status of the auto-repricing system"
)
async def get_auto_repricing_status(
    db_session: AsyncSession = Depends(get_db_session)
):
    """Get auto-repricing system status"""
    logger.info("Getting auto-repricing status")
    
    try:
        smart_pricing = SmartPricingService(db_session)
        status = await smart_pricing.get_auto_repricing_status()
        
        return {
            "enabled": status.get("enabled", False),
            "last_run": status.get("last_run"),
            "items_repriced": status.get("items_repriced", 0),
            "strategy": status.get("strategy", "profit_maximization"),
            "next_run": status.get("next_run"),
            "rules_applied": status.get("rules_applied", 0)
        }
        
    except Exception as e:
        logger.error("Failed to get auto-repricing status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get auto-repricing status: {str(e)}")


class AutoRepricingToggleRequest(BaseModel):
    enabled: bool


@router.post(
    "/smart/auto-repricing/toggle",
    summary="Toggle Auto-Repricing",
    description="Enable or disable the auto-repricing system"
)
async def toggle_auto_repricing(
    request: AutoRepricingToggleRequest,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Toggle auto-repricing system on/off"""
    logger.info("Toggling auto-repricing", enabled=request.enabled)
    
    try:
        smart_pricing = SmartPricingService(db_session)
        result = await smart_pricing.toggle_auto_repricing(request.enabled)
        
        return {
            "success": True,
            "enabled": result.get("enabled", request.enabled),
            "message": f"Auto-repricing {'enabled' if request.enabled else 'disabled'} successfully"
        }
        
    except Exception as e:
        logger.error("Failed to toggle auto-repricing", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to toggle auto-repricing: {str(e)}")
