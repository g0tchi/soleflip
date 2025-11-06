"""
Base Event System for Domain Communication
Enables loose coupling between domains through event-driven architecture.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class BaseEvent(BaseModel):
    """Base class for all domain events"""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    domain: str
    aggregate_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat(), UUID: str}

    @property
    def event_name(self) -> str:
        """Get the full event name"""
        return f"{self.domain}.{self.event_type}"


class DomainEvent(BaseEvent, ABC):
    """Abstract base for domain-specific events"""

    @abstractmethod
    def get_event_data(self) -> Dict[str, Any]:
        """Get the event-specific data payload"""
        pass


class IntegrationEvent(BaseEvent):
    """Events for integration between domains"""

    source_domain: str
    target_domain: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    def get_event_data(self) -> Dict[str, Any]:
        return self.payload


# Specific event types for the import system
class ImportEvent(DomainEvent):
    """Base class for import-related events"""

    domain: str = "integration"


class ImportBatchCreatedEvent(ImportEvent):
    """Event fired when a new import batch is created"""

    event_type: str = "batch_created"

    batch_id: UUID
    source_type: str
    filename: Optional[str] = None
    total_records: Optional[int] = None

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "source_type": self.source_type,
            "filename": self.filename,
            "total_records": self.total_records,
        }


class ImportBatchProgressEvent(ImportEvent):
    """Event fired when import batch progress updates"""

    event_type: str = "batch_progress"

    batch_id: UUID
    processed_records: int
    failed_records: int
    progress_percentage: float
    current_stage: str

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "processed_records": self.processed_records,
            "failed_records": self.failed_records,
            "progress_percentage": self.progress_percentage,
            "current_stage": self.current_stage,
        }


class ImportBatchCompletedEvent(ImportEvent):
    """Event fired when import batch completes"""

    event_type: str = "batch_completed"

    batch_id: UUID
    total_processed: int
    total_failed: int
    processing_time_seconds: float
    success: bool

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "processing_time_seconds": self.processing_time_seconds,
            "success": self.success,
        }


class ImportBatchFailedEvent(ImportEvent):
    """Event fired when import batch fails"""

    event_type: str = "batch_failed"

    batch_id: UUID
    error_message: str
    error_type: str
    failed_at_stage: str

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "error_message": self.error_message,
            "error_type": self.error_type,
            "failed_at_stage": self.failed_at_stage,
        }


# Product domain events
class ProductEvent(DomainEvent):
    """Base class for product-related events"""

    domain: str = "products"


class ProductCreatedEvent(ProductEvent):
    """Event fired when a new product is created"""

    event_type: str = "product_created"

    product_id: UUID
    sku: str
    name: str
    brand: str
    category: str
    source: str

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "product_id": str(self.product_id),
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "source": self.source,
        }


class ProductUpdatedEvent(ProductEvent):
    """Event fired when a product is updated"""

    event_type: str = "product_updated"

    product_id: UUID
    changed_fields: Dict[str, Any]
    previous_values: Dict[str, Any]

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "product_id": str(self.product_id),
            "changed_fields": self.changed_fields,
            "previous_values": self.previous_values,
        }


# Inventory domain events
class InventoryEvent(DomainEvent):
    """Base class for inventory-related events"""

    domain: str = "inventory"


class InventoryUpdatedEvent(InventoryEvent):
    """Event fired when inventory levels change"""

    event_type: str = "inventory_updated"

    product_id: UUID
    previous_quantity: int
    new_quantity: int
    change_reason: str

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "product_id": str(self.product_id),
            "previous_quantity": self.previous_quantity,
            "new_quantity": self.new_quantity,
            "change_reason": self.change_reason,
        }


class LowStockAlertEvent(InventoryEvent):
    """Event fired when stock levels are low"""

    event_type: str = "low_stock_alert"

    product_id: UUID
    current_quantity: int
    threshold: int
    sku: str

    def get_event_data(self) -> Dict[str, Any]:
        return {
            "product_id": str(self.product_id),
            "current_quantity": self.current_quantity,
            "threshold": self.threshold,
            "sku": self.sku,
        }
