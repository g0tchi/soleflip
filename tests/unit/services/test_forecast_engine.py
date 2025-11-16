"""
Unit tests for ForecastEngine

Tests comprehensive forecasting functionality including:
- Multiple forecasting models (Linear, Seasonal, Random Forest, Ensemble)
- Data preparation and feature engineering
- Predictive insights generation
- Model selection and configuration
- Error handling and edge cases
"""

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domains.analytics.services.forecast_engine import (
    ForecastConfig,
    ForecastEngine,
    ForecastHorizon,
    ForecastLevel,
    ForecastModel,
    ForecastResult,
)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_repository():
    """Mock forecast repository"""
    repository = AsyncMock()
    repository.get_historical_sales_data = AsyncMock()
    repository.create_forecast_batch = AsyncMock()
    return repository


@pytest.fixture
def forecast_engine(mock_db_session, mock_repository):
    """ForecastEngine instance with mocked dependencies"""
    engine = ForecastEngine(mock_db_session)
    engine.repository = mock_repository
    return engine


@pytest.fixture
def sample_historical_data():
    """Sample historical sales data for testing"""
    base_date = date.today() - timedelta(days=100)
    data = []
    for i in range(100):
        data.append(
            {
                "period_date": base_date + timedelta(days=i),
                "units_sold": 10 + i * 0.5 + np.random.normal(0, 2),  # Linear trend with noise
                "total_revenue": (10 + i * 0.5) * 50,
                "avg_price": 50.0,
            }
        )
    return data


@pytest.fixture
def sample_config():
    """Sample forecast configuration"""
    return ForecastConfig(
        model=ForecastModel.LINEAR_TREND,
        horizon=ForecastHorizon.DAILY,
        level=ForecastLevel.PRODUCT,
        prediction_days=30,
        confidence_level=0.95,
        min_history_days=90,
    )


# =====================================================
# MAIN FORECASTING FLOW TESTS
# =====================================================


@pytest.mark.asyncio
async def test_generate_forecasts_with_entity_ids(
    forecast_engine, sample_config, sample_historical_data, mock_repository
):
    """Test forecast generation with specific entity IDs"""
    entity_ids = [uuid.uuid4(), uuid.uuid4()]
    mock_repository.get_historical_sales_data = AsyncMock(return_value=sample_historical_data)

    results = await forecast_engine.generate_forecasts(config=sample_config, entity_ids=entity_ids)

    assert len(results) == 2
    assert all(isinstance(r, ForecastResult) for r in results)
    assert mock_repository.create_forecast_batch.called


@pytest.mark.asyncio
async def test_generate_forecasts_without_entity_ids(
    forecast_engine, sample_config, mock_repository
):
    """Test forecast generation when no entities provided"""
    # Mock _get_forecastable_entities to return empty list
    forecast_engine._get_forecastable_entities = AsyncMock(return_value=[])

    results = await forecast_engine.generate_forecasts(config=sample_config)

    assert results == []
    # Store is still called with empty list, which is fine
    mock_repository.create_forecast_batch.assert_called_once()


@pytest.mark.asyncio
async def test_generate_forecasts_handles_failures(
    forecast_engine, sample_config, sample_historical_data, mock_repository
):
    """Test forecast generation handles entity failures gracefully"""
    entity_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

    # First entity succeeds, second fails, third succeeds
    call_count = [0]

    async def mock_get_historical(entity_type, entity_id, days_back, aggregation):
        call_count[0] += 1
        if call_count[0] == 2:
            # Second call raises exception
            raise Exception("Database error")
        return sample_historical_data

    mock_repository.get_historical_sales_data = mock_get_historical

    results = await forecast_engine.generate_forecasts(config=sample_config, entity_ids=entity_ids)

    # Should have 2 successful forecasts (1st and 3rd)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_forecast_single_entity_insufficient_data(
    forecast_engine, sample_config, mock_repository
):
    """Test forecast single entity with insufficient historical data"""
    entity_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # Return very little data
    mock_repository.get_historical_sales_data = AsyncMock(return_value=[{"units_sold": 10}])

    result = await forecast_engine._forecast_single_entity(sample_config, entity_id, run_id)

    assert result is None


