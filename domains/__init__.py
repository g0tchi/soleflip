"""
Domains Package
===============

This package contains all domain-specific business logic following Domain-Driven Design (DDD) principles.

Each domain is self-contained with its own:
- API routes (api/)
- Business logic (services/)
- Data access (repositories/)
- Domain events (events/)

Available Domains:
- admin: Administration and security-restricted operations
- analytics: Forecasting, KPI calculations, and business intelligence
- auth: JWT authentication and authorization
- dashboard: Dashboard data aggregation and metrics
- integration: External platform integrations (StockX, Budibase, Metabase, AWIN)
- inventory: Product inventory management and dead stock analysis
- orders: Multi-platform order management (StockX, eBay, GOAT, Alias)
- pricing: Smart pricing engine and auto-listing service
- products: Product catalog and brand intelligence
- sales: Legacy sales domain (deprecated - use orders instead)
- suppliers: Supplier account management
"""

__all__ = [
    "admin",
    "analytics",
    "auth",
    "dashboard",
    "integration",
    "inventory",
    "orders",
    "pricing",
    "products",
    "sales",
    "suppliers",
]
