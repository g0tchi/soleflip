"""
Pydantic schemas for Arbitrage API

Request and response models for arbitrage endpoints.
"""

from datetime import date
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