# =====================================================
# LINEAR TREND MODEL TESTS
# =====================================================


@pytest.mark.asyncio
async def test_linear_trend_model_success(forecast_engine, sample_config):
    """Test linear trend model with sufficient data"""
    # Create simple linear data
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),  # Perfect linear trend
            "total_revenue": [x * 100 for x in range(50)],
        }
    )

    predictions, intervals, metrics, importance = await forecast_engine._linear_trend_model(
        df, sample_config
    )

    assert len(predictions) == sample_config.prediction_days
    assert len(intervals) == sample_config.prediction_days
    assert "mae" in metrics or "r2_score" in metrics
    assert all(pred >= 0 for pred in predictions)  # Non-negative predictions


@pytest.mark.asyncio
async def test_linear_trend_model_insufficient_data(forecast_engine, sample_config):
    """Test linear trend model with too little data"""
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=5, freq="D"),
            "units_sold": [1, 2, 3, 4, 5],
        }
    )

    with pytest.raises(ValueError, match="Insufficient data"):
        await forecast_engine._linear_trend_model(df, sample_config)


@pytest.mark.asyncio
async def test_linear_trend_model_confidence_intervals(forecast_engine, sample_config):
    """Test that linear trend model produces valid confidence intervals"""
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),
            "total_revenue": [x * 100 for x in range(50)],
        }
    )

    predictions, intervals, _, _ = await forecast_engine._linear_trend_model(df, sample_config)

    # Check confidence intervals are valid
    for pred, (lower, upper) in zip(predictions, intervals):
        assert lower <= pred <= upper or lower <= upper  # Intervals should be ordered
        assert lower >= 0  # Non-negative lower bound


# =====================================================
# SEASONAL NAIVE MODEL TESTS
# =====================================================


@pytest.mark.asyncio
async def test_seasonal_naive_model_success(forecast_engine, sample_config):
    """Test seasonal naive model with sufficient data"""
    # Create data with weekly pattern
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=30, freq="D"),
            "units_sold": [10, 12, 15, 18, 20, 15, 8] * 4 + [10, 12],  # Weekly pattern
            "total_revenue": [x * 100 for x in [10, 12, 15, 18, 20, 15, 8] * 4 + [10, 12]],
        }
    )

    predictions, intervals, metrics, _ = await forecast_engine._seasonal_naive_model(
        df, sample_config
    )

    assert len(predictions) == sample_config.prediction_days
    assert len(intervals) == sample_config.prediction_days
    assert "mae" in metrics


@pytest.mark.asyncio
async def test_seasonal_naive_model_insufficient_data(forecast_engine, sample_config):
    """Test seasonal naive model with too little data"""
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=10, freq="D"),
            "units_sold": list(range(10)),
        }
    )

    with pytest.raises(ValueError, match="Insufficient data"):
        await forecast_engine._seasonal_naive_model(df, sample_config)


@pytest.mark.asyncio
async def test_seasonal_naive_model_with_custom_periods(forecast_engine):
    """Test seasonal naive model with custom seasonal periods"""
    config = ForecastConfig(
        model=ForecastModel.SEASONAL_NAIVE,
        horizon=ForecastHorizon.DAILY,
        level=ForecastLevel.PRODUCT,
        prediction_days=14,
        seasonal_periods=7,  # Weekly pattern
    )

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=30, freq="D"),
            "units_sold": list(range(30)),
            "total_revenue": [x * 100 for x in range(30)],
        }
    )

    predictions, _, _, _ = await forecast_engine._seasonal_naive_model(df, config)

    assert len(predictions) == 14


# =====================================================
# RANDOM FOREST MODEL TESTS
# =====================================================


