"""
Pydantic schemas for Arbitrage API

Request and response models for arbitrage endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =====================================================
# ENUMS
# =====================================================


class RiskLevelEnum(str, Enum):
    """Risk level classification"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =====================================================
# RESPONSE MODELS
# =====================================================


class DemandScoreResponse(BaseModel):
    """Demand score response"""

    product_id: UUID
    demand_score: float = Field(..., ge=0, le=100, description="Demand score (0-100)")
    breakdown: Dict[str, float] = Field(
        ..., description="Detailed breakdown of demand components"
    )
    pattern_date: date
    trend_direction: str = Field(..., description="increasing, decreasing, or stable")

    class Config:
        from_attributes = True


class RiskFactorsResponse(BaseModel):
    """Risk factors breakdown"""

    demand: str
    volatility: str
    stock: str
    margin: str
    supplier: str


class RiskAssessmentResponse(BaseModel):
    """Risk assessment response"""

    risk_level: RiskLevelEnum
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100, lower is better)")
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence in assessment")
    risk_factors: RiskFactorsResponse
    recommendations: List[str]

    class Config:
        from_attributes = True


class OpportunityBaseResponse(BaseModel):
    """Base opportunity data from QuickFlip"""

    product_id: UUID
    product_name: str
    product_sku: str
    brand_name: Optional[str] = None
    buy_price: Decimal
    buy_source: str
    buy_supplier: Optional[str] = None
    buy_url: Optional[str] = None
    buy_stock_qty: Optional[int] = None
    sell_price: Decimal
    gross_profit: Decimal
    profit_margin: Decimal
    roi: Decimal

    class Config:
        from_attributes = True


class EnhancedOpportunityResponse(BaseModel):
    """Enhanced opportunity with scoring"""

    opportunity: OpportunityBaseResponse
    demand_score: float = Field(..., ge=0, le=100)
    demand_breakdown: Dict[str, float] = {}
    risk_assessment: Optional[RiskAssessmentResponse] = None
    feasibility_score: int = Field(..., ge=0, le=100, description="Composite feasibility score")
    estimated_days_to_sell: Optional[int] = None
    risk_level: str = Field(..., description="LOW, MEDIUM, or HIGH")

    class Config:
        from_attributes = True


class OpportunitySummaryResponse(BaseModel):
    """Summary statistics for opportunities"""

    total_opportunities: int
    avg_feasibility_score: float
    avg_demand_score: float
    avg_risk_score: float
    risk_distribution: Dict[str, int]
    total_potential_profit: float
    estimated_avg_days_to_sell: float

    class Config:
        from_attributes = True


# =====================================================
# REQUEST MODELS
# =====================================================


class OpportunityFilterRequest(BaseModel):
    """Request filters for finding opportunities"""

    min_profit_margin: float = Field(
        default=10.0, ge=0, le=100, description="Minimum profit margin %"
    )
    min_gross_profit: float = Field(default=20.0, ge=0, description="Minimum gross profit €")
    max_buy_price: Optional[float] = Field(default=None, ge=0, description="Maximum buy price €")
    source_filter: Optional[str] = Field(
        default=None, description="Filter by source (awin, webgains, etc.)"
    )
    limit: Optional[int] = Field(default=10, ge=1, le=100, description="Max results")
    calculate_demand: bool = Field(default=True, description="Calculate demand scores")
    calculate_risk: bool = Field(default=True, description="Calculate risk assessments")


class TopOpportunitiesRequest(BaseModel):
    """Request for top opportunities"""

    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    min_feasibility: int = Field(
        default=60, ge=0, le=100, description="Minimum feasibility score"
    )
    max_risk: Optional[RiskLevelEnum] = Field(
        default=RiskLevelEnum.MEDIUM, description="Maximum acceptable risk level"
    )


class BatchAssessRequest(BaseModel):
    """Request for batch risk assessment"""

    product_ids: List[UUID] = Field(
        ..., min_length=1, max_length=50, description="Product IDs to assess (max 50)"
    )


class BatchAssessResponse(BaseModel):
    """Response for batch assessment"""

    assessments: Dict[str, RiskAssessmentResponse]
    total_assessed: int
    failed_assessments: int = 0


# =====================================================
# QUERY PARAMETER MODELS
# =====================================================


