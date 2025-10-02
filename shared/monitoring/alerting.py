"""
Enhanced Alerting System
Advanced alerting and notification system integrated with APM monitoring
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

import structlog
from shared.monitoring.apm import get_apm_collector

logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels"""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class AlertRule:
    """Configuration for alert rules"""
    name: str
    condition: Callable[[Dict], bool]
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 5
    description: str = ""
    enabled: bool = True


@dataclass
class Alert:
    """Alert instance"""
    rule_name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertManager:
    """Advanced alert management system"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.rule_cooldowns: Dict[str, datetime] = {}
        self.notification_handlers: Dict[AlertChannel, Callable] = {}
        
        # Setup default notification handlers
        self._setup_default_handlers()
        
        # Setup default alert rules
        self._setup_default_rules()
        
        logger.info("Alert Manager initialized")
    
    def _setup_default_handlers(self):
        """Setup default notification handlers"""
        self.notification_handlers[AlertChannel.LOG] = self._log_alert
    
    def _setup_default_rules(self):
        """Setup default alerting rules"""
        
        # High error rate alert
        self.add_rule(AlertRule(
            name="high_error_rate",
            condition=lambda metrics: metrics.get("requests", {}).get("error_rate", 0) > 10,
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG],
            cooldown_minutes=5,
            description="Error rate exceeded 10%"
        ))
        
        # Slow response time alert
        self.add_rule(AlertRule(
            name="slow_response_time",
            condition=lambda metrics: metrics.get("requests", {}).get("avg_response_time_ms", 0) > 2000,
            severity=AlertSeverity.MEDIUM,
            channels=[AlertChannel.LOG],
            cooldown_minutes=3,
            description="Average response time exceeded 2 seconds"
        ))
        
        # High CPU usage alert
        self.add_rule(AlertRule(
            name="high_cpu_usage",
            condition=lambda metrics: metrics.get("system", {}).get("avg_cpu_percent", 0) > 80,
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG],
            cooldown_minutes=2,
            description="CPU usage exceeded 80%"
        ))
        
        # High memory usage alert
        self.add_rule(AlertRule(
            name="high_memory_usage",
            condition=lambda metrics: metrics.get("system", {}).get("avg_memory_percent", 0) > 85,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.LOG],
            cooldown_minutes=2,
            description="Memory usage exceeded 85%"
        ))
        
        # Low health score alert
        self.add_rule(AlertRule(
            name="low_health_score",
            condition=lambda metrics: metrics.get("health_score", 100) < 70,
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.LOG],
            cooldown_minutes=5,
            description="System health score dropped below 70"
        ))
        
        # Database slow query alert
        self.add_rule(AlertRule(
            name="high_slow_query_rate",
            condition=lambda metrics: metrics.get("database", {}).get("slow_query_rate", 0) > 20,
            severity=AlertSeverity.MEDIUM,
            channels=[AlertChannel.LOG],
            cooldown_minutes=3,
            description="Slow query rate exceeded 20%"
        ))
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules[rule.name] = rule
        logger.info("Alert rule added", rule_name=rule.name, severity=rule.severity.value)
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info("Alert rule removed", rule_name=rule_name)
    
    def add_notification_handler(self, channel: AlertChannel, handler: Callable):
        """Add a custom notification handler"""
        self.notification_handlers[channel] = handler
        logger.info("Notification handler added", channel=channel.value)
    
    async def check_rules(self) -> List[Alert]:
        """Check all alert rules against current metrics"""
        apm_collector = get_apm_collector()
        
        # Get current performance summary
        metrics = apm_collector.get_performance_summary(minutes=5)
        
        triggered_alerts = []
        current_time = datetime.utcnow()
        
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown
            if rule_name in self.rule_cooldowns:
                cooldown_end = self.rule_cooldowns[rule_name] + timedelta(minutes=rule.cooldown_minutes)
                if current_time < cooldown_end:
                    continue
            
            # Check condition
            try:
                if rule.condition(metrics):
                    alert = Alert(
                        rule_name=rule_name,
                        severity=rule.severity,
                        message=rule.description,
                        details={
                            "metrics_snapshot": metrics,
                            "rule_name": rule_name,
                            "triggered_at": current_time.isoformat()
                        }
                    )
                    
                    triggered_alerts.append(alert)
                    self.active_alerts[rule_name] = alert
                    self.alert_history.append(alert)
                    self.rule_cooldowns[rule_name] = current_time
                    
                    # Send notifications
                    await self._send_notifications(alert, rule.channels)
                    
                    logger.warning(
                        "Alert triggered",
                        rule_name=rule_name,
                        severity=rule.severity.value,
                        message=rule.description
                    )
                
                elif rule_name in self.active_alerts:
                    # Rule condition no longer met - resolve alert
                    await self._resolve_alert(rule_name)
                    
            except Exception as e:
                logger.error(
                    "Error checking alert rule",
                    rule_name=rule_name,
                    error=str(e)
                )
        
        return triggered_alerts
    
    async def _resolve_alert(self, rule_name: str):
        """Resolve an active alert"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            del self.active_alerts[rule_name]
            
            logger.info(
                "Alert resolved",
                rule_name=rule_name,
                duration_minutes=round((alert.resolved_at - alert.timestamp).total_seconds() / 60, 2)
            )
    
    async def _send_notifications(self, alert: Alert, channels: List[AlertChannel]):
        """Send alert notifications to configured channels"""
        for channel in channels:
            if channel in self.notification_handlers:
                try:
                    await self.notification_handlers[channel](alert)
                except Exception as e:
                    logger.error(
                        "Failed to send alert notification",
                        channel=channel.value,
                        rule_name=alert.rule_name,
                        error=str(e)
                    )
    
    async def _log_alert(self, alert: Alert):
        """Default log notification handler"""
        logger.warning(
            "ALERT",
            rule_name=alert.rule_name,
            severity=alert.severity.value,
            message=alert.message,
            timestamp=alert.timestamp.isoformat()
        )
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp > cutoff_time]
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics"""
        recent_alerts = self.get_alert_history(hours)
        
        # Group by severity
        severity_counts = defaultdict(int)
        for alert in recent_alerts:
            severity_counts[alert.severity.value] += 1
        
        # Group by rule
        rule_counts = defaultdict(int)
        for alert in recent_alerts:
            rule_counts[alert.rule_name] += 1
        
        # Calculate resolution times
        resolved_alerts = [a for a in recent_alerts if a.resolved and a.resolved_at]
        avg_resolution_time = 0
        if resolved_alerts:
            total_resolution_time = sum(
                (alert.resolved_at - alert.timestamp).total_seconds()
                for alert in resolved_alerts
            )
            avg_resolution_time = total_resolution_time / len(resolved_alerts) / 60  # in minutes
        
        return {
            "total_alerts": len(recent_alerts),
            "active_alerts": len(self.active_alerts),
            "by_severity": dict(severity_counts),
            "by_rule": dict(rule_counts),
            "avg_resolution_time_minutes": round(avg_resolution_time, 2),
            "resolution_rate": round(len(resolved_alerts) / len(recent_alerts) * 100, 2) if recent_alerts else 0
        }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


async def start_alert_monitoring(check_interval_seconds: int = 60):
    """Start continuous alert monitoring"""
    alert_manager = get_alert_manager()
    
    logger.info("Starting alert monitoring", interval_seconds=check_interval_seconds)
    
    while True:
        try:
            await alert_manager.check_rules()
            await asyncio.sleep(check_interval_seconds)
        except Exception as e:
            logger.error("Alert monitoring error", error=str(e))
            await asyncio.sleep(check_interval_seconds * 2)  # Wait longer on error