@pytest.mark.asyncio
async def test_random_forest_model_success(forecast_engine, sample_config):
    """Test random forest model with sufficient data"""
    # Skip if sklearn not available
    try:
        from sklearn.ensemble import RandomForestRegressor  # noqa: F401
    except ImportError:
        pytest.skip("sklearn not available")

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),
            "total_revenue": [x * 100 for x in range(50)],
        }
    )

    predictions, intervals, metrics, importance = await forecast_engine._random_forest_model(
        df, sample_config
    )

    assert len(predictions) == sample_config.prediction_days
    assert len(intervals) == sample_config.prediction_days
    assert "r2_score" in metrics
    assert importance is not None
    assert all(pred >= 0 for pred in predictions)


@pytest.mark.asyncio
async def test_random_forest_model_insufficient_data(forecast_engine, sample_config):
    """Test random forest model with too little data"""
    # Skip if sklearn not available
    try:
        from sklearn.ensemble import RandomForestRegressor  # noqa: F401
    except ImportError:
        pytest.skip("sklearn not available")

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=15, freq="D"),
            "units_sold": list(range(15)),
        }
    )

    with pytest.raises(ValueError, match="Insufficient data"):
        await forecast_engine._random_forest_model(df, sample_config)


@pytest.mark.asyncio
async def test_random_forest_model_with_hyperparameters(forecast_engine):
    """Test random forest model with custom hyperparameters"""
    # Skip if sklearn not available
    try:
        from sklearn.ensemble import RandomForestRegressor  # noqa: F401
    except ImportError:
        pytest.skip("sklearn not available")

    config = ForecastConfig(
        model=ForecastModel.RANDOM_FOREST,
        horizon=ForecastHorizon.DAILY,
        level=ForecastLevel.PRODUCT,
        prediction_days=15,
        hyperparameters={"n_estimators": 50, "max_depth": 5},
    )

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),
            "total_revenue": [x * 100 for x in range(50)],
        }
    )

    predictions, _, _, _ = await forecast_engine._random_forest_model(df, config)

    assert len(predictions) == 15


# =====================================================
# ENSEMBLE MODEL TESTS
# =====================================================


@pytest.mark.asyncio
async def test_ensemble_model_success(forecast_engine, sample_config):
    """Test ensemble model combining multiple approaches"""
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),
            "total_revenue": [x * 100 for x in range(50)],
        }
    )

    predictions, intervals, metrics, _ = await forecast_engine._ensemble_model(df, sample_config)

    assert len(predictions) == sample_config.prediction_days
    assert len(intervals) == sample_config.prediction_days
    assert "ensemble_models" in metrics
    assert metrics["ensemble_models"] >= 2  # At least linear and seasonal


@pytest.mark.asyncio
async def test_ensemble_model_all_models_fail(forecast_engine, sample_config):
    """Test ensemble model when all sub-models fail"""
    # Very small dataset that will fail all models
    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=5, freq="D"),
            "units_sold": [1, 2, 3, 4, 5],
        }
    )

    with pytest.raises(ValueError, match="All ensemble models failed"):
        await forecast_engine._ensemble_model(df, sample_config)


# =====================================================
# MODEL SELECTION TESTS
# =====================================================


def test_get_model_function_linear_trend(forecast_engine):
    """Test model function selection for linear trend"""
    func = forecast_engine._get_model_function(ForecastModel.LINEAR_TREND)
    assert func == forecast_engine._linear_trend_model


def test_get_model_function_seasonal_naive(forecast_engine):
    """Test model function selection for seasonal naive"""
    func = forecast_engine._get_model_function(ForecastModel.SEASONAL_NAIVE)
    assert func == forecast_engine._seasonal_naive_model


def test_get_model_function_random_forest(forecast_engine):
    """Test model function selection for random forest"""
    func = forecast_engine._get_model_function(ForecastModel.RANDOM_FOREST)
    assert func == forecast_engine._random_forest_model


def test_get_model_function_ensemble(forecast_engine):
    """Test model function selection for ensemble"""
    func = forecast_engine._get_model_function(ForecastModel.ENSEMBLE)
    assert func == forecast_engine._ensemble_model


