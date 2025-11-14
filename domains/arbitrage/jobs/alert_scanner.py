"""
Alert Scanner Background Job

Periodically scans for active arbitrage alerts and processes them.
Runs as a background task in the FastAPI lifespan.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from domains.arbitrage.services.alert_service import AlertService
from domains.arbitrage.services.enhanced_opportunity_service import (
    EnhancedOpportunityService,
)
from shared.database.connection import db_manager

logger = logging.getLogger(__name__)


class AlertScanner:
    """
    Background scanner for arbitrage alerts.

    Runs continuously, checking for alerts ready to trigger
    and processing them.
    """

    def __init__(self, scan_interval_seconds: int = 60):
        """
        Initialize alert scanner.

        Args:
            scan_interval_seconds: Seconds between scan cycles (default: 60)
        """
        self.scan_interval = scan_interval_seconds
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """
        Start the alert scanner background task.

        This runs continuously until the application shuts down.
        """
        self.is_running = True
        self.logger.info(
            f"Alert scanner started. Scan interval: {self.scan_interval} seconds"
        )

        while self.is_running:
            try:
                await self._scan_and_process_alerts()
            except Exception as e:
                self.logger.error(
                    f"Error in alert scanner cycle: {str(e)}", exc_info=True
                )

            # Wait for next cycle
            await asyncio.sleep(self.scan_interval)

    async def stop(self):
        """Stop the alert scanner."""
        self.is_running = False
        self.logger.info("Alert scanner stopped")

    async def _scan_and_process_alerts(self):
        """
        Single scan cycle: find and process alerts ready to trigger.
        """
        scan_start = datetime.now()
        self.logger.debug("Starting alert scan cycle")

        async with db_manager.get_session() as session:
            alert_service = AlertService(session)
            opportunities_service = EnhancedOpportunityService(session)

            # Get alerts ready to trigger
            ready_alerts = await alert_service.get_alerts_ready_to_trigger()

            if not ready_alerts:
                self.logger.debug("No alerts ready to trigger")
                return

            self.logger.info(f"Processing {len(ready_alerts)} alerts")

            # Process each alert
            results = []
            for alert in ready_alerts:
                try:
                    result = await alert_service.process_alert(
                        alert, opportunities_service
                    )
                    results.append(
                        {
                            "alert_id": str(alert.id),
                            "alert_name": alert.alert_name,
                            "result": result,
                        }
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to process alert {alert.id}: {str(e)}", exc_info=True
                    )
                    results.append(
                        {
                            "alert_id": str(alert.id),
                            "alert_name": alert.alert_name,
                            "result": {"status": "error", "error": str(e)},
                        }
                    )

            # Log summary
            scan_duration = (datetime.now() - scan_start).total_seconds()
            success_count = sum(1 for r in results if r["result"]["status"] == "success")
            error_count = len(results) - success_count
            total_opportunities = sum(
                r["result"].get("opportunities_sent", 0) for r in results
            )

            self.logger.info(
                f"Alert scan completed. "
                f"Duration: {scan_duration:.2f}s, "
                f"Alerts processed: {len(results)}, "
                f"Success: {success_count}, "
                f"Errors: {error_count}, "
                f"Total opportunities sent: {total_opportunities}"
            )


# Global scanner instance
_alert_scanner: AlertScanner | None = None


def get_alert_scanner() -> AlertScanner:
    """
    Get the global alert scanner instance.

    Returns:
        AlertScanner instance
    """
    global _alert_scanner
    if _alert_scanner is None:
        _alert_scanner = AlertScanner(scan_interval_seconds=60)
    return _alert_scanner


async def start_alert_scanner():
    """
    Start the alert scanner as a background task.

    This should be called from the FastAPI lifespan.
    """
    scanner = get_alert_scanner()
    await scanner.start()
