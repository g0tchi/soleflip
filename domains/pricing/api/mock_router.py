"""
Mock Pricing & Analytics API Router - Temporary endpoints with sample data
"""

from typing import Dict, Any, List
import structlog
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter()


# Mock response models
class MockPricingInsights(BaseModel):
    timestamp: str
    summary: Dict[str, Any]
    recommendations: List[str]


class MockPredictiveInsights(BaseModel):
    timestamp: str
    business_metrics: Dict[str, Any]
    predictive_insights: List[str]
    growth_opportunities: List[str]
    risk_factors: List[str]
    recommendations: List[str]
    confidence_score: float


class MockMarketTrend(BaseModel):
    period: str
    trend_direction: str
    strength: float
    key_drivers: List[str]
    forecast_impact: str


@router.get("/insights", response_model=MockPricingInsights)
async def get_pricing_insights():
    """Mock pricing insights endpoint"""
    return MockPricingInsights(
        timestamp=datetime.utcnow().isoformat() + "Z",
        summary={
            "total_products_analyzed": 853,
            "average_price": 95.50,
            "average_margin_percent": 24.5,
            "total_price_updates": 127,
            "recent_updates_30d": 23,
        },
        recommendations=[
            "Consider dynamic pricing for high-demand items",
            "Review pricing strategy for low-margin products",
            "Optimize seasonal pricing adjustments",
        ],
    )


@router.get("/strategies")
async def get_pricing_strategies():
    """Mock pricing strategies endpoint"""
    return {
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
        "dynamic": {
            "name": "Dynamic",
            "description": "AI-powered adaptive pricing",
            "use_case": "Maximum profit optimization",
        },
    }