def test_get_model_function_not_implemented(forecast_engine):
    """Test model function selection for unimplemented model"""
    # ARIMA is in enum but not implemented
    with pytest.raises(ValueError, match="not implemented"):
        forecast_engine._get_model_function(ForecastModel.ARIMA)


# =====================================================
# DATA PREPARATION TESTS
# =====================================================


def test_prepare_training_data_success(forecast_engine, sample_config):
    """Test successful data preparation"""
    historical_data = [
        {
            "period_date": date.today() - timedelta(days=i),
            "units_sold": 10 + i,
            "total_revenue": (10 + i) * 50,
        }
        for i in range(50)
    ]

    df = forecast_engine._prepare_training_data(historical_data, sample_config)

    assert not df.empty
    assert "period_date" in df.columns
    assert "units_sold" in df.columns
    assert df["units_sold"].notna().all()  # No NaN values


def test_prepare_training_data_empty_input(forecast_engine, sample_config):
    """Test data preparation with empty input"""
    df = forecast_engine._prepare_training_data([], sample_config)
    assert df.empty


def test_prepare_training_data_missing_columns(forecast_engine, sample_config):
    """Test data preparation with missing required columns"""
    historical_data = [{"some_field": 123}]

    df = forecast_engine._prepare_training_data(historical_data, sample_config)
    assert df.empty  # Should return empty DataFrame


def test_prepare_training_data_outlier_removal(forecast_engine, sample_config):
    """Test that outliers are handled"""
    historical_data = [
        {"period_date": date.today() - timedelta(days=i), "units_sold": 10, "total_revenue": 500}
        for i in range(20)
    ]
    # Add outlier
    historical_data.append(
        {
            "period_date": date.today() - timedelta(days=21),
            "units_sold": 10000,
            "total_revenue": 500,
        }
    )

    df = forecast_engine._prepare_training_data(historical_data, sample_config)

    # Check that outlier was capped
    assert df["units_sold"].max() < 10000


# =====================================================
# FEATURE ENGINEERING TESTS
# =====================================================


def test_create_ml_features_daily_horizon(forecast_engine):
    """Test ML feature creation for daily horizon"""
    config = ForecastConfig(
        model=ForecastModel.RANDOM_FOREST,
        horizon=ForecastHorizon.DAILY,
        level=ForecastLevel.PRODUCT,
        prediction_days=30,
    )

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),
        }
    )

    df_features = forecast_engine._create_ml_features(df, config)

    # Check time features
    assert "trend" in df_features.columns
    assert "month" in df_features.columns
    assert "day_of_week" in df_features.columns
    assert "is_weekend" in df_features.columns

    # Check lag features
    assert "units_sold_lag_1" in df_features.columns
    assert "units_sold_lag_7" in df_features.columns

    # Check moving averages
    assert "units_sold_ma_7" in df_features.columns


def test_create_ml_features_weekly_horizon(forecast_engine):
    """Test ML feature creation for weekly horizon"""
    config = ForecastConfig(
        model=ForecastModel.RANDOM_FOREST,
        horizon=ForecastHorizon.WEEKLY,
        level=ForecastLevel.PRODUCT,
        prediction_days=12,
    )

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=20, freq="W"),
            "units_sold": list(range(20)),
        }
    )

    df_features = forecast_engine._create_ml_features(df, config)

    assert "trend" in df_features.columns
    assert "month" in df_features.columns
    assert "day_of_week" not in df_features.columns  # Not for weekly


def test_create_ml_features_with_price_data(forecast_engine):
    """Test ML feature creation with price data"""
    config = ForecastConfig(
        model=ForecastModel.RANDOM_FOREST,
        horizon=ForecastHorizon.DAILY,
        level=ForecastLevel.PRODUCT,
        prediction_days=30,
    )

    df = pd.DataFrame(
        {
            "period_date": pd.date_range(start="2024-01-01", periods=50, freq="D"),
            "units_sold": list(range(50)),
            "avg_price": [100.0 + i * 0.5 for i in range(50)],
        }
    )

    df_features = forecast_engine._create_ml_features(df, config)

    # Check price features
    assert "price_change" in df_features.columns
    assert "price_ma_7" in df_features.columns


