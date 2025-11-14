"""
Event Handlers for Inventory Domain
Handles inventory-related events and cross-domain communication.
"""

import structlog

from shared.events import (
    ImportBatchCompletedEvent,
    InventoryUpdatedEvent,
    LowStockAlertEvent,
    ProductCreatedEvent,
    publish_event,
    subscribe_to_event,
)

logger = structlog.get_logger(__name__)


class InventoryEventHandler:
    """Event handler for inventory domain events"""

    def __init__(self):
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers"""
        # Listen to own domain events
        subscribe_to_event(
            InventoryUpdatedEvent, self.handle_inventory_updated, "inventory.inventory_updated"
        )
        subscribe_to_event(
            LowStockAlertEvent, self.handle_low_stock_alert, "inventory.low_stock_alert"
        )

        # Listen to product events that affect inventory
        subscribe_to_event(
            ProductCreatedEvent, self.handle_product_created, "inventory.product_created"
        )
        subscribe_to_event(
            ImportBatchCompletedEvent, self.handle_import_completed, "inventory.import_completed"
        )

    async def handle_inventory_updated(self, event: InventoryUpdatedEvent):
        """Handle inventory level changes"""
        logger.info(
            "Inventory updated",
            product_id=str(event.product_id),
            previous_quantity=event.previous_quantity,
            new_quantity=event.new_quantity,
            change_reason=event.change_reason,
        )

        # Could trigger:
        # - Reorder point checks
        # - Analytics updates
        # - Pricing adjustments
        # - Sales channel updates
        # - Warehouse notifications

        # Example: Check if we need to trigger low stock alert
        # This would typically check against a threshold stored in the database
        LOW_STOCK_THRESHOLD = 10  # Example threshold
        if (
            event.new_quantity <= LOW_STOCK_THRESHOLD
            and event.previous_quantity > LOW_STOCK_THRESHOLD
        ):
            # We just crossed the low stock threshold
            await self._trigger_low_stock_alert(
                event.product_id, event.new_quantity, LOW_STOCK_THRESHOLD
            )

    async def handle_low_stock_alert(self, event: LowStockAlertEvent):
        """Handle low stock alerts"""
        logger.warning(
            "Low stock alert triggered",
            product_id=str(event.product_id),
            sku=event.sku,
            current_quantity=event.current_quantity,
            threshold=event.threshold,
        )

        # Could trigger:
        # - Automatic reordering
        # - Buyer notifications
        # - Sales team alerts
        # - Supply chain notifications
        # - Price adjustments to slow demand

    async def handle_product_created(self, event: ProductCreatedEvent):
        """Handle new product creation - initialize inventory"""
        logger.info(
            "New product created, initializing inventory",
            product_id=str(event.product_id),
            sku=event.sku,
            source=event.source,
        )

        # Could trigger:
        # - Initial inventory record creation
        # - Warehouse setup
        # - Stock location assignment
        # - Initial stock ordering

    async def handle_import_completed(self, event: ImportBatchCompletedEvent):
        """Handle completed import batches that may affect inventory"""
        if not event.success:
            return  # Skip failed imports

        logger.info(
            "Import batch completed, inventory may need updates",
            batch_id=str(event.batch_id),
            processed_records=event.total_processed,
        )

        # Could trigger:
        # - Inventory reconciliation
        # - Stock level verification
        # - Warehouse sync
        # - Reorder point updates

    async def _trigger_low_stock_alert(self, product_id, current_quantity: int, threshold: int):
        """Helper method to trigger low stock alert"""
        try:
            # In a real implementation, we'd fetch the product SKU from the database
            # For now, just use a placeholder
            await publish_event(
                LowStockAlertEvent(
                    aggregate_id=product_id,
                    product_id=product_id,
                    current_quantity=current_quantity,
                    threshold=threshold,
                    sku="unknown",  # Would be fetched from database
                )
            )
        except Exception as e:
            logger.error(
                "Failed to publish low stock alert event", product_id=str(product_id), error=str(e)
            )


# Initialize the event handler
_inventory_handler = None


def get_inventory_event_handler() -> InventoryEventHandler:
    """Get the inventory event handler instance"""
    global _inventory_handler
    if _inventory_handler is None:
        _inventory_handler = InventoryEventHandler()
    return _inventory_handler
