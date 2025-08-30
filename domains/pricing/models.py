"""
Pricing Domain SQLAlchemy Models
Advanced pricing and forecasting data models
"""
from sqlalchemy import Column, String, Integer, Numeric, Boolean, ForeignKey, Date, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from shared.database.utils import get_schema_ref, IS_POSTGRES
from shared.database.models import Base, TimestampMixin

# =====================================================
# PRICING SCHEMA MODELS
# =====================================================

class PriceRule(Base, TimestampMixin):
    """Price Rules - Configurable pricing logic and strategies"""
    __tablename__ = "price_rules"
    __table_args__ = {'schema': 'pricing'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)  # 'cost_plus', 'market_based', 'competitive'
    priority = Column(Integer, nullable=False, default=100)
    active = Column(Boolean, nullable=False, default=True)
    
    # Scope filters
    brand_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")), nullable=True)
    platform_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("platforms.id", "core")), nullable=True)
    
    # Pricing parameters
    base_markup_percent = Column(Numeric(5, 2), nullable=True)
    minimum_margin_percent = Column(Numeric(5, 2), nullable=True)
    maximum_discount_percent = Column(Numeric(5, 2), nullable=True)
    condition_multipliers = Column(JSON, nullable=True)
    seasonal_adjustments = Column(JSON, nullable=True)
    
    # Validity period
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    brand = relationship("Brand", back_populates="price_rules")
    category = relationship("Category", back_populates="price_rules")
    platform = relationship("Platform", back_populates="price_rules")
    
    def is_active(self, check_date: datetime = None) -> bool:
        """Check if rule is active at given date"""
        if not self.active:
            return False
        
        if check_date is None:
            check_date = datetime.now()
            
        if self.effective_from > check_date:
            return False
            
        if self.effective_until and self.effective_until < check_date:
            return False
            
        return True
    
    def get_condition_multiplier(self, condition: str) -> Decimal:
        """Get multiplier for specific condition"""
        if not self.condition_multipliers:
            return Decimal('1.0')
        
        return Decimal(str(self.condition_multipliers.get(condition, 1.0)))
    
    def get_seasonal_adjustment(self, month: int) -> Decimal:
        """Get seasonal adjustment for specific month"""
        if not self.seasonal_adjustments:
            return Decimal('1.0')
        
        return Decimal(str(self.seasonal_adjustments.get(str(month), 1.0)))

class BrandMultiplier(Base, TimestampMixin):
    """Brand-specific pricing multipliers and adjustments"""
    __tablename__ = "brand_multipliers"
    __table_args__ = {'schema': 'pricing'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=False)
    multiplier_type = Column(String(50), nullable=False)  # 'premium', 'discount', 'seasonal'
    multiplier_value = Column(Numeric(4, 3), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date, nullable=True)
    
    # Relationships
    brand = relationship("Brand", back_populates="brand_multipliers")
    
    def is_effective(self, check_date: date = None) -> bool:
        """Check if multiplier is effective at given date"""
        if not self.active:
            return False
            
        if check_date is None:
            check_date = date.today()
            
        if self.effective_from > check_date:
            return False
            
        if self.effective_until and self.effective_until < check_date:
            return False
            
        return True

class PriceHistory(Base):
    """Historical price tracking for products and inventory items"""
    __tablename__ = "price_history"
    __table_args__ = {'schema': 'pricing'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=False)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("inventory_items.id", "inventory")), nullable=True)
    platform_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("platforms.id", "core")), nullable=True)
    
    price_date = Column(Date, nullable=False)
    price_type = Column(String(30), nullable=False)  # 'listing', 'sale', 'market', 'competitor'
    price_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='EUR')
    source = Column(String(50), nullable=False)  # 'internal', 'stockx', 'goat', 'manual'
    confidence_score = Column(Numeric(3, 2), nullable=True)
    additional_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="price_history")
    inventory_item = relationship("InventoryItem", back_populates="price_history")
    platform = relationship("Platform", back_populates="price_history")

class MarketPrice(Base):
    """External market price data from various platforms"""
    __tablename__ = "market_prices"
    __table_args__ = {'schema': 'pricing'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=False)
    platform_name = Column(String(50), nullable=False)
    size_value = Column(String(20), nullable=True)
    condition = Column(String(20), nullable=False)
    price_date = Column(Date, nullable=False)
    
    # Market metrics
    lowest_ask = Column(Numeric(10, 2), nullable=True)
    highest_bid = Column(Numeric(10, 2), nullable=True)
    last_sale = Column(Numeric(10, 2), nullable=True)
    average_price = Column(Numeric(10, 2), nullable=True)
    sales_volume = Column(Integer, nullable=True)
    premium_percentage = Column(Numeric(5, 2), nullable=True)
    data_quality_score = Column(Numeric(3, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="market_prices")
    
    def get_market_price(self, price_type: str = 'last_sale') -> Optional[Decimal]:
        """Get specific market price type"""
        price_map = {
            'last_sale': self.last_sale,
            'lowest_ask': self.lowest_ask,
            'highest_bid': self.highest_bid,
            'average': self.average_price
        }
        return price_map.get(price_type)

# =====================================================
# ANALYTICS SCHEMA MODELS
# =====================================================

class SalesForecast(Base):
    """Sales forecast predictions at various levels and horizons"""
    __tablename__ = "sales_forecasts"
    __table_args__ = {'schema': 'analytics'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_run_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Forecast dimensions
    product_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")), nullable=True)
    platform_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("platforms.id", "core")), nullable=True)
    
    forecast_level = Column(String(20), nullable=False)  # 'product', 'brand', 'category', 'platform'
    forecast_date = Column(Date, nullable=False)
    forecast_horizon = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    
    # Forecast values
    forecasted_units = Column(Numeric(10, 2), nullable=False)
    forecasted_revenue = Column(Numeric(12, 2), nullable=False)
    confidence_lower = Column(Numeric(10, 2), nullable=True)
    confidence_upper = Column(Numeric(10, 2), nullable=True)
    
    # Model metadata
    model_name = Column(String(50), nullable=False)
    model_version = Column(String(20), nullable=False)
    feature_importance = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="sales_forecasts")
    brand = relationship("Brand", back_populates="sales_forecasts")
    category = relationship("Category", back_populates="sales_forecasts")
    platform = relationship("Platform", back_populates="sales_forecasts")
    
    @property
    def confidence_interval(self) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """Get confidence interval as tuple"""
        return (self.confidence_lower, self.confidence_upper)
    
    def accuracy_score(self, actual_value: Decimal) -> Dict[str, float]:
        """Calculate accuracy metrics against actual value"""
        if not actual_value:
            return {}
        
        forecast_value = self.forecasted_units
        abs_error = abs(forecast_value - actual_value)
        percentage_error = (abs_error / actual_value) * 100 if actual_value != 0 else 0
        
        return {
            'absolute_error': float(abs_error),
            'percentage_error': float(percentage_error),
            'forecast_value': float(forecast_value),
            'actual_value': float(actual_value)
        }