# =====================================================
# PREDICTION FORMATTING TESTS
# =====================================================


def test_format_predictions_daily(forecast_engine):
    """Test prediction formatting for daily horizon"""
    config = ForecastConfig(
        model=ForecastModel.LINEAR_TREND,
        horizon=ForecastHorizon.DAILY,
        level=ForecastLevel.PRODUCT,
        prediction_days=7,
    )

    predictions = [10.5, 11.2, 12.0, 13.5, 14.0, 15.2, 16.0]
    intervals = [
        (9.0, 12.0),
        (10.0, 13.0),
        (11.0, 14.0),
        (12.0, 15.0),
        (13.0, 16.0),
        (14.0, 17.0),
        (15.0, 18.0),
    ]

    result = forecast_engine._format_predictions(predictions, intervals, config)

    assert len(result) == 7
    assert all("forecast_date" in pred for pred in result)
    assert all("forecasted_units" in pred for pred in result)
    assert all("confidence_lower" in pred for pred in result)
    assert all("confidence_upper" in pred for pred in result)

    # Check dates are sequential
    for i in range(len(result) - 1):
        assert result[i + 1]["forecast_date"] > result[i]["forecast_date"]


def test_format_predictions_weekly(forecast_engine):
    """Test prediction formatting for weekly horizon"""
    config = ForecastConfig(
        model=ForecastModel.LINEAR_TREND,
        horizon=ForecastHorizon.WEEKLY,
        level=ForecastLevel.PRODUCT,
        prediction_days=4,
    )

    predictions = [100.0, 110.0, 120.0, 130.0]
    intervals = [(90.0, 110.0), (100.0, 120.0), (110.0, 130.0), (120.0, 140.0)]

    result = forecast_engine._format_predictions(predictions, intervals, config)

    assert len(result) == 4
    # Weekly predictions should be ~7 days apart
    date_diff = (result[1]["forecast_date"] - result[0]["forecast_date"]).days
    assert 6 <= date_diff <= 8  # Approximately 7 days


def test_format_predictions_non_negative(forecast_engine, sample_config):
    """Test that negative predictions are clamped to zero"""
    predictions = [10.0, -5.0, 3.0, -2.0]  # Some negative values
    intervals = [(-1.0, 11.0), (-10.0, 0.0), (0.0, 6.0), (-5.0, 1.0)]

    result = forecast_engine._format_predictions(predictions, intervals, sample_config)

    # All forecasted values should be non-negative
    assert all(pred["forecasted_units"] >= 0 for pred in result)
    assert all(pred["confidence_lower"] >= 0 for pred in result)


# =====================================================
# PREDICTIVE INSIGHTS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_generate_predictive_insights_high_performance(forecast_engine):
    """Test predictive insights for high-performing business"""
    insights = await forecast_engine.generate_predictive_insights(
        transaction_count=1500,
        revenue=150000.0,
        avg_value=120.0,
        product_count=600,
        brand_count=25,
    )

    assert "predictive_insights" in insights
    assert "growth_opportunities" in insights
    assert "risk_factors" in insights
    assert "confidence_score" in insights

    # High performance should have positive insights
    assert len(insights["predictive_insights"]) > 0
    assert insights["confidence_score"] > 0.7


@pytest.mark.asyncio
async def test_generate_predictive_insights_low_performance(forecast_engine):
    """Test predictive insights for low-performing business"""
    insights = await forecast_engine.generate_predictive_insights(
        transaction_count=50,
        revenue=5000.0,
        avg_value=25.0,
        product_count=20,
        brand_count=3,
    )

    # Low performance should have risk factors
    assert len(insights["risk_factors"]) > 0
    assert len(insights["growth_opportunities"]) > 0


