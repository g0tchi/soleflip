"""
ArbitrageAlert Model - User-configurable arbitrage opportunity alerts

Stores alert configurations for users to receive notifications when
new arbitrage opportunities matching their criteria are detected.
"""

import uuid
from datetime import datetime, time
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from shared.database.models import Base, TimestampMixin
from shared.database.utils import IS_POSTGRES, get_schema_ref


class RiskLevelFilter(str, Enum):
    """Risk level filter for alerts"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ArbitrageAlert(Base, TimestampMixin):
    """
    Arbitrage Alert Configuration

    Users can create alerts to be notified when arbitrage opportunities
    matching their criteria are detected.

    Notification flow:
    1. Background job scans for opportunities (every 15 min by default)
    2. Matches opportunities against active alert criteria
    3. Sends notification via n8n webhook
    4. n8n workflow routes to Discord/Email/Telegram based on config
    """

    __tablename__ = "arbitrage_alerts"
    __table_args__ = {"schema": "arbitrage"} if IS_POSTGRES else None

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User association
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(get_schema_ref("users.id", "auth")),
        nullable=False,
        index=True,
    )

    # Alert identification
    alert_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    active = Column(Boolean, nullable=False, default=True, index=True)

    # =====================================================
    # FILTER CRITERIA
    # =====================================================

    # Profit filters
    min_profit_margin = Column(
        Numeric(5, 2), nullable=False, default=10.0, comment="Minimum profit margin %"
    )
    min_gross_profit = Column(
        Numeric(8, 2), nullable=False, default=20.0, comment="Minimum gross profit €"
    )
    max_buy_price = Column(Numeric(8, 2), nullable=True, comment="Maximum buy price €")

    # Quality filters
    min_feasibility_score = Column(
        Integer, nullable=False, default=60, comment="Minimum feasibility score (0-100)"
    )
    max_risk_level = Column(
        SQLEnum(RiskLevelFilter),
        nullable=False,
        default=RiskLevelFilter.MEDIUM,
        comment="Maximum acceptable risk level",
    )

    # Source filter
    source_filter = Column(
        String(50), nullable=True, comment="Filter by source (awin, webgains, etc.)"
    )

    # Additional filters (JSONB for flexibility)
    additional_filters = Column(
        JSONB,
        nullable=True,
        comment="Additional filters (brand, category, supplier, etc.)",
    )

    # =====================================================
    # NOTIFICATION SETTINGS
    # =====================================================

    # n8n webhook URL for notifications
    n8n_webhook_url = Column(
        String(500), nullable=False, comment="n8n webhook endpoint for notifications"
    )

    # Notification channels configuration (for n8n routing)
    notification_config = Column(
        JSONB,
        nullable=True,
        comment="Notification preferences: {discord: true, email: false, telegram: false}",
    )

    # Alert content preferences
    include_demand_breakdown = Column(Boolean, nullable=False, default=True)
    include_risk_details = Column(Boolean, nullable=False, default=True)
    max_opportunities_per_alert = Column(Integer, nullable=False, default=10)

    # =====================================================
    # SCHEDULE SETTINGS
    # =====================================================

    # Frequency (minutes between checks)
    alert_frequency_minutes = Column(
        Integer, nullable=False, default=15, comment="Minutes between alert checks"
    )

    # Active hours (optional - if null, alerts run 24/7)
    active_hours_start = Column(
        Time, nullable=True, comment="Start of active hours (e.g., 09:00)"
    )
    active_hours_end = Column(
        Time, nullable=True, comment="End of active hours (e.g., 22:00)"
    )

    # Active days (JSONB array: ["monday", "tuesday", ...] or null for all days)
    active_days = Column(
        JSONB, nullable=True, comment="Active days: ['monday', 'tuesday', ...] or null for all"
    )

    # Timezone for schedule
    timezone = Column(String(50), nullable=False, default="Europe/Berlin")

    # =====================================================
    # ALERT TRACKING
    # =====================================================

    # Last triggered timestamp
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    # Last scan timestamp (even if no opportunities found)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    total_alerts_sent = Column(Integer, nullable=False, default=0)
    total_opportunities_sent = Column(
        Integer, nullable=False, default=0, comment="Total opportunities sent across all alerts"
    )

    # Last error (for debugging)
    last_error = Column(String(1000), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    user = relationship("User", foreign_keys=[user_id])

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def is_currently_active(self, check_time: datetime = None) -> bool:
        """
        Check if alert should be active at given time.

        Considers:
        - Alert active flag
        - Active hours (if configured)
        - Active days (if configured)

        Args:
            check_time: Datetime to check (defaults to now)

        Returns:
            True if alert should run at this time
        """
        if not self.active:
            return False

        if check_time is None:
            check_time = datetime.now()

        # Check active hours
        if self.active_hours_start and self.active_hours_end:
            current_time = check_time.time()
            if not (self.active_hours_start <= current_time <= self.active_hours_end):
                return False

        # Check active days
        if self.active_days:
            current_day = check_time.strftime("%A").lower()
            if current_day not in [day.lower() for day in self.active_days]:
                return False

        return True

    def should_trigger_now(self, current_time: datetime = None) -> bool:
        """
        Check if alert should trigger based on frequency and last trigger time.

        Args:
            current_time: Current datetime (defaults to now)

        Returns:
            True if enough time has passed since last trigger
        """
        if not self.is_currently_active(current_time):
            return False

        if current_time is None:
            current_time = datetime.now()

        # If never triggered, should trigger now
        if not self.last_scanned_at:
            return True

        # Check if enough time has passed
        time_since_last = (current_time - self.last_scanned_at).total_seconds() / 60
        return time_since_last >= self.alert_frequency_minutes

    def get_filter_dict(self) -> dict:
        """
        Get filter criteria as dictionary for service consumption.

        Returns:
            Dictionary with all filter parameters
        """
        return {
            "min_profit_margin": float(self.min_profit_margin),
            "min_gross_profit": float(self.min_gross_profit),
            "max_buy_price": float(self.max_buy_price) if self.max_buy_price else None,
            "min_feasibility": self.min_feasibility_score,
            "max_risk": self.max_risk_level.value,
            "source_filter": self.source_filter,
            "additional_filters": self.additional_filters or {},
        }

    def increment_alert_stats(self, opportunities_count: int):
        """
        Increment alert statistics after sending notification.

        Args:
            opportunities_count: Number of opportunities sent in alert
        """
        self.total_alerts_sent += 1
        self.total_opportunities_sent += opportunities_count
        self.last_triggered_at = datetime.now()

    def record_error(self, error_message: str):
        """
        Record alert error for debugging.

        Args:
            error_message: Error message to record
        """
        self.last_error = error_message[:1000]  # Truncate to field length
        self.last_error_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"<ArbitrageAlert(id={self.id}, name='{self.alert_name}', "
            f"user={self.user_id}, active={self.active})>"
        )
