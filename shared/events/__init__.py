"""
Event System for Domain Communication
"""

from .base_event import (  # Import events; Product events; Inventory events
    BaseEvent,
    DomainEvent,
    ImportBatchCompletedEvent,
    ImportBatchCreatedEvent,
    ImportBatchFailedEvent,
    ImportBatchProgressEvent,
    ImportEvent,
    IntegrationEvent,
    InventoryEvent,
    InventoryUpdatedEvent,
    LowStockAlertEvent,
    ProductCreatedEvent,
    ProductEvent,
    ProductUpdatedEvent,
)
from .event_bus import (
    EventBus,
    EventHandler,
    get_event_bus,
    publish_event,
    subscribe_to_domain_events,
    subscribe_to_event,
)

__all__ = [
    # Base classes
    "BaseEvent",
    "DomainEvent",
    "IntegrationEvent",
    # Import events
    "ImportEvent",
    "ImportBatchCreatedEvent",
    "ImportBatchProgressEvent",
    "ImportBatchCompletedEvent",
    "ImportBatchFailedEvent",
    # Product events
    "ProductEvent",
    "ProductCreatedEvent",
    "ProductUpdatedEvent",
    # Inventory events
    "InventoryEvent",
    "InventoryUpdatedEvent",
    "LowStockAlertEvent",
    # Event bus
    "EventBus",
    "EventHandler",
    "get_event_bus",
    "publish_event",
    "subscribe_to_event",
    "subscribe_to_domain_events",
]
