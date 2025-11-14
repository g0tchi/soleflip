"""
Event Handlers for Integration Domain
Handles cross-domain events related to import processing.
"""

import structlog

from shared.events import (
    ImportBatchCompletedEvent,
    ImportBatchCreatedEvent,
    ImportBatchFailedEvent,
    ImportBatchProgressEvent,
    subscribe_to_event,
)

logger = structlog.get_logger(__name__)


class IntegrationEventHandler:
    """Event handler for integration domain events"""

    def __init__(self):
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers"""
        subscribe_to_event(
            ImportBatchCreatedEvent, self.handle_batch_created, "integration.batch_created"
        )
        subscribe_to_event(
            ImportBatchProgressEvent, self.handle_batch_progress, "integration.batch_progress"
        )
        subscribe_to_event(
            ImportBatchCompletedEvent, self.handle_batch_completed, "integration.batch_completed"
        )
        subscribe_to_event(
            ImportBatchFailedEvent, self.handle_batch_failed, "integration.batch_failed"
        )

    async def handle_batch_created(self, event: ImportBatchCreatedEvent):
        """Handle new import batch creation"""
        logger.info(
            "Import batch created",
            batch_id=str(event.batch_id),
            source_type=event.source_type,
            filename=event.filename,
            total_records=event.total_records,
        )

        # Could trigger notifications, monitoring alerts, etc.
        # For now, just log the event

    async def handle_batch_progress(self, event: ImportBatchProgressEvent):
        """Handle import batch progress updates"""
        logger.debug(
            "Import batch progress update",
            batch_id=str(event.batch_id),
            processed=event.processed_records,
            failed=event.failed_records,
            progress=event.progress_percentage,
            stage=event.current_stage,
        )

        # Could update real-time dashboards, send progress notifications
        # Trigger alerts if failure rate is too high
        if event.processed_records > 0:
            failure_rate = (event.failed_records / event.processed_records) * 100
            if failure_rate > 10:  # Alert if >10% failure rate
                logger.warning(
                    "High import failure rate detected",
                    batch_id=str(event.batch_id),
                    failure_rate=failure_rate,
                )

    async def handle_batch_completed(self, event: ImportBatchCompletedEvent):
        """Handle import batch completion"""
        logger.info(
            "Import batch completed",
            batch_id=str(event.batch_id),
            processed=event.total_processed,
            failed=event.total_failed,
            duration=event.processing_time_seconds,
            success=event.success,
        )

        # Could trigger post-processing tasks:
        # - Update analytics
        # - Send completion notifications
        # - Trigger dependent workflows
        # - Update monitoring metrics

        # Example: Log performance metrics
        if event.total_processed > 0:
            records_per_second = event.total_processed / event.processing_time_seconds
            logger.info(
                "Import performance metrics",
                batch_id=str(event.batch_id),
                records_per_second=records_per_second,
                total_duration=event.processing_time_seconds,
            )

    async def handle_batch_failed(self, event: ImportBatchFailedEvent):
        """Handle import batch failure"""
        logger.error(
            "Import batch failed",
            batch_id=str(event.batch_id),
            error_message=event.error_message,
            error_type=event.error_type,
            failed_stage=event.failed_at_stage,
        )

        # Could trigger:
        # - Error alerts/notifications
        # - Retry mechanisms
        # - Support ticket creation
        # - Failure analysis


# Initialize the event handler
_integration_handler = None


def get_integration_event_handler() -> IntegrationEventHandler:
    """Get the integration event handler instance"""
    global _integration_handler
    if _integration_handler is None:
        _integration_handler = IntegrationEventHandler()
    return _integration_handler
