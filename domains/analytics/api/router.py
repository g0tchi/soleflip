"""
Analytics & Forecast API Router - Advanced sales forecasting and predictive analytics
"""

from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from decimal import Decimal
import structlog
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from enum import Enum

from shared.database.connection import get_db_session
from ..services.forecast_engine import ForecastEngine, ForecastModel, ForecastHorizon
from ..repositories.forecast_repository import ForecastRepository

logger = structlog.get_logger(__name__)

router = APIRouter()


# Pydantic models for API requests/responses
class ForecastRequest(BaseModel):
    product_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    horizon_days: int = 30
    model: Optional[ForecastModel] = ForecastModel.ENSEMBLE
    confidence_level: float = 0.95


class SalesForecast(BaseModel):
    target_id: UUID
    target_type: str  # "product", "brand", "category"
    forecast_date: date
    horizon_days: int
    predicted_sales: Decimal
    predicted_revenue: Decimal
    confidence_interval_lower: Decimal
    confidence_interval_upper: Decimal
    model_used: str
    accuracy_score: Optional[Decimal] = None
    trend: str  # "increasing", "decreasing", "stable"
    seasonality_factor: Optional[Decimal] = None


class ForecastAnalysis(BaseModel):
    forecast: SalesForecast
    historical_data: List[Dict[str, Any]]
    key_insights: List[str]
    recommendations: List[str]
    model_performance: Dict[str, Any]


class MarketTrend(BaseModel):
    period: str
    trend_direction: str
    strength: Decimal  # 0-1 scale
    key_drivers: List[str]
    forecast_impact: str


def get_forecast_repository(db: AsyncSession = Depends(get_db_session)) -> ForecastRepository:
    return ForecastRepository(db)


def get_forecast_engine(db: AsyncSession = Depends(get_db_session)) -> ForecastEngine:
    forecast_repo = ForecastRepository(db)
    return ForecastEngine(forecast_repo, db)


