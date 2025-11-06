"""
Inventory Services
==================

Business logic for inventory management, dead stock analysis, and predictive insights.

Services:
- inventory_service: Core inventory management (LARGE - 1,720 lines, refactoring candidate)
- dead_stock_service: Dead stock identification and analysis
- predictive_insights_service: Predictive inventory insights
"""

from domains.inventory.services import (
    dead_stock_service,
    inventory_service,
    predictive_insights_service,
)

__all__ = [
    "inventory_service",
    "dead_stock_service",
    "predictive_insights_service",
]
