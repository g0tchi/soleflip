"""
Mock Analytics API Router - Temporary endpoints with sample data
"""

from datetime import datetime
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter()


# Mock response models
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


@router.get("/insights/predictive", response_model=MockPredictiveInsights)
async def get_predictive_insights():
    """Mock predictive insights endpoint"""
    return MockPredictiveInsights(
        timestamp=datetime.utcnow().isoformat() + "Z",
        business_metrics={
            "transactions_90d": 2250,
            "revenue_90d": 187500.00,
            "avg_transaction_value": 83.33,
            "active_products": 853,
            "active_brands": 42,
        },
        predictive_insights=[
            "Sales velocity increasing by 12% month-over-month",
            "Premium sneaker segment showing strong demand growth",
            "Brand diversification strategy yielding positive results",
            "Market conditions favorable for inventory expansion",
        ],
        growth_opportunities=[
            "Expand into emerging streetwear categories",
            "Optimize pricing for high-demand vintage items",
            "Leverage social media trends for product selection",
            "Partner with influencers for brand awareness",
        ],
        risk_factors=[
            "Market saturation in popular sneaker categories",
            "Seasonal demand fluctuations approaching",
            "Supply chain disruptions in key markets",
        ],
        recommendations=[
            "Diversify product portfolio across price ranges",
            "Implement dynamic pricing for trending items",
            "Build strategic inventory reserves",
            "Monitor competitor pricing strategies closely",
        ],
        confidence_score=0.87,
    )


@router.get("/trends/market", response_model=List[MockMarketTrend])
async def get_market_trends(days_back: int = Query(90)):
    """Mock market trends endpoint"""
    return [
        MockMarketTrend(
            period="Q4 2024",
            trend_direction="increasing",
            strength=0.78,
            key_drivers=["Holiday season", "Limited releases", "Celebrity endorsements"],
            forecast_impact="positive",
        ),
        MockMarketTrend(
            period="Sneaker Resale",
            trend_direction="stable",
            strength=0.65,
            key_drivers=["Consistent demand", "Market maturation"],
            forecast_impact="neutral",
        ),
        MockMarketTrend(
            period="Vintage Items",
            trend_direction="increasing",
            strength=0.89,
            key_drivers=["Nostalgia trend", "Scarcity premium"],
            forecast_impact="positive",
        ),
        MockMarketTrend(
            period="Luxury Brands",
            trend_direction="increasing",
            strength=0.72,
            key_drivers=["Premium positioning", "Brand exclusivity"],
            forecast_impact="positive",
        ),
        MockMarketTrend(
            period="Seasonal Items",
            trend_direction="decreasing",
            strength=0.45,
            key_drivers=["End of season", "Weather patterns"],
            forecast_impact="negative",
        ),
        MockMarketTrend(
            period="Collaborations",
            trend_direction="increasing",
            strength=0.91,
            key_drivers=["Hype culture", "Limited availability"],
            forecast_impact="very_positive",
        ),
    ]


@router.get("/models")
async def get_forecast_models():
    """Mock forecast models endpoint"""
    return {
        "ensemble": {
            "name": "Ensemble",
            "description": "Combination of multiple ML models",
            "best_for": "Maximum accuracy across all scenarios",
            "accuracy": "Highest",
            "speed": "Medium",
        },
        "random_forest": {
            "name": "Random Forest",
            "description": "Machine learning ensemble method",
            "best_for": "Multi-factor forecasting",
            "accuracy": "Very High",
            "speed": "Fast",
        },
        "linear_trend": {
            "name": "Linear Trend",
            "description": "Simple linear trend analysis",
            "best_for": "Short-term trends with consistent growth",
            "accuracy": "Medium",
            "speed": "Very Fast",
        },
    }
