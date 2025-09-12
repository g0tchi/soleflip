"""
Products Domain Events
"""

from .handlers import ProductEventHandler, get_product_event_handler

__all__ = [
    "ProductEventHandler",
    "get_product_event_handler",
]