@pytest.mark.asyncio
async def test_generate_predictive_insights_confidence_score(forecast_engine):
    """Test that confidence score is calculated correctly"""
    # Very low metrics
    insights_low = await forecast_engine.generate_predictive_insights(
        transaction_count=10,
        revenue=1000.0,
        avg_value=10.0,
        product_count=5,
        brand_count=1,
    )

    # High metrics
    insights_high = await forecast_engine.generate_predictive_insights(
        transaction_count=5000,
        revenue=500000.0,
        avg_value=200.0,
        product_count=1000,
        brand_count=50,
    )

    assert insights_low["confidence_score"] < insights_high["confidence_score"]
    assert 0.0 <= insights_low["confidence_score"] <= 1.0
    assert 0.0 <= insights_high["confidence_score"] <= 1.0


# =====================================================
# STORAGE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_store_forecast_results(forecast_engine, mock_repository):
    """Test forecast results storage"""
    run_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    results = [
        ForecastResult(
            entity_id=entity_id,
            entity_type="product",
            predictions=[
                {
                    "forecast_date": date.today() + timedelta(days=1),
                    "forecasted_units": 10.5,
                    "forecasted_revenue": 525.0,
                    "confidence_lower": 8.0,
                    "confidence_upper": 13.0,
                }
            ],
            model_name="linear_trend",
            model_version="1.0.0",
            confidence_intervals=[(8.0, 13.0)],
            feature_importance=None,
            model_metrics={"mae": 1.5},
        )
    ]

    await forecast_engine._store_forecast_results(results, run_id)

    # Verify repository was called
    mock_repository.create_forecast_batch.assert_called_once()
    call_args = mock_repository.create_forecast_batch.call_args
    assert call_args[0][0] == run_id
    assert len(call_args[0][1]) == 1


@pytest.mark.asyncio
async def test_store_forecast_results_multiple_predictions(forecast_engine, mock_repository):
    """Test storage of multiple predictions"""
    run_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    results = [
        ForecastResult(
            entity_id=entity_id,
            entity_type="brand",
            predictions=[
                {
                    "forecast_date": date.today() + timedelta(days=i),
                    "forecasted_units": 10.0 + i,
                    "forecasted_revenue": (10.0 + i) * 50,
                    "confidence_lower": 8.0 + i,
                    "confidence_upper": 12.0 + i,
                }
                for i in range(1, 6)
            ],
            model_name="ensemble",
            model_version="1.0.0",
            confidence_intervals=[(8.0 + i, 12.0 + i) for i in range(5)],
            feature_importance={"trend": 0.5, "seasonality": 0.3},
            model_metrics={"r2_score": 0.85},
        )
    ]

    await forecast_engine._store_forecast_results(results, run_id)

    # Should create 5 forecast records (one per prediction)
    call_args = mock_repository.create_forecast_batch.call_args
    assert len(call_args[0][1]) == 5


# =====================================================
# EDGE CASES AND ERROR HANDLING
# =====================================================


@pytest.mark.asyncio
async def test_forecast_single_entity_model_failure(
    forecast_engine, sample_config, sample_historical_data, mock_repository
):
    """Test handling of model failures"""
    entity_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mock_repository.get_historical_sales_data = AsyncMock(return_value=sample_historical_data)

    # Mock model to raise exception
    with patch.object(forecast_engine, "_linear_trend_model", side_effect=Exception("Model error")):
        result = await forecast_engine._forecast_single_entity(sample_config, entity_id, run_id)

    assert result is None


def test_prepare_training_data_handles_nan(forecast_engine, sample_config):
    """Test data preparation handles NaN values"""
    historical_data = [
        {"period_date": date.today() - timedelta(days=i), "units_sold": None, "total_revenue": 100}
        for i in range(20)
    ]

    df = forecast_engine._prepare_training_data(historical_data, sample_config)

    # NaN values should be filled with 0
    assert df["units_sold"].notna().all()
    assert (df["units_sold"] == 0).all()