class OpportunityQueryParams(BaseModel):
    """Query parameters for opportunity endpoints"""

    min_profit_margin: float = Field(default=10.0, ge=0, le=100)
    min_gross_profit: float = Field(default=20.0, ge=0)
    max_buy_price: Optional[float] = Field(default=None, ge=0)
    source_filter: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Ensure limit is reasonable"""
        if v > 100:
            return 100
        return v


# =====================================================
# ALERT MODELS
# =====================================================


class AlertCreate(BaseModel):
    """Request model for creating an alert"""

    alert_name: str = Field(..., min_length=1, max_length=100, description="Alert name")
    description: Optional[str] = Field(None, max_length=500, description="Alert description")
    n8n_webhook_url: str = Field(
        ..., min_length=10, max_length=500, description="n8n webhook URL"
    )

    # Filter criteria
    min_profit_margin: float = Field(default=10.0, ge=0, le=100)
    min_gross_profit: float = Field(default=20.0, ge=0)
    max_buy_price: Optional[float] = Field(default=None, ge=0)
    min_feasibility_score: int = Field(default=60, ge=0, le=100)
    max_risk_level: RiskLevelEnum = Field(default=RiskLevelEnum.MEDIUM)
    source_filter: Optional[str] = Field(default=None, max_length=50)
    additional_filters: Optional[Dict] = Field(default=None)

    # Notification settings
    notification_config: Optional[Dict] = Field(
        default=None, description="Notification channels config"
    )
    include_demand_breakdown: bool = Field(default=True)
    include_risk_details: bool = Field(default=True)
    max_opportunities_per_alert: int = Field(default=10, ge=1, le=50)

    # Schedule settings
    alert_frequency_minutes: int = Field(default=15, ge=5, le=1440)
    active_hours_start: Optional[str] = Field(
        default=None, description="Start time in HH:MM format"
    )
    active_hours_end: Optional[str] = Field(default=None, description="End time in HH:MM format")
    active_days: Optional[List[str]] = Field(
        default=None, description="Active days: ['monday', 'tuesday', ...]"
    )
    timezone: str = Field(default="Europe/Berlin", max_length=50)
    active: bool = Field(default=True)


class AlertUpdate(BaseModel):
    """Request model for updating an alert"""

    alert_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    n8n_webhook_url: Optional[str] = Field(None, min_length=10, max_length=500)
    min_profit_margin: Optional[float] = Field(None, ge=0, le=100)
    min_gross_profit: Optional[float] = Field(None, ge=0)
    max_buy_price: Optional[float] = Field(None, ge=0)
    min_feasibility_score: Optional[int] = Field(None, ge=0, le=100)
    max_risk_level: Optional[RiskLevelEnum] = None
    source_filter: Optional[str] = Field(None, max_length=50)
    additional_filters: Optional[Dict] = None
    notification_config: Optional[Dict] = None
    include_demand_breakdown: Optional[bool] = None
    include_risk_details: Optional[bool] = None
    max_opportunities_per_alert: Optional[int] = Field(None, ge=1, le=50)
    alert_frequency_minutes: Optional[int] = Field(None, ge=5, le=1440)
    active_hours_start: Optional[str] = None
    active_hours_end: Optional[str] = None
    active_days: Optional[List[str]] = None
    timezone: Optional[str] = Field(None, max_length=50)
    active: Optional[bool] = None


class AlertResponse(BaseModel):
    """Response model for alert"""

    id: UUID
    user_id: UUID
    alert_name: str
    description: Optional[str]
    active: bool
    n8n_webhook_url: str

    # Filters
    min_profit_margin: float
    min_gross_profit: float
    max_buy_price: Optional[float]
    min_feasibility_score: int
    max_risk_level: RiskLevelEnum
    source_filter: Optional[str]
    additional_filters: Optional[Dict]

    # Notification
    notification_config: Optional[Dict]
    include_demand_breakdown: bool
    include_risk_details: bool
    max_opportunities_per_alert: int

    # Schedule
    alert_frequency_minutes: int
    active_hours_start: Optional[str]
    active_hours_end: Optional[str]
    active_days: Optional[List[str]]
    timezone: str

    # Tracking
    last_triggered_at: Optional[datetime]
    last_scanned_at: Optional[datetime]
    total_alerts_sent: int
    total_opportunities_sent: int
    last_error: Optional[str]
    last_error_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertToggleRequest(BaseModel):
    """Request to enable/disable alert"""

    active: bool = Field(..., description="True to enable, False to disable")


class AlertStatsResponse(BaseModel):
    """Alert statistics response"""

    alert_id: str
    alert_name: str
    active: bool
    total_alerts_sent: int
    total_opportunities_sent: int
    avg_opportunities_per_alert: float
    last_triggered_at: Optional[str]
    last_scanned_at: Optional[str]
    last_error: Optional[str]
    last_error_at: Optional[str]
