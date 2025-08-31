"""
Forecast Repository - Data access layer for forecasting operations
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from domains.pricing.models import DemandPattern, ForecastAccuracy, PricingKPI, SalesForecast
from shared.database.models import Brand, Category, InventoryItem, Platform, Product, Transaction


class ForecastRepository:
    """Repository for forecasting and analytics data operations"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # =====================================================
    # SALES FORECASTS MANAGEMENT
    # =====================================================

    async def create_forecast_batch(
        self, forecast_run_id: uuid.UUID, forecasts: List[Dict[str, Any]]
    ) -> List[SalesForecast]:
        """Create a batch of forecasts for a single run"""
        forecast_objects = []

        for forecast_data in forecasts:
            forecast_data["forecast_run_id"] = forecast_run_id
            forecast = SalesForecast(**forecast_data)
            self.db.add(forecast)
            forecast_objects.append(forecast)

        await self.db.flush()
        return forecast_objects

    async def get_latest_forecasts(
        self,
        forecast_level: str,
        forecast_horizon: str,
        limit_days: int = 30,
        entity_id: Optional[uuid.UUID] = None,
    ) -> List[SalesForecast]:
        """Get latest forecasts for specified parameters"""
        query = (
            select(SalesForecast)
            .where(
                SalesForecast.forecast_level == forecast_level,
                SalesForecast.forecast_horizon == forecast_horizon,
                SalesForecast.forecast_date >= date.today(),
                SalesForecast.forecast_date <= date.today() + timedelta(days=limit_days),
            )
            .options(
                joinedload(SalesForecast.product),
                joinedload(SalesForecast.brand),
                joinedload(SalesForecast.category),
                joinedload(SalesForecast.platform),
            )
            .order_by(SalesForecast.forecast_date.asc())
        )

        # Apply entity filter based on forecast level
        if entity_id:
            if forecast_level == "product":
                query = query.where(SalesForecast.product_id == entity_id)
            elif forecast_level == "brand":
                query = query.where(SalesForecast.brand_id == entity_id)
            elif forecast_level == "category":
                query = query.where(SalesForecast.category_id == entity_id)
            elif forecast_level == "platform":
                query = query.where(SalesForecast.platform_id == entity_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_forecast_by_run(
        self, forecast_run_id: uuid.UUID, forecast_level: Optional[str] = None
    ) -> List[SalesForecast]:
        """Get all forecasts for a specific run"""
        query = (
            select(SalesForecast)
            .where(SalesForecast.forecast_run_id == forecast_run_id)
            .options(joinedload(SalesForecast.product), joinedload(SalesForecast.brand))
        )

        if forecast_level:
            query = query.where(SalesForecast.forecast_level == forecast_level)

        query = query.order_by(SalesForecast.forecast_date.asc())

        result = await self.db.execute(query)
        return result.scalars().all()

    # =====================================================
    # HISTORICAL DATA FOR TRAINING
    # =====================================================

    async def get_historical_sales_data(
        self,
        entity_type: str,
        entity_id: Optional[uuid.UUID] = None,
        days_back: int = 365,
        aggregation: str = "daily",
    ) -> List[Dict[str, Any]]:
        """Get historical sales data for model training"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Base query for transactions
        if aggregation == "daily":
            date_trunc = func.date_trunc("day", Transaction.transaction_date)
            date_format = "YYYY-MM-DD"
        elif aggregation == "weekly":
            date_trunc = func.date_trunc("week", Transaction.transaction_date)
            date_format = 'YYYY-"W"WW'
        elif aggregation == "monthly":
            date_trunc = func.date_trunc("month", Transaction.transaction_date)
            date_format = "YYYY-MM"
        else:
            raise ValueError(f"Invalid aggregation: {aggregation}")

        # Build aggregation query based on entity type
        if entity_type == "product":
            query = (
                select(
                    func.to_char(date_trunc, date_format).label("period"),
                    date_trunc.label("period_date"),
                    Transaction.product_id.label("entity_id"),
                    func.count(Transaction.id).label("units_sold"),
                    func.sum(Transaction.net_revenue).label("total_revenue"),
                    func.avg(Transaction.net_revenue).label("avg_price"),
                )
                .select_from(Transaction)
                .where(
                    Transaction.transaction_date.between(start_date, end_date),
                    Transaction.status == "completed",
                )
                .group_by(date_trunc, Transaction.product_id)
                .order_by(date_trunc.asc())
            )

            if entity_id:
                query = query.where(Transaction.product_id == entity_id)

        elif entity_type == "brand":
            query = (
                select(
                    func.to_char(date_trunc, date_format).label("period"),
                    date_trunc.label("period_date"),
                    Product.brand_id.label("entity_id"),
                    func.count(Transaction.id).label("units_sold"),
                    func.sum(Transaction.net_revenue).label("total_revenue"),
                    func.avg(Transaction.net_revenue).label("avg_price"),
                )
                .select_from(Transaction)
                .join(Product, Transaction.product_id == Product.id)
                .where(
                    Transaction.transaction_date.between(start_date, end_date),
                    Transaction.status == "completed",
                )
                .group_by(date_trunc, Product.brand_id)
                .order_by(date_trunc.asc())
            )

            if entity_id:
                query = query.where(Product.brand_id == entity_id)

        elif entity_type == "category":
            query = (
                select(
                    func.to_char(date_trunc, date_format).label("period"),
                    date_trunc.label("period_date"),
                    Product.category_id.label("entity_id"),
                    func.count(Transaction.id).label("units_sold"),
                    func.sum(Transaction.net_revenue).label("total_revenue"),
                    func.avg(Transaction.net_revenue).label("avg_price"),
                )
                .select_from(Transaction)
                .join(Product, Transaction.product_id == Product.id)
                .where(
                    Transaction.transaction_date.between(start_date, end_date),
                    Transaction.status == "completed",
                )
                .group_by(date_trunc, Product.category_id)
                .order_by(date_trunc.asc())
            )

            if entity_id:
                query = query.where(Product.category_id == entity_id)

        else:
            raise ValueError(f"Invalid entity type: {entity_type}")

        result = await self.db.execute(query)
        rows = result.all()

        # Convert to list of dictionaries
        historical_data = []
        for row in rows:
            historical_data.append(
                {
                    "period": row.period,
                    "period_date": (
                        row.period_date.date()
                        if hasattr(row.period_date, "date")
                        else row.period_date
                    ),
                    "entity_id": str(row.entity_id) if row.entity_id else None,
                    "units_sold": int(row.units_sold) if row.units_sold else 0,
                    "total_revenue": float(row.total_revenue) if row.total_revenue else 0.0,
                    "avg_price": float(row.avg_price) if row.avg_price else 0.0,
                }
            )

        return historical_data

    async def get_external_features(
        self,
        entity_type: str,
        entity_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Get external features for model training (seasonality, trends, etc.)"""
        if not start_date:
            start_date = date.today() - timedelta(days=365)
        if not end_date:
            end_date = date.today()

        # This would typically pull from external data sources
        # For now, we'll create some basic seasonal and trend features
        features = []
        current_date = start_date

        while current_date <= end_date:
            # Basic seasonal features
            month = current_date.month
            day_of_year = current_date.timetuple().tm_yday
            quarter = (month - 1) // 3 + 1

            # Holiday indicators (basic)
            is_holiday = self._is_holiday(current_date)
            is_weekend = current_date.weekday() >= 5

            # Seasonal multipliers
            seasonal_multiplier = self._get_seasonal_multiplier(month)

            features.append(
                {
                    "date": current_date,
                    "month": month,
                    "quarter": quarter,
                    "day_of_year": day_of_year,
                    "is_weekend": is_weekend,
                    "is_holiday": is_holiday,
                    "seasonal_multiplier": seasonal_multiplier,
                    "trend": day_of_year / 365.0,  # Simple linear trend
                }
            )

            current_date += timedelta(days=1)

        return features

    # =====================================================
    # FORECAST ACCURACY TRACKING
    # =====================================================

    async def record_forecast_accuracy(self, accuracy_data: Dict[str, Any]) -> ForecastAccuracy:
        """Record forecast accuracy metrics"""
        accuracy = ForecastAccuracy(**accuracy_data)
        self.db.add(accuracy)
        await self.db.flush()
        return accuracy

    async def get_model_accuracy_history(
        self,
        model_name: str,
        forecast_level: Optional[str] = None,
        forecast_horizon: Optional[str] = None,
        days_back: int = 90,
    ) -> List[ForecastAccuracy]:
        """Get accuracy history for a model"""
        start_date = date.today() - timedelta(days=days_back)

        query = (
            select(ForecastAccuracy)
            .where(
                ForecastAccuracy.model_name == model_name,
                ForecastAccuracy.accuracy_date >= start_date,
            )
            .order_by(desc(ForecastAccuracy.accuracy_date))
        )

        if forecast_level:
            query = query.where(ForecastAccuracy.forecast_level == forecast_level)
        if forecast_horizon:
            query = query.where(ForecastAccuracy.forecast_horizon == forecast_horizon)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def calculate_forecast_accuracy(
        self, forecast_run_id: uuid.UUID, actual_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate accuracy metrics by comparing forecasts with actual data"""
        # Get forecasts for the run
        forecasts = await self.get_forecast_by_run(forecast_run_id)

        if not forecasts or not actual_data:
            return {}

        # Create lookup for actual data
        actual_lookup = {(item["entity_id"], item["date"]): item for item in actual_data}

        # Calculate accuracy metrics
        errors = []
        percentage_errors = []
        squared_errors = []

        for forecast in forecasts:
            # Determine entity_id based on forecast level
            if forecast.forecast_level == "product":
                entity_id = str(forecast.product_id)
            elif forecast.forecast_level == "brand":
                entity_id = str(forecast.brand_id)
            elif forecast.forecast_level == "category":
                entity_id = str(forecast.category_id)
            else:
                continue

            actual_key = (entity_id, forecast.forecast_date)
            actual_item = actual_lookup.get(actual_key)

            if actual_item:
                actual_value = actual_item["units_sold"]
                forecast_value = float(forecast.forecasted_units)

                if actual_value > 0:
                    error = abs(forecast_value - actual_value)
                    percentage_error = (error / actual_value) * 100
                    squared_error = (forecast_value - actual_value) ** 2

                    errors.append(error)
                    percentage_errors.append(percentage_error)
                    squared_errors.append(squared_error)

        if not errors:
            return {}

        # Calculate metrics
        mae = sum(errors) / len(errors)  # Mean Absolute Error
        mape = sum(percentage_errors) / len(percentage_errors)  # Mean Absolute Percentage Error
        rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5  # Root Mean Square Error

        # Calculate R-squared (simplified)
        actual_values = [
            actual_lookup[(entity_id, fc.forecast_date)]["units_sold"]
            for fc in forecasts
            if (str(fc.product_id or fc.brand_id or fc.category_id), fc.forecast_date)
            in actual_lookup
        ]

        if actual_values:
            actual_mean = sum(actual_values) / len(actual_values)
            total_sum_squares = sum((val - actual_mean) ** 2 for val in actual_values)
            residual_sum_squares = sum(squared_errors)
            r2 = 1 - (residual_sum_squares / total_sum_squares) if total_sum_squares > 0 else 0
        else:
            r2 = 0

        return {
            "mae": mae,
            "mape": mape,
            "rmse": rmse,
            "r2": max(0, r2),  # Ensure R2 is not negative
            "records_evaluated": len(errors),
        }

    # =====================================================
    # DEMAND PATTERNS ANALYSIS
    # =====================================================

    async def create_demand_pattern(self, pattern_data: Dict[str, Any]) -> DemandPattern:
        """Create demand pattern record"""
        pattern = DemandPattern(**pattern_data)
        self.db.add(pattern)
        await self.db.flush()
        return pattern

    async def get_demand_patterns(
        self,
        entity_type: str,
        entity_id: Optional[uuid.UUID] = None,
        period_type: Optional[str] = None,
        days_back: int = 90,
    ) -> List[DemandPattern]:
        """Get demand patterns for analysis"""
        start_date = date.today() - timedelta(days=days_back)

        query = (
            select(DemandPattern)
            .where(
                DemandPattern.analysis_level == entity_type,
                DemandPattern.pattern_date >= start_date,
            )
            .options(
                joinedload(DemandPattern.product),
                joinedload(DemandPattern.brand),
                joinedload(DemandPattern.category),
            )
            .order_by(desc(DemandPattern.pattern_date))
        )

        if entity_id:
            if entity_type == "product":
                query = query.where(DemandPattern.product_id == entity_id)
            elif entity_type == "brand":
                query = query.where(DemandPattern.brand_id == entity_id)
            elif entity_type == "category":
                query = query.where(DemandPattern.category_id == entity_id)

        if period_type:
            query = query.where(DemandPattern.period_type == period_type)

        result = await self.db.execute(query)
        return result.scalars().all()

    # =====================================================
    # PRICING KPIs
    # =====================================================

    async def create_pricing_kpi(self, kpi_data: Dict[str, Any]) -> PricingKPI:
        """Create pricing KPI record"""
        kpi = PricingKPI(**kpi_data)
        self.db.add(kpi)
        await self.db.flush()
        return kpi

    async def get_pricing_kpis(
        self, aggregation_level: str, entity_id: Optional[uuid.UUID] = None, days_back: int = 30
    ) -> List[PricingKPI]:
        """Get pricing KPIs for analysis"""
        start_date = date.today() - timedelta(days=days_back)

        query = (
            select(PricingKPI)
            .where(
                PricingKPI.aggregation_level == aggregation_level, PricingKPI.kpi_date >= start_date
            )
            .order_by(desc(PricingKPI.kpi_date))
        )

        if entity_id:
            if aggregation_level == "product":
                query = query.where(PricingKPI.product_id == entity_id)
            elif aggregation_level == "brand":
                query = query.where(PricingKPI.brand_id == entity_id)
            elif aggregation_level == "category":
                query = query.where(PricingKPI.category_id == entity_id)
            elif aggregation_level == "platform":
                query = query.where(PricingKPI.platform_id == entity_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _is_holiday(self, check_date: date) -> bool:
        """Check if date is a holiday (simplified)"""
        # Basic holiday detection - would be expanded with proper holiday calendar
        holidays = [
            (1, 1),  # New Year
            (12, 25),  # Christmas
            (12, 26),  # Boxing Day
        ]
        return (check_date.month, check_date.day) in holidays

    def _get_seasonal_multiplier(self, month: int) -> float:
        """Get seasonal multiplier for month"""
        # Sneaker industry seasonality (simplified)
        seasonal_factors = {
            1: 0.85,  # January - Post-holiday low
            2: 0.9,  # February
            3: 1.05,  # March - Spring releases
            4: 1.1,  # April - Spring peak
            5: 1.0,  # May
            6: 0.95,  # June - Summer start
            7: 0.9,  # July - Summer low
            8: 1.0,  # August - Back to school prep
            9: 1.15,  # September - Back to school peak
            10: 1.1,  # October - Fall releases
            11: 1.2,  # November - Holiday shopping
            12: 1.25,  # December - Holiday peak
        }
        return seasonal_factors.get(month, 1.0)
