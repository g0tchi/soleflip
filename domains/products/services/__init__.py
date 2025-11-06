"""
Products Services
=================

Business logic for product catalog and brand intelligence.

Services:
- brand_service: Brand extraction and intelligence
- category_service: Category detection and classification
- product_processor: Product data processing
"""

from domains.products.services import brand_service, category_service, product_processor

__all__ = [
    "brand_service",
    "category_service",
    "product_processor",
]
