"""Domain-specific models for suppliers."""

from typing import Dict

from pydantic import BaseModel


class SupplierPerformanceSummary(BaseModel):
    total_orders: int
    total_revenue: float
    average_roi: float
    top_performing_accounts: list


class SupplierAnalytics(BaseModel):
    category: str
    supplier_count: int
    performance_metrics: Dict[str, float]