@router.post(
    "/forecast/sales",
    summary="Generate Sales Forecast",
    description="Generate AI-powered sales forecasts using advanced ML models",
    response_model=ForecastAnalysis,
)
async def generate_sales_forecast(
    request: ForecastRequest,
    forecast_engine: ForecastEngine = Depends(get_forecast_engine),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate comprehensive sales forecast with analysis"""
    logger.info(
        "Received sales forecast request",
        product_id=str(request.product_id) if request.product_id else None,
        brand_id=str(request.brand_id) if request.brand_id else None,
        horizon_days=request.horizon_days,
    )

    try:
        # Determine forecast horizon
        if request.horizon_days <= 7:
            horizon = ForecastHorizon.SHORT_TERM
        elif request.horizon_days <= 30:
            horizon = ForecastHorizon.MEDIUM_TERM
        else:
            horizon = ForecastHorizon.LONG_TERM

        # Generate forecast based on target type
        if request.product_id:
            # Product-level forecast
            from shared.database.models import Product
            from sqlalchemy import select

            product_result = await db.execute(
                select(Product).where(Product.id == request.product_id)
            )
            product = product_result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            forecast_result = await forecast_engine.forecast_product_sales(
                product=product,
                horizon=horizon,
                model=request.model,
                confidence_level=request.confidence_level,
            )

            target_id = request.product_id
            target_type = "product"

        elif request.brand_id:
            # Brand-level forecast
            forecast_result = await forecast_engine.forecast_brand_sales(
                brand_id=request.brand_id, horizon=horizon, model=request.model
            )

            target_id = request.brand_id
            target_type = "brand"

        elif request.category_id:
            # Category-level forecast
            forecast_result = await forecast_engine.forecast_category_sales(
                category_id=request.category_id, horizon=horizon, model=request.model
            )

            target_id = request.category_id
            target_type = "category"

        else:
            # Overall business forecast
            forecast_result = await forecast_engine.forecast_overall_sales(
                horizon=horizon, model=request.model
            )

            target_id = UUID("00000000-0000-0000-0000-000000000000")  # Null UUID for overall
            target_type = "overall"

        # Get historical data for context
        historical_data = await forecast_engine.get_historical_sales_data(
            target_id=target_id, target_type=target_type, days_back=90
        )

        # Create forecast response
        forecast = SalesForecast(
            target_id=target_id,
            target_type=target_type,
            forecast_date=date.today(),
            horizon_days=request.horizon_days,
            predicted_sales=forecast_result.predicted_quantity,
            predicted_revenue=forecast_result.predicted_revenue,
            confidence_interval_lower=forecast_result.confidence_interval[0],
            confidence_interval_upper=forecast_result.confidence_interval[1],
            model_used=forecast_result.model_used.value,
            accuracy_score=forecast_result.accuracy_score,
            trend=forecast_result.trend_direction,
            seasonality_factor=forecast_result.seasonality_factor,
        )

        return ForecastAnalysis(
            forecast=forecast,
            historical_data=historical_data,
            key_insights=forecast_result.key_insights,
            recommendations=forecast_result.recommendations,
            model_performance=forecast_result.model_metrics,
        )

    except Exception as e:
        logger.error("Failed to generate sales forecast", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate sales forecast: {str(e)}")


@router.get(
    "/trends/market",
    summary="Get Market Trends",
    description="Analyze market trends and seasonal patterns",
    response_model=List[MarketTrend],
)
async def get_market_trends(
    days_back: int = Query(90, description="Number of days to analyze"),
    forecast_engine: ForecastEngine = Depends(get_forecast_engine),
):
    """Get comprehensive market trend analysis"""
    logger.info("Fetching market trends", days_back=days_back)

    try:
        trends = await forecast_engine.analyze_market_trends(days_back=days_back)

        return [
            MarketTrend(
                period=trend.get("period", "unknown"),
                trend_direction=trend.get("direction", "stable"),
                strength=Decimal(str(trend.get("strength", 0.5))),
                key_drivers=trend.get("drivers", []),
                forecast_impact=trend.get("impact", "neutral"),
            )
            for trend in trends
        ]

    except Exception as e:
        logger.error("Failed to fetch market trends", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch market trends: {str(e)}")


@router.get(
    "/models",
    summary="Get Available Forecast Models",
    description="List all available forecasting models with capabilities",
)
async def get_forecast_models():
    """Get list of available forecasting models"""
    models = {
        "linear_trend": {
            "name": "Linear Trend",
            "description": "Simple linear trend analysis",
            "best_for": "Short-term trends with consistent growth",
            "accuracy": "Medium",
            "speed": "Fast",
        },
        "seasonal_naive": {
            "name": "Seasonal Naive",
            "description": "Seasonal pattern recognition",
            "best_for": "Products with strong seasonality",
            "accuracy": "Medium",
            "speed": "Fast",
        },
        "exponential_smoothing": {
            "name": "Exponential Smoothing",
            "description": "Weighted historical data analysis",
            "best_for": "Medium-term forecasting",
            "accuracy": "High",
            "speed": "Medium",
        },
        "arima": {
            "name": "ARIMA",
            "description": "Advanced time series analysis",
            "best_for": "Complex trend and seasonal patterns",
            "accuracy": "High",
            "speed": "Slow",
        },
        "random_forest": {
            "name": "Random Forest",
            "description": "Machine learning ensemble method",
            "best_for": "Multi-factor forecasting",
            "accuracy": "Very High",
            "speed": "Medium",
        },
        "gradient_boost": {
            "name": "Gradient Boosting",
            "description": "Advanced ML gradient optimization",
            "best_for": "Complex non-linear patterns",
            "accuracy": "Very High",
            "speed": "Slow",
        },
        "ensemble": {
            "name": "Ensemble",
            "description": "Combination of multiple models",
            "best_for": "Maximum accuracy across all scenarios",
            "accuracy": "Highest",
            "speed": "Slow",
        },
    }
    return models


@router.get(
    "/performance/models",
    summary="Get Model Performance Metrics",
    description="Get accuracy metrics for all forecasting models",
)
async def get_model_performance(
    forecast_repo: ForecastRepository = Depends(get_forecast_repository),
):
    """Get model performance metrics"""
    try:
        performance_data = await forecast_repo.get_model_accuracy_metrics()

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model_performance": [
                {
                    "model_name": perf.model_name,
                    "accuracy_score": float(perf.accuracy_score),
                    "mae": float(perf.mae),
                    "rmse": float(perf.rmse),
                    "mape": float(perf.mape),
                    "predictions_count": perf.predictions_count,
                    "last_updated": perf.updated_at.isoformat() + "Z",
                }
                for perf in performance_data
            ],
        }

    except Exception as e:
        logger.error("Failed to fetch model performance", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch model performance: {str(e)}")


@router.get(
    "/insights/predictive",
    summary="Get Predictive Analytics Insights",
    description="Get AI-powered business insights and recommendations",
)
async def get_predictive_insights(
    forecast_engine: ForecastEngine = Depends(get_forecast_engine),
    db: AsyncSession = Depends(get_db_session),
):
    """Get comprehensive predictive analytics insights"""
    try:
        from sqlalchemy import text

        # Get overall business metrics for insights
        insights_query = text(
            """
            SELECT 
                COUNT(DISTINCT t.id) as total_transactions_90d,
                SUM(t.sale_price) as total_revenue_90d,
                AVG(t.sale_price) as avg_transaction_value,
                COUNT(DISTINCT p.id) as active_products,
                COUNT(DISTINCT b.id) as active_brands
            FROM sales.transactions t
            LEFT JOIN products.inventory i ON t.inventory_id = i.id
            LEFT JOIN products.products p ON i.product_id = p.id
            LEFT JOIN core.brands b ON p.brand_id = b.id
            WHERE t.created_at >= NOW() - INTERVAL '90 days'
            AND t.sale_price IS NOT NULL
        """
        )

        result = await db.execute(insights_query)
        metrics = result.fetchone()

        # Generate AI insights
        insights = await forecast_engine.generate_predictive_insights(
            transaction_count=metrics.total_transactions_90d or 0,
            revenue=float(metrics.total_revenue_90d or 0),
            avg_value=float(metrics.avg_transaction_value or 0),
            product_count=metrics.active_products or 0,
            brand_count=metrics.active_brands or 0,
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "business_metrics": {
                "transactions_90d": metrics.total_transactions_90d or 0,
                "revenue_90d": float(metrics.total_revenue_90d or 0),
                "avg_transaction_value": float(metrics.avg_transaction_value or 0),
                "active_products": metrics.active_products or 0,
                "active_brands": metrics.active_brands or 0,
            },
            "predictive_insights": insights.get("insights", []),
            "growth_opportunities": insights.get("opportunities", []),
            "risk_factors": insights.get("risks", []),
            "recommendations": insights.get("recommendations", []),
            "confidence_score": insights.get("confidence", 0.7),
        }

    except Exception as e:
        logger.error("Failed to generate predictive insights", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate predictive insights: {str(e)}"
        )