class ForecastAccuracy(Base):
    """Forecast accuracy tracking and model performance metrics"""
    __tablename__ = "forecast_accuracy"
    __table_args__ = {'schema': 'analytics'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_run_id = Column(UUID(as_uuid=True), nullable=False)
    model_name = Column(String(50), nullable=False)
    forecast_level = Column(String(20), nullable=False)
    forecast_horizon = Column(String(20), nullable=False)
    accuracy_date = Column(Date, nullable=False)
    
    # Accuracy metrics
    mape_score = Column(Numeric(5, 2), nullable=True)  # Mean Absolute Percentage Error
    rmse_score = Column(Numeric(10, 2), nullable=True)  # Root Mean Square Error
    mae_score = Column(Numeric(10, 2), nullable=True)   # Mean Absolute Error
    r2_score = Column(Numeric(5, 4), nullable=True)    # R-squared
    bias_score = Column(Numeric(8, 2), nullable=True)
    
    records_evaluated = Column(Integer, nullable=False)
    evaluation_period_days = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def get_accuracy_summary(self) -> Dict[str, Any]:
        """Get comprehensive accuracy summary"""
        return {
            'model': self.model_name,
            'level': self.forecast_level,
            'horizon': self.forecast_horizon,
            'mape': float(self.mape_score) if self.mape_score else None,
            'rmse': float(self.rmse_score) if self.rmse_score else None,
            'r2': float(self.r2_score) if self.r2_score else None,
            'records': self.records_evaluated,
            'period_days': self.evaluation_period_days
        }

class DemandPattern(Base):
    """Historical demand analysis and pattern recognition"""
    __tablename__ = "demand_patterns"
    __table_args__ = {'schema': 'analytics'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")), nullable=True)
    
    analysis_level = Column(String(20), nullable=False)
    pattern_date = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'seasonal'
    
    # Pattern metrics
    demand_score = Column(Numeric(8, 4), nullable=False)
    velocity_rank = Column(Integer, nullable=True)
    seasonality_factor = Column(Numeric(4, 3), nullable=True)
    trend_direction = Column(String(20), nullable=True)  # 'increasing', 'decreasing', 'stable'
    volatility_score = Column(Numeric(5, 4), nullable=True)
    pattern_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="demand_patterns")
    brand = relationship("Brand", back_populates="demand_patterns")
    category = relationship("Category", back_populates="demand_patterns")

class PricingKPI(Base):
    """Pricing key performance indicators and metrics"""
    __tablename__ = "pricing_kpis"
    __table_args__ = {'schema': 'analytics'} if IS_POSTGRES else None
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_date = Column(Date, nullable=False)
    
    # Aggregation dimensions
    product_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("products.id", "products")), nullable=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("brands.id", "core")), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("categories.id", "core")), nullable=True)
    platform_id = Column(UUID(as_uuid=True), ForeignKey(get_schema_ref("platforms.id", "core")), nullable=True)
    aggregation_level = Column(String(20), nullable=False)
    
    # Performance metrics
    average_margin_percent = Column(Numeric(5, 2), nullable=True)
    average_markup_percent = Column(Numeric(5, 2), nullable=True)
    price_realization_percent = Column(Numeric(5, 2), nullable=True)
    competitive_index = Column(Numeric(5, 2), nullable=True)
    conversion_rate_percent = Column(Numeric(5, 2), nullable=True)
    revenue_impact_eur = Column(Numeric(12, 2), nullable=True)
    units_sold = Column(Integer, nullable=True)
    average_selling_price = Column(Numeric(10, 2), nullable=True)
    price_elasticity = Column(Numeric(6, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="pricing_kpis")
    brand = relationship("Brand", back_populates="pricing_kpis")
    category = relationship("Category", back_populates="pricing_kpis")
    platform = relationship("Platform", back_populates="pricing_kpis")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'date': self.kpi_date.isoformat(),
            'level': self.aggregation_level,
            'margin': float(self.average_margin_percent) if self.average_margin_percent else None,
            'markup': float(self.average_markup_percent) if self.average_markup_percent else None,
            'conversion': float(self.conversion_rate_percent) if self.conversion_rate_percent else None,
            'revenue': float(self.revenue_impact_eur) if self.revenue_impact_eur else None,
            'units': self.units_sold,
            'avg_price': float(self.average_selling_price) if self.average_selling_price else None
        }