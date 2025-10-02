"""
Event Handlers for Products Domain
Handles product-related events and cross-domain communication.
"""

import structlog

from shared.events import (
    ProductCreatedEvent,
    ProductUpdatedEvent,
    ImportBatchCompletedEvent,
    subscribe_to_event
)

logger = structlog.get_logger(__name__)


class ProductEventHandler:
    """Event handler for product domain events"""
    
    def __init__(self):
        self._register_handlers()
    
    def _register_handlers(self):
        """Register event handlers"""
        # Listen to own domain events
        subscribe_to_event(ProductCreatedEvent, self.handle_product_created, "products.product_created")
        subscribe_to_event(ProductUpdatedEvent, self.handle_product_updated, "products.product_updated")
        
        # Listen to integration events that affect products
        subscribe_to_event(ImportBatchCompletedEvent, self.handle_import_completed, "products.import_completed")
    
    async def handle_product_created(self, event: ProductCreatedEvent):
        """Handle new product creation"""
        logger.info(
            "Product created",
            product_id=str(event.product_id),
            sku=event.sku,
            name=event.name,
            brand=event.brand,
            category=event.category,
            source=event.source
        )
        
        # Could trigger:
        # - Inventory initialization
        # - Price calculation
        # - Search index updates
        # - Analytics updates
        # - Third-party integrations
    
    async def handle_product_updated(self, event: ProductUpdatedEvent):
        """Handle product updates"""
        logger.info(
            "Product updated",
            product_id=str(event.product_id),
            changed_fields=list(event.changed_fields.keys())
        )
        
        # Could trigger:
        # - Cache invalidation
        # - Search index updates
        # - Price recalculation (if cost changed)
        # - Notification to other systems
        # - Audit trail updates
        
        # Example: If price-related fields changed, update pricing
        price_fields = {'cost', 'msrp', 'base_price'}
        if any(field in price_fields for field in event.changed_fields.keys()):
            logger.info(
                "Price-related fields changed, triggering price updates",
                product_id=str(event.product_id),
                changed_price_fields=[f for f in event.changed_fields.keys() if f in price_fields]
            )
            # Would publish a price update event here
    
    async def handle_import_completed(self, event: ImportBatchCompletedEvent):
        """Handle completed import batches that may have created/updated products"""
        if not event.success:
            return  # Skip failed imports
        
        logger.info(
            "Import batch completed, products may need post-processing",
            batch_id=str(event.batch_id),
            processed_records=event.total_processed
        )
        
        # Could trigger:
        # - Product data validation
        # - Search index rebuild
        # - Cache warming
        # - Analytics recalculation
        # - Duplicate product detection
        # - Category assignment
        # - Price optimization


# Initialize the event handler
_product_handler = None


def get_product_event_handler() -> ProductEventHandler:
    """Get the product event handler instance"""
    global _product_handler
    if _product_handler is None:
        _product_handler = ProductEventHandler()
    return _product_handler