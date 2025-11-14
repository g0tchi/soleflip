"""
Alert Service - Manages arbitrage opportunity alerts

This service handles:
- CRUD operations for user alerts
- Finding alerts ready to trigger
- Matching opportunities against alert criteria
- Sending notifications via n8n webhooks
- Tracking alert statistics and errors
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.arbitrage.models.alert import ArbitrageAlert, RiskLevelFilter
from domains.arbitrage.services.enhanced_opportunity_service import (
    EnhancedOpportunity,
    EnhancedOpportunityService,
)
from domains.arbitrage.services.risk_scorer import RiskLevel

logger = logging.getLogger(__name__)


class AlertService:
    """
    Alert management service for arbitrage opportunities.

    Provides:
    - CRUD operations for alerts
    - Alert triggering logic
    - n8n webhook notifications
    - Alert statistics tracking
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    # =====================================================
    # CRUD OPERATIONS
    # =====================================================

    async def create_alert(
        self,
        user_id: UUID,
        alert_name: str,
        n8n_webhook_url: str,
        min_profit_margin: float = 10.0,
        min_gross_profit: float = 20.0,
        min_feasibility_score: int = 60,
        max_risk_level: RiskLevelFilter = RiskLevelFilter.MEDIUM,
        **kwargs,
    ) -> ArbitrageAlert:
        """
        Create a new arbitrage alert.

        Args:
            user_id: User ID creating the alert
            alert_name: Name/description of alert
            n8n_webhook_url: Webhook URL for notifications
            min_profit_margin: Minimum profit margin %
            min_gross_profit: Minimum gross profit €
            min_feasibility_score: Minimum feasibility score (0-100)
            max_risk_level: Maximum acceptable risk level
            **kwargs: Additional alert configuration

        Returns:
            Created ArbitrageAlert instance
        """
        alert = ArbitrageAlert(
            user_id=user_id,
            alert_name=alert_name,
            n8n_webhook_url=n8n_webhook_url,
            min_profit_margin=min_profit_margin,
            min_gross_profit=min_gross_profit,
            min_feasibility_score=min_feasibility_score,
            max_risk_level=max_risk_level,
            **kwargs,
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        self.logger.info(f"Created alert '{alert_name}' for user {user_id}")
        return alert

    async def get_alert(self, alert_id: UUID) -> Optional[ArbitrageAlert]:
        """Get alert by ID"""
        stmt = select(ArbitrageAlert).where(ArbitrageAlert.id == alert_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_alerts(
        self, user_id: UUID, active_only: bool = False
    ) -> List[ArbitrageAlert]:
        """
        Get all alerts for a user.

        Args:
            user_id: User ID
            active_only: Only return active alerts

        Returns:
            List of alerts
        """
        stmt = select(ArbitrageAlert).where(ArbitrageAlert.user_id == user_id)

        if active_only:
            stmt = stmt.where(ArbitrageAlert.active == True)  # noqa: E712

        stmt = stmt.order_by(ArbitrageAlert.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_alert(
        self, alert_id: UUID, update_data: Dict
    ) -> Optional[ArbitrageAlert]:
        """
        Update alert configuration.

        Args:
            alert_id: Alert ID to update
            update_data: Dictionary of fields to update

        Returns:
            Updated alert or None if not found
        """
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        for key, value in update_data.items():
            if hasattr(alert, key):
                setattr(alert, key, value)

        await self.db.commit()
        await self.db.refresh(alert)

        self.logger.info(f"Updated alert {alert_id}")
        return alert

    async def delete_alert(self, alert_id: UUID) -> bool:
        """
        Delete an alert.

        Args:
            alert_id: Alert ID to delete

        Returns:
            True if deleted, False if not found
        """
        alert = await self.get_alert(alert_id)
        if not alert:
            return False

        await self.db.delete(alert)
        await self.db.commit()

        self.logger.info(f"Deleted alert {alert_id}")
        return True

    async def toggle_alert(self, alert_id: UUID, active: bool) -> Optional[ArbitrageAlert]:
        """
        Enable or disable an alert.

        Args:
            alert_id: Alert ID
            active: True to enable, False to disable

        Returns:
            Updated alert or None if not found
        """
        return await self.update_alert(alert_id, {"active": active})

    # =====================================================
    # ALERT TRIGGERING
    # =====================================================

    async def get_alerts_ready_to_trigger(
        self, current_time: datetime = None
    ) -> List[ArbitrageAlert]:
        """
        Get all alerts that should trigger now.

        Considers:
        - Active status
        - Alert frequency
        - Last scan time
        - Active hours
        - Active days

        Args:
            current_time: Current datetime (defaults to now)

        Returns:
            List of alerts ready to trigger
        """
        if current_time is None:
            current_time = datetime.now()

        # Get all active alerts
        stmt = select(ArbitrageAlert).where(ArbitrageAlert.active == True)  # noqa: E712
        result = await self.db.execute(stmt)
        all_active_alerts = list(result.scalars().all())

        # Filter alerts that should trigger now
        ready_alerts = [
            alert for alert in all_active_alerts if alert.should_trigger_now(current_time)
        ]

        self.logger.info(f"Found {len(ready_alerts)} alerts ready to trigger")
        return ready_alerts

    async def process_alert(
        self, alert: ArbitrageAlert, opportunities_service: EnhancedOpportunityService
    ) -> Dict:
        """
        Process a single alert: find matching opportunities and send notification.

        Args:
            alert: Alert to process
            opportunities_service: Service for finding opportunities

        Returns:
            Processing result with status and details
        """
        self.logger.info(f"Processing alert: {alert.alert_name} (ID: {alert.id})")

        try:
            # Update last scanned timestamp
            alert.last_scanned_at = datetime.now()

            # Find matching opportunities
            opportunities = await self._find_matching_opportunities(
                alert, opportunities_service
            )

            if not opportunities:
                self.logger.info(f"No matching opportunities for alert {alert.id}")
                await self.db.commit()
                return {"status": "success", "opportunities_found": 0, "notification_sent": False}

            # Limit opportunities per alert
            limited_opportunities = opportunities[: alert.max_opportunities_per_alert]

            # Send notification
            notification_result = await self._send_notification(alert, limited_opportunities)

            if notification_result["success"]:
                # Update alert statistics
                alert.increment_alert_stats(len(limited_opportunities))
                await self.db.commit()

                self.logger.info(
                    f"Alert {alert.id} processed successfully. "
                    f"Sent {len(limited_opportunities)} opportunities"
                )

                return {
                    "status": "success",
                    "opportunities_found": len(opportunities),
                    "opportunities_sent": len(limited_opportunities),
                    "notification_sent": True,
                }
            else:
                # Record error
                alert.record_error(notification_result.get("error", "Unknown error"))
                await self.db.commit()

                self.logger.error(
                    f"Failed to send notification for alert {alert.id}: "
                    f"{notification_result.get('error')}"
                )

                return {
                    "status": "error",
                    "opportunities_found": len(opportunities),
                    "notification_sent": False,
                    "error": notification_result.get("error"),
                }

        except Exception as e:
            self.logger.error(f"Error processing alert {alert.id}: {str(e)}", exc_info=True)
            alert.record_error(str(e))
            await self.db.commit()

            return {
                "status": "error",
                "opportunities_found": 0,
                "notification_sent": False,
                "error": str(e),
            }

    async def _find_matching_opportunities(
        self, alert: ArbitrageAlert, opportunities_service: EnhancedOpportunityService
    ) -> List[EnhancedOpportunity]:
        """
        Find opportunities matching alert criteria.

        Args:
            alert: Alert with filter criteria
            opportunities_service: Service for finding opportunities

        Returns:
            List of matching enhanced opportunities
        """
        # Convert alert's max_risk to RiskLevel enum
        risk_level_map = {
            RiskLevelFilter.LOW: RiskLevel.LOW,
            RiskLevelFilter.MEDIUM: RiskLevel.MEDIUM,
            RiskLevelFilter.HIGH: RiskLevel.HIGH,
        }
        max_risk = risk_level_map[alert.max_risk_level]

        # Get opportunities using the enhanced service
        opportunities = await opportunities_service.get_top_opportunities(
            limit=100,  # Get more than needed, we'll filter
            min_feasibility=alert.min_feasibility_score,
            max_risk=max_risk,
            min_profit_margin=float(alert.min_profit_margin),
            min_gross_profit=float(alert.min_gross_profit),
            max_buy_price=float(alert.max_buy_price) if alert.max_buy_price else None,
            source_filter=alert.source_filter,
        )

        # Apply additional filters if configured
        if alert.additional_filters:
            opportunities = self._apply_additional_filters(
                opportunities, alert.additional_filters
            )

        return opportunities

    def _apply_additional_filters(
        self, opportunities: List[EnhancedOpportunity], filters: Dict
    ) -> List[EnhancedOpportunity]:
        """
        Apply additional custom filters to opportunities.

        Args:
            opportunities: List of opportunities to filter
            filters: Dictionary of additional filter criteria

        Returns:
            Filtered list of opportunities
        """
        filtered = opportunities

        # Brand filter
        if "brand" in filters:
            brand_filter = filters["brand"].lower()
            filtered = [
                opp
                for opp in filtered
                if opp.opportunity.brand_name
                and brand_filter in opp.opportunity.brand_name.lower()
            ]

        # Supplier filter
        if "supplier" in filters:
            supplier_filter = filters["supplier"].lower()
            filtered = [
                opp
                for opp in filtered
                if opp.opportunity.buy_supplier
                and supplier_filter in opp.opportunity.buy_supplier.lower()
            ]

        # Min ROI filter
        if "min_roi" in filters:
            min_roi = float(filters["min_roi"])
            filtered = [opp for opp in filtered if float(opp.opportunity.roi) >= min_roi]

        # Min demand score filter
        if "min_demand_score" in filters:
            min_demand = float(filters["min_demand_score"])
            filtered = [opp for opp in filtered if opp.demand_score >= min_demand]

        return filtered

    async def _send_notification(
        self, alert: ArbitrageAlert, opportunities: List[EnhancedOpportunity]
    ) -> Dict:
        """
        Send notification via n8n webhook.

        Args:
            alert: Alert configuration
            opportunities: Opportunities to include in notification

        Returns:
            Result dictionary with success status
        """
        # Build notification payload
        payload = self._build_notification_payload(alert, opportunities)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(alert.n8n_webhook_url, json=payload)
                response.raise_for_status()

            self.logger.info(f"Notification sent successfully for alert {alert.id}")
            return {"success": True}

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error sending notification: {str(e)}")
            return {"success": False, "error": f"HTTP error: {str(e)}"}

        except Exception as e:
            self.logger.error(f"Error sending notification: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _build_notification_payload(
        self, alert: ArbitrageAlert, opportunities: List[EnhancedOpportunity]
    ) -> Dict:
        """
        Build notification payload for n8n webhook.

        Args:
            alert: Alert configuration
            opportunities: Opportunities to include

        Returns:
            Payload dictionary
        """
        # Build opportunities list
        opps_data = []
        for opp in opportunities:
            opp_dict = {
                "product_name": opp.opportunity.product_name,
                "product_sku": opp.opportunity.product_sku,
                "brand": opp.opportunity.brand_name,
                "buy_price": float(opp.opportunity.buy_price),
                "sell_price": float(opp.opportunity.sell_price),
                "gross_profit": float(opp.opportunity.gross_profit),
                "profit_margin": float(opp.opportunity.profit_margin),
                "roi": float(opp.opportunity.roi),
                "buy_source": opp.opportunity.buy_source,
                "buy_supplier": opp.opportunity.buy_supplier,
                "buy_url": opp.opportunity.buy_url,
                "stock_qty": opp.opportunity.buy_stock_qty,
                "feasibility_score": opp.feasibility_score,
                "demand_score": opp.demand_score,
                "risk_level": opp.risk_level_str,
                "estimated_days_to_sell": opp.estimated_days_to_sell,
            }

            # Include demand breakdown if requested
            if alert.include_demand_breakdown:
                opp_dict["demand_breakdown"] = opp.demand_breakdown

            # Include risk details if requested
            if alert.include_risk_details and opp.risk_assessment:
                opp_dict["risk_details"] = {
                    "risk_score": opp.risk_assessment.risk_score,
                    "confidence": opp.risk_assessment.confidence_score,
                    "factors": opp.risk_assessment.risk_factors,
                    "recommendations": opp.risk_assessment.recommendations,
                }

            opps_data.append(opp_dict)

        # Build complete payload
        payload = {
            "alert": {
                "id": str(alert.id),
                "name": alert.alert_name,
                "user_id": str(alert.user_id),
            },
            "notification_config": alert.notification_config or {},
            "opportunities": opps_data,
            "summary": {
                "total_opportunities": len(opportunities),
                "avg_profit_margin": sum(o.opportunity.profit_margin for o in opportunities)
                / len(opportunities),
                "avg_feasibility": sum(o.feasibility_score for o in opportunities)
                / len(opportunities),
                "total_potential_profit": sum(o.opportunity.gross_profit for o in opportunities),
            },
            "timestamp": datetime.now().isoformat(),
        }

        return payload

    # =====================================================
    # STATISTICS & MONITORING
    # =====================================================

    async def get_alert_statistics(self, alert_id: UUID) -> Optional[Dict]:
        """
        Get statistics for an alert.

        Args:
            alert_id: Alert ID

        Returns:
            Statistics dictionary or None if not found
        """
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        return {
            "alert_id": str(alert.id),
            "alert_name": alert.alert_name,
            "active": alert.active,
            "total_alerts_sent": alert.total_alerts_sent,
            "total_opportunities_sent": alert.total_opportunities_sent,
            "last_triggered_at": alert.last_triggered_at.isoformat()
            if alert.last_triggered_at
            else None,
            "last_scanned_at": alert.last_scanned_at.isoformat()
            if alert.last_scanned_at
            else None,
            "last_error": alert.last_error,
            "last_error_at": alert.last_error_at.isoformat() if alert.last_error_at else None,
            "avg_opportunities_per_alert": (
                alert.total_opportunities_sent / alert.total_alerts_sent
                if alert.total_alerts_sent > 0
                else 0
            ),
        }
