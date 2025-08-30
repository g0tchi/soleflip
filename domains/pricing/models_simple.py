"""
Simplified Pricing Models - Working version without complex Foreign Keys
"""

from sqlalchemy import Column, String, Integer, Numeric, Boolean, Date, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from shared.database.utils import IS_POSTGRES
from shared.database.models import Base, TimestampMixin


# Simplified models without complex relationships
class SalesForecast(Base, TimestampMixin):
    """Sales Forecasting Results"""

    __tablename__ = "sales_forecasts"
    __table_args__ = {"schema": "pricing"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    target_type = Column(String(50), nullable=False)  # 'product', 'brand', 'category'

    # Forecast parameters
    forecast_date = Column(Date, nullable=False)
    horizon_days = Column(Integer, nullable=False)
    model_used = Column(String(50), nullable=False)
    confidence_level = Column(Numeric(3, 2), nullable=False, default=0.95)

    # Forecast results
    predicted_quantity = Column(Numeric(10, 2), nullable=False)
    predicted_revenue = Column(Numeric(12, 2), nullable=False)
    confidence_interval_lower = Column(Numeric(12, 2), nullable=False)
    confidence_interval_upper = Column(Numeric(12, 2), nullable=False)

    # Additional metrics
    trend_direction = Column(String(20), nullable=True)
    seasonality_factor = Column(Numeric(5, 4), nullable=True)
    accuracy_score = Column(Numeric(5, 4), nullable=True)

    # Model metadata
    model_parameters = Column(JSON, nullable=True)
    feature_importance = Column(JSON, nullable=True)


class ForecastAccuracy(Base, TimestampMixin):
    """Model Performance Tracking"""

    __tablename__ = "forecast_accuracy"
    __table_args__ = {"schema": "pricing"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(50), nullable=False)

    # Accuracy metrics
    accuracy_score = Column(Numeric(5, 4), nullable=False)
    mae = Column(Numeric(10, 4), nullable=False)  # Mean Absolute Error
    rmse = Column(Numeric(10, 4), nullable=False)  # Root Mean Square Error
    mape = Column(Numeric(5, 4), nullable=False)  # Mean Absolute Percentage Error

    # Validation metadata
    validation_period_start = Column(Date, nullable=False)
    validation_period_end = Column(Date, nullable=False)
    predictions_count = Column(Integer, nullable=False)
    model_version = Column(String(20), nullable=True)


class MarketPrice(Base, TimestampMixin):
    """Market Price Tracking"""

    __tablename__ = "market_prices"
    __table_args__ = {"schema": "pricing"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    platform_name = Column(String(50), nullable=False)

    # Price data
    current_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    condition = Column(String(20), nullable=False, default="new")
    size_variant = Column(String(20), nullable=True)

    # Market metrics
    highest_bid = Column(Numeric(10, 2), nullable=True)
    lowest_ask = Column(Numeric(10, 2), nullable=True)
    last_sale_price = Column(Numeric(10, 2), nullable=True)

    # Source metadata
    data_source = Column(String(50), nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=False)


class PriceHistory(Base, TimestampMixin):
    """Price Change History"""

    __tablename__ = "price_history"
    __table_args__ = {"schema": "pricing"} if IS_POSTGRES else None

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), nullable=False)

    # Price information
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    pricing_strategy = Column(String(50), nullable=True)

    # Context
    reason = Column(String(200), nullable=True)
    automated = Column(Boolean, nullable=False, default=True)
    confidence_score = Column(Numeric(3, 2), nullable=True)
