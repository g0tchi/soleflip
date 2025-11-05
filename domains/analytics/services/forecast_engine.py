"""
Forecast Engine - Advanced sales forecasting with multiple ML models
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

# ML and statistics imports
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("sklearn not available. ML models will be disabled.")

try:
    from statsmodels.tsa.arima.model import ARIMA

    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.warning("statsmodels not available. Time series models will be limited.")


from ..repositories.forecast_repository import ForecastRepository


class ForecastModel(Enum):
    """Available forecasting models"""

    LINEAR_TREND = "linear_trend"
    SEASONAL_NAIVE = "seasonal_naive"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    ARIMA = "arima"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOST = "gradient_boost"
    ENSEMBLE = "ensemble"


class ForecastHorizon(Enum):
    """Forecast time horizons"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ForecastLevel(Enum):
    """Forecast aggregation levels"""

    PRODUCT = "product"
    BRAND = "brand"
    CATEGORY = "category"
    PLATFORM = "platform"


@dataclass
class ForecastConfig:
    """Configuration for forecasting models"""

    model: ForecastModel
    horizon: ForecastHorizon
    level: ForecastLevel
    prediction_days: int = 30
    confidence_level: float = 0.95
    min_history_days: int = 90
    seasonal_periods: Optional[int] = None
    features_to_include: List[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None


@dataclass
class ForecastResult:
    """Result of a forecasting operation"""

    entity_id: uuid.UUID
    entity_type: str
    predictions: List[Dict[str, Any]]
    model_name: str
    model_version: str
    confidence_intervals: List[Tuple[float, float]]
    feature_importance: Optional[Dict[str, float]] = None
    model_metrics: Optional[Dict[str, float]] = None
    warnings: List[str] = None


class ForecastEngine:
    """Advanced sales forecasting engine with multiple model support"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repository = ForecastRepository(db_session)
        self.logger = logging.getLogger(__name__)
        self.model_version = "1.0.0"

    # =====================================================
    # MAIN FORECASTING METHODS
    # =====================================================

    async def generate_forecasts(
        self,
        config: ForecastConfig,
        entity_ids: Optional[List[uuid.UUID]] = None,
        run_id: Optional[uuid.UUID] = None,
    ) -> List[ForecastResult]:
        """Generate forecasts for specified entities using given configuration"""
        if not run_id:
            run_id = uuid.uuid4()

        self.logger.info(f"Starting forecast generation with run_id: {run_id}")

        # Get entities to forecast
        if not entity_ids:
            entity_ids = await self._get_forecastable_entities(config.level)

        # PERFORMANCE OPTIMIZATION: Use list comprehension with error handling
        results = []
        async def safe_forecast(entity_id):
            try:
                result = await self._forecast_single_entity(config, entity_id, run_id)
                return result if result else None
            except Exception as e:
                self.logger.error(f"Failed to forecast entity {entity_id}: {str(e)}")
                return None
        
        # Process all entities and filter out None results
        forecast_results = [await safe_forecast(entity_id) for entity_id in entity_ids]
        results = [result for result in forecast_results if result is not None]

        # Store forecasts in database
        await self._store_forecast_results(results, run_id)

        self.logger.info(f"Completed forecast generation. Generated {len(results)} forecasts.")
        return results

    async def _forecast_single_entity(
        self, config: ForecastConfig, entity_id: uuid.UUID, run_id: uuid.UUID
    ) -> Optional[ForecastResult]:
        """Generate forecast for a single entity"""
        # Get historical data
        historical_data = await self.repository.get_historical_sales_data(
            entity_type=config.level.value,
            entity_id=entity_id,
            days_back=max(config.min_history_days, config.prediction_days * 3),
            aggregation=config.horizon.value,
        )

        if not historical_data or len(historical_data) < config.min_history_days // 7:
            self.logger.warning(f"Insufficient data for entity {entity_id}")
            return None

        # Prepare data for modeling
        df = self._prepare_training_data(historical_data, config)

        if df.empty:
            return None

        # Select and train model
        model_func = self._get_model_function(config.model)

        try:
            predictions, confidence_intervals, model_metrics, feature_importance = await model_func(
                df, config
            )
        except Exception as e:
            self.logger.error(f"Model {config.model.value} failed for entity {entity_id}: {str(e)}")
            return None

        # Format predictions
        prediction_list = self._format_predictions(predictions, confidence_intervals, config)

        return ForecastResult(
            entity_id=entity_id,
            entity_type=config.level.value,
            predictions=prediction_list,
            model_name=config.model.value,
            model_version=self.model_version,
            confidence_intervals=confidence_intervals,
            feature_importance=feature_importance,
            model_metrics=model_metrics,
        )

    # =====================================================
    # MODEL IMPLEMENTATIONS
    # =====================================================

    async def _linear_trend_model(
        self, df: pd.DataFrame, config: ForecastConfig
    ) -> Tuple[
        List[float], List[Tuple[float, float]], Dict[str, float], Optional[Dict[str, float]]
    ]:
        """Simple linear trend forecasting"""
        if len(df) < 10:
            raise ValueError("Insufficient data for linear trend model")

        # Prepare data
        df = df.sort_values("period_date").reset_index(drop=True)
        df["trend"] = range(len(df))

        y = df["units_sold"].values
        X = df[["trend"]].values

        if SKLEARN_AVAILABLE:
            model = LinearRegression()
            model.fit(X, y)

            # Generate predictions
            last_trend = df["trend"].iloc[-1]
            future_trends = np.arange(last_trend + 1, last_trend + 1 + config.prediction_days)
            predictions = model.predict(future_trends.reshape(-1, 1))

            # Calculate confidence intervals (simplified)
            residuals = y - model.predict(X)
            mse = np.mean(residuals**2)
            std_error = np.sqrt(mse)

            confidence_intervals = [
                (max(0, pred - 1.96 * std_error), pred + 1.96 * std_error) for pred in predictions
            ]

            # Model metrics
            train_pred = model.predict(X)
            metrics = {
                "r2_score": r2_score(y, train_pred),
                "mae": mean_absolute_error(y, train_pred),
                "rmse": np.sqrt(mean_squared_error(y, train_pred)),
            }
        else:
            # Fallback to simple numpy linear regression
            trend = df["trend"].values
            coeffs = np.polyfit(trend, y, 1)

            # Generate predictions
            last_trend = df["trend"].iloc[-1]
            future_trends = np.arange(last_trend + 1, last_trend + 1 + config.prediction_days)
            predictions = np.polyval(coeffs, future_trends)

            # Simple confidence intervals
            residuals = y - np.polyval(coeffs, trend)
            std_error = np.std(residuals)
            confidence_intervals = [
                (max(0, pred - 1.96 * std_error), pred + 1.96 * std_error) for pred in predictions
            ]

            # Basic metrics
            train_pred = np.polyval(coeffs, trend)
            metrics = {
                "mae": np.mean(np.abs(y - train_pred)),
                "rmse": np.sqrt(np.mean((y - train_pred) ** 2)),
            }

        return predictions.tolist(), confidence_intervals, metrics, None

    async def _seasonal_naive_model(
        self, df: pd.DataFrame, config: ForecastConfig
    ) -> Tuple[
        List[float], List[Tuple[float, float]], Dict[str, float], Optional[Dict[str, float]]
    ]:
        """Seasonal naive forecasting (repeat seasonal pattern)"""
        if len(df) < 14:  # Need at least 2 weeks of data
            raise ValueError("Insufficient data for seasonal naive model")

        df = df.sort_values("period_date").reset_index(drop=True)
        y = df["units_sold"].values

        # Determine seasonal period
        if config.seasonal_periods:
            season_length = config.seasonal_periods
        elif config.horizon == ForecastHorizon.DAILY:
            season_length = 7  # Weekly seasonality
        elif config.horizon == ForecastHorizon.WEEKLY:
            season_length = 4  # Monthly seasonality
        else:
            season_length = 12  # Annual seasonality for monthly data

        season_length = min(season_length, len(y) // 2)

        if season_length < 2:
            # Fall back to simple mean
            predictions = [np.mean(y[-7:])] * config.prediction_days
        else:
            # Use seasonal pattern with list comprehension
            seasonal_pattern = y[-season_length:]
            predictions = [seasonal_pattern[i % season_length] for i in range(config.prediction_days)]

        # Calculate confidence intervals based on historical variance
        recent_variance = np.var(y[-min(30, len(y)) :])
        std_error = np.sqrt(recent_variance)

        confidence_intervals = [
            (max(0, pred - 1.96 * std_error), pred + 1.96 * std_error) for pred in predictions
        ]

        # Model metrics (on recent data)
        if len(y) >= season_length * 2:
            test_y = y[-season_length:]
            test_pred = y[-season_length * 2 : -season_length]
            metrics = {
                "mae": np.mean(np.abs(test_y - test_pred)),
                "rmse": np.sqrt(np.mean((test_y - test_pred) ** 2)),
            }
        else:
            metrics = {"mae": 0, "rmse": 0}

        return predictions, confidence_intervals, metrics, None

    async def _random_forest_model(
        self, df: pd.DataFrame, config: ForecastConfig
    ) -> Tuple[
        List[float], List[Tuple[float, float]], Dict[str, float], Optional[Dict[str, float]]
    ]:
        """Random Forest forecasting model"""
        if not SKLEARN_AVAILABLE:
            raise ValueError("sklearn not available for Random Forest model")

        if len(df) < 20:
            raise ValueError("Insufficient data for Random Forest model")

        # Prepare features
        df = self._create_ml_features(df, config)
        feature_cols = [
            col for col in df.columns if col not in ["period_date", "units_sold", "entity_id"]
        ]

        if not feature_cols:
            raise ValueError("No features available for ML model")

        X = df[feature_cols].values
        y = df["units_sold"].values

        # Handle missing values
        X = np.nan_to_num(X, nan=0)

        # Split data for training and validation
        if len(df) > 50:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        else:
            X_train, X_test, y_train, y_test = X, X[-5:], y, y[-5:]

        # Configure model
        hyperparams = config.hyperparameters or {}
        model = RandomForestRegressor(
            n_estimators=hyperparams.get("n_estimators", 100),
            max_depth=hyperparams.get("max_depth", 10),
            min_samples_split=hyperparams.get("min_samples_split", 5),
            random_state=42,
        )

        # Train model
        model.fit(X_train, y_train)

        # Generate predictions
        last_features = X[-1:].copy()
        predictions = []

        for i in range(config.prediction_days):
            pred = model.predict(last_features)[0]
            predictions.append(max(0, pred))  # Ensure non-negative

            # Update features for next prediction (simplified)
            if len(feature_cols) > 0:
                # Update trend feature if it exists
                trend_idx = next((i for i, col in enumerate(feature_cols) if "trend" in col), None)
                if trend_idx is not None:
                    last_features[0, trend_idx] += 1

        # Calculate confidence intervals using prediction quantiles with list comprehensions
        
        # PERFORMANCE OPTIMIZATION: Use nested list comprehensions for tree predictions
        tree_predictions = [
            [max(0, tree.predict(X[-1:].reshape(1, -1))[0]) for tree in model.estimators_]
            for i in range(config.prediction_days)
        ]

        # PERFORMANCE OPTIMIZATION: Use list comprehension for confidence intervals
        alpha = 1 - config.confidence_level
        confidence_intervals = [
            (
                np.percentile(tree_preds, 100 * alpha / 2),
                np.percentile(tree_preds, 100 * (1 - alpha / 2))
            )
            for tree_preds in tree_predictions
        ]

        # Model metrics
        y_pred = model.predict(X_test)
        metrics = {
            "r2_score": r2_score(y_test, y_pred),
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
        }

        # Feature importance
        feature_importance = dict(zip(feature_cols, model.feature_importances_))

        return predictions, confidence_intervals, metrics, feature_importance

    async def _ensemble_model(
        self, df: pd.DataFrame, config: ForecastConfig
    ) -> Tuple[
        List[float], List[Tuple[float, float]], Dict[str, float], Optional[Dict[str, float]]
    ]:
        """Ensemble model combining multiple forecasting approaches"""
        models_to_ensemble = [ForecastModel.LINEAR_TREND, ForecastModel.SEASONAL_NAIVE]

        # Add ML models if available
        if SKLEARN_AVAILABLE and len(df) >= 20:
            models_to_ensemble.append(ForecastModel.RANDOM_FOREST)

        # Generate predictions from each model
        model_results = {}
        model_weights = {
            ForecastModel.LINEAR_TREND: 0.3,
            ForecastModel.SEASONAL_NAIVE: 0.4,
            ForecastModel.RANDOM_FOREST: 0.3,
        }

        for model_type in models_to_ensemble:
            try:
                temp_config = ForecastConfig(
                    model=model_type,
                    horizon=config.horizon,
                    level=config.level,
                    prediction_days=config.prediction_days,
                    confidence_level=config.confidence_level,
                )

                model_func = self._get_model_function(model_type)
                predictions, intervals, metrics, _ = await model_func(df, temp_config)

                model_results[model_type] = {
                    "predictions": predictions,
                    "intervals": intervals,
                    "weight": model_weights.get(model_type, 0.33),
                }
            except Exception as e:
                self.logger.warning(f"Ensemble model {model_type.value} failed: {str(e)}")
                continue

        if not model_results:
            raise ValueError("All ensemble models failed")

        # Combine predictions using weighted average
        ensemble_predictions = []
        ensemble_intervals = []
        total_weight = sum(result["weight"] for result in model_results.values())

        for i in range(config.prediction_days):
            weighted_pred = 0
            weighted_lower = 0
            weighted_upper = 0

            for model_type, result in model_results.items():
                weight = result["weight"] / total_weight
                weighted_pred += result["predictions"][i] * weight
                weighted_lower += result["intervals"][i][0] * weight
                weighted_upper += result["intervals"][i][1] * weight

            ensemble_predictions.append(weighted_pred)
            ensemble_intervals.append((weighted_lower, weighted_upper))

        # Combined metrics (simplified)
        metrics = {
            "ensemble_models": len(model_results),
            "model_weights": {m.value: r["weight"] for m, r in model_results.items()},
        }

        return ensemble_predictions, ensemble_intervals, metrics, None

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _get_model_function(self, model: ForecastModel):
        """Get the appropriate model function"""
        model_map = {
            ForecastModel.LINEAR_TREND: self._linear_trend_model,
            ForecastModel.SEASONAL_NAIVE: self._seasonal_naive_model,
            ForecastModel.RANDOM_FOREST: self._random_forest_model,
            ForecastModel.ENSEMBLE: self._ensemble_model,
        }

        if model not in model_map:
            raise ValueError(f"Model {model.value} not implemented")

        return model_map[model]

    def _prepare_training_data(
        self, historical_data: List[Dict[str, Any]], config: ForecastConfig
    ) -> pd.DataFrame:
        """Prepare historical data for model training"""
        df = pd.DataFrame(historical_data)

        if df.empty:
            return df

        # Ensure required columns
        required_cols = ["period_date", "units_sold"]
        for col in required_cols:
            if col not in df.columns:
                return pd.DataFrame()

        # Sort by date
        df["period_date"] = pd.to_datetime(df["period_date"])
        df = df.sort_values("period_date").reset_index(drop=True)

        # Fill missing values
        df["units_sold"] = df["units_sold"].fillna(0)
        df["total_revenue"] = df["total_revenue"].fillna(0)

        # Remove outliers (simple method)
        if len(df) > 10:
            q99 = df["units_sold"].quantile(0.99)
            df.loc[df["units_sold"] > q99, "units_sold"] = q99

        return df

    def _create_ml_features(self, df: pd.DataFrame, config: ForecastConfig) -> pd.DataFrame:
        """Create features for ML models"""
        df = df.copy()

        # Time-based features
        df["trend"] = range(len(df))
        df["month"] = df["period_date"].dt.month
        df["quarter"] = df["period_date"].dt.quarter
        df["day_of_year"] = df["period_date"].dt.dayofyear

        if config.horizon == ForecastHorizon.DAILY:
            df["day_of_week"] = df["period_date"].dt.dayofweek
            df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Lagged features
        for lag in [1, 2, 3, 7, 14]:
            if lag < len(df):
                df[f"units_sold_lag_{lag}"] = df["units_sold"].shift(lag)

        # Moving averages
        for window in [3, 7, 14]:
            if window < len(df):
                df[f"units_sold_ma_{window}"] = (
                    df["units_sold"].rolling(window, min_periods=1).mean()
                )

        # Seasonal features
        if config.horizon == ForecastHorizon.DAILY and len(df) >= 14:
            df["seasonal_7"] = df["units_sold"].shift(7)
        elif config.horizon == ForecastHorizon.WEEKLY and len(df) >= 8:
            df["seasonal_4"] = df["units_sold"].shift(4)

        # Price features if available
        if "avg_price" in df.columns:
            df["price_change"] = df["avg_price"].pct_change()
            df["price_ma_7"] = df["avg_price"].rolling(7, min_periods=1).mean()

        # Fill remaining NaN values
        df = df.fillna(method="bfill").fillna(0)

        return df

    def _format_predictions(
        self,
        predictions: List[float],
        confidence_intervals: List[Tuple[float, float]],
        config: ForecastConfig,
    ) -> List[Dict[str, Any]]:
        """Format predictions for storage"""
        prediction_list = []
        base_date = date.today()

        for i, (pred, (lower, upper)) in enumerate(zip(predictions, confidence_intervals)):
            # Calculate prediction date
            if config.horizon == ForecastHorizon.DAILY:
                pred_date = base_date + timedelta(days=i + 1)
            elif config.horizon == ForecastHorizon.WEEKLY:
                pred_date = base_date + timedelta(weeks=i + 1)
            else:  # Monthly
                # Approximate monthly increment
                pred_date = base_date + timedelta(days=(i + 1) * 30)

            prediction_list.append(
                {
                    "forecast_date": pred_date,
                    "forecasted_units": max(0, round(pred, 2)),
                    "forecasted_revenue": max(0, round(pred * 100, 2)),  # Placeholder calculation
                    "confidence_lower": max(0, round(lower, 2)),
                    "confidence_upper": round(upper, 2),
                }
            )

        return prediction_list

    async def _get_forecastable_entities(self, level: ForecastLevel) -> List[uuid.UUID]:
        """Get list of entities that can be forecasted"""
        # This would typically query for active products/brands/categories
        # with sufficient historical data
        return []  # Placeholder - would be implemented based on business logic

    async def _store_forecast_results(
        self, results: List[ForecastResult], run_id: uuid.UUID
    ) -> None:
        """Store forecast results in database"""
        all_forecasts = []

        for result in results:
            for pred in result.predictions:
                forecast_data = {
                    "forecast_run_id": run_id,
                    "forecast_level": result.entity_type,
                    "forecast_date": pred["forecast_date"],
                    "forecast_horizon": "daily",  # Would be derived from config
                    "forecasted_units": Decimal(str(pred["forecasted_units"])),
                    "forecasted_revenue": Decimal(str(pred["forecasted_revenue"])),
                    "confidence_lower": Decimal(str(pred["confidence_lower"])),
                    "confidence_upper": Decimal(str(pred["confidence_upper"])),
                    "model_name": result.model_name,
                    "model_version": result.model_version,
                    "feature_importance": result.feature_importance,
                }

                # Set appropriate entity ID field
                if result.entity_type == "product":
                    forecast_data["product_id"] = result.entity_id
                elif result.entity_type == "brand":
                    forecast_data["brand_id"] = result.entity_id
                elif result.entity_type == "category":
                    forecast_data["category_id"] = result.entity_id
                elif result.entity_type == "platform":
                    forecast_data["platform_id"] = result.entity_id

                all_forecasts.append(forecast_data)

        # Store in database
        await self.repository.create_forecast_batch(run_id, all_forecasts)

        self.logger.info(f"Stored {len(all_forecasts)} forecast records for run {run_id}")

    # =====================================================
    # PREDICTIVE INSIGHTS GENERATION
    # =====================================================

    async def generate_predictive_insights(
        self,
        transaction_count: int,
        revenue: float,
        avg_value: float,
        product_count: int,
        brand_count: int,
    ) -> Dict[str, Any]:
        """Generate predictive insights based on business metrics"""
        
        insights = []
        opportunities = []
        risk_factors = []
        
        # Analyze transaction trends
        if transaction_count > 1000:
            insights.append("High transaction volume indicates strong market presence")
        elif transaction_count < 100:
            risk_factors.append("Low transaction volume may impact revenue stability")
        
        # Revenue analysis
        if revenue > 100000:
            insights.append("Strong revenue performance demonstrates market demand")
            opportunities.append("Consider expanding into adjacent product categories")
        elif revenue < 10000:
            risk_factors.append("Revenue below market expectations")
            opportunities.append("Focus on high-margin premium products")
        
        # Average transaction value insights
        if avg_value > 100:
            insights.append("Premium pricing strategy showing effectiveness")
            opportunities.append("Target luxury segment expansion")
        elif avg_value < 30:
            opportunities.append("Opportunity to increase average order value through bundling")
        
        # Product diversity analysis
        if product_count > 500:
            insights.append("Diverse product portfolio reduces market risk")
        elif product_count < 50:
            opportunities.append("Expand product catalog to capture more market share")
        
        # Brand portfolio analysis
        if brand_count > 20:
            insights.append("Multi-brand strategy provides market resilience")
        elif brand_count < 5:
            opportunities.append("Partner with additional brands to diversify portfolio")
        
        # Calculate confidence score based on data quality
        confidence_score = min(0.95, max(0.1, (
            min(transaction_count / 1000, 1.0) * 0.3 +
            min(revenue / 50000, 1.0) * 0.3 +
            min(product_count / 200, 1.0) * 0.2 +
            min(brand_count / 10, 1.0) * 0.2
        )))
        
        return {
            "predictive_insights": insights,
            "growth_opportunities": opportunities,
            "risk_factors": risk_factors,
            "confidence_score": round(confidence_score, 2),
            "recommendations": [
                "Monitor market trends for emerging opportunities",
                "Focus on high-performing product categories",
                "Optimize pricing strategies based on demand patterns"
            ]
        }
