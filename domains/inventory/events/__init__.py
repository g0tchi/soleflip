"""
Inventory Domain Events
"""

from .handlers import InventoryEventHandler, get_inventory_event_handler

__all__ = [
    "InventoryEventHandler", 
    "get_inventory_event_handler",
]