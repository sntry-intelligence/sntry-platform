"""
Alerting system for critical errors and system events
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.redis import get_redis_client
from config.logging import get_logger

logger = get_logger("app.alerting")


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    SCRAPING_FAILURE = "scraping_failure"
    GEOCODING_QUOTA_EXCEEDED = "geocoding_quota_exceeded"
    DATABASE_ERROR = "database_error"
    API_ERROR = "api_error"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    COST_THRESHOLD_EXCEEDED = "cost_threshold_exceeded"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        data['type'] = self.type.value
        data['severity'] = self.severity.value
        return data


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.redis_client = None
        self.alert_key_prefix = "alerts:"
        self.alert_stats_key = "alert_stats"
        self.rate_limit_key_prefix = "alert_rate_limit:"
        
        # Rate limiting configuration (alerts per hour)
        self.rate_limits = {
            AlertType.SCRAPING_FAILURE: 5,
            AlertType.GEOCODING_QUOTA_EXCEEDED: 3,
            AlertType.DATABASE_ERROR: 10,
            AlertType.API_ERROR: 20,
            AlertType.SYSTEM_ERROR: 10,
            AlertType.PERFORMANCE_DEGRADATION: 5,
            AlertType.HEALTH_CHECK_FAILURE: 3,
            AlertType.COST_THRESHOLD_EXCEEDED: 2
        }
    
    async def _get_redis(self):
        """Get Redis client"""
        if not self.redis_client:
            self.redis_client = get_redis_client()
        return self.redis_client
    
    async def _check_rate_limit(self, alert_type: AlertType) -> bool:
        """Check if alert type is rate limited"""
        try:
            redis = await self._get_redis()
            rate_limit_key = f"{self.rate_limit_key_prefix}{alert_type.value}"
            
            current_count = await redis.get(rate_limit_key)
            current_count = int(current_count) if current_count else 0
            
            limit = self.rate_limits.get(alert_type, 10)
            
            if current_count >= limit:
                logger.warning(f"Alert rate limit exceeded for {alert_type.value}: {current_count}/{limit}")
                return False
            
            # Increment counter with 1-hour expiry
            await redis.incr(rate_limit_key)
            await redis.expire(rate_limit_key, 3600)
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True  # Allow alert if rate limit check fails
    
    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        details: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> Optional[Alert]:
        """Create and store a new alert"""
        
        # Check rate limiting
        if not await self._check_rate_limit(alert_type):
            return None
        
        # Create alert
        alert_id = f"{alert_type.value}_{int(datetime.utcnow().timestamp())}"
        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            details=details or {},
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id
        )
        
        try:
            # Store alert in Redis
            redis = await self._get_redis()
            alert_key = f"{self.alert_key_prefix}{alert_id}"
            await redis.setex(alert_key, 86400 * 7, json.dumps(alert.to_dict()))  # Keep for 7 days
            
            # Update alert statistics
            await self._update_alert_stats(alert_type, severity)
            
            # Log the alert
            logger.warning(
                f"Alert created: {title}",
                extra={
                    "extra_fields": {
                        "alert_id": alert_id,
                        "alert_type": alert_type.value,
                        "severity": severity.value,
                        "title": title,
                        "message": message,
                        "details": details,
                        "correlation_id": correlation_id,
                        "event_type": "alert_created"
                    }
                }
            )
            
            # Send notifications for high/critical alerts
            if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                await self._send_notifications(alert)
            
            return alert
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}", exc_info=True)
            return None
    
    async def _update_alert_stats(self, alert_type: AlertType, severity: AlertSeverity):
        """Update alert statistics"""
        try:
            redis = await self._get_redis()
            
            # Update daily stats
            today = datetime.utcnow().strftime("%Y-%m-%d")
            stats_key = f"{self.alert_stats_key}:{today}"
            
            await redis.hincrby(stats_key, f"total", 1)
            await redis.hincrby(stats_key, f"type:{alert_type.value}", 1)
            await redis.hincrby(stats_key, f"severity:{severity.value}", 1)
            await redis.expire(stats_key, 86400 * 30)  # Keep for 30 days
            
        except Exception as e:
            logger.error(f"Error updating alert stats: {str(e)}")
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for critical alerts"""
        try:
            # Send email notification if configured
            if settings.SMTP_HOST and settings.ALERT_EMAIL_RECIPIENTS:
                await self._send_email_notification(alert)
            
            # Add webhook notifications here if needed
            # await self._send_webhook_notification(alert)
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
    
    async def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        try:
            # Create email content
            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            
            body = f"""
Alert Details:
- Type: {alert.type.value}
- Severity: {alert.severity.value}
- Time: {alert.timestamp.isoformat()}
- Correlation ID: {alert.correlation_id or 'N/A'}

Message:
{alert.message}

Details:
{json.dumps(alert.details, indent=2)}

---
Jamaica Business Directory Monitoring System
            """.strip()
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = ', '.join(settings.ALERT_EMAIL_RECIPIENTS)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
    
    async def get_recent_alerts(self, hours: int = 24, alert_type: AlertType = None) -> List[Alert]:
        """Get recent alerts"""
        try:
            redis = await self._get_redis()
            
            # Get all alert keys
            pattern = f"{self.alert_key_prefix}*"
            if alert_type:
                pattern = f"{self.alert_key_prefix}{alert_type.value}_*"
            
            keys = await redis.keys(pattern)
            
            alerts = []
            for key in keys:
                alert_data = await redis.get(key)
                if alert_data:
                    alert_dict = json.loads(alert_data)
                    alert_time = datetime.fromisoformat(alert_dict['timestamp'])
                    
                    # Filter by time
                    if datetime.utcnow() - alert_time <= timedelta(hours=hours):
                        alerts.append(alert_dict)
            
            # Sort by timestamp (newest first)
            alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {str(e)}")
            return []
    
    async def get_alert_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            redis = await self._get_redis()
            
            stats = {
                "total_alerts": 0,
                "by_type": {},
                "by_severity": {},
                "by_day": {}
            }
            
            # Get stats for each day
            for i in range(days):
                date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                stats_key = f"{self.alert_stats_key}:{date}"
                
                day_stats = await redis.hgetall(stats_key)
                if day_stats:
                    day_total = int(day_stats.get(b'total', 0))
                    stats["total_alerts"] += day_total
                    stats["by_day"][date] = day_total
                    
                    # Aggregate by type and severity
                    for key, value in day_stats.items():
                        key_str = key.decode()
                        value_int = int(value)
                        
                        if key_str.startswith("type:"):
                            alert_type = key_str[5:]
                            stats["by_type"][alert_type] = stats["by_type"].get(alert_type, 0) + value_int
                        elif key_str.startswith("severity:"):
                            severity = key_str[9:]
                            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + value_int
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting alert stats: {str(e)}")
            return {"error": str(e)}


# Global alert manager instance
alert_manager = AlertManager()


# Convenience functions for creating specific alerts
async def alert_scraping_failure(scraper_name: str, error: str, correlation_id: str = None):
    """Create scraping failure alert"""
    await alert_manager.create_alert(
        alert_type=AlertType.SCRAPING_FAILURE,
        severity=AlertSeverity.HIGH,
        title=f"Scraping failure: {scraper_name}",
        message=f"Scraper {scraper_name} failed with error: {error}",
        details={"scraper_name": scraper_name, "error": error},
        correlation_id=correlation_id
    )


async def alert_geocoding_quota_exceeded(current_usage: int, quota_limit: int, correlation_id: str = None):
    """Create geocoding quota exceeded alert"""
    await alert_manager.create_alert(
        alert_type=AlertType.GEOCODING_QUOTA_EXCEEDED,
        severity=AlertSeverity.CRITICAL,
        title="Geocoding API quota exceeded",
        message=f"Geocoding quota exceeded: {current_usage}/{quota_limit}",
        details={"current_usage": current_usage, "quota_limit": quota_limit},
        correlation_id=correlation_id
    )


async def alert_database_error(error: str, correlation_id: str = None):
    """Create database error alert"""
    await alert_manager.create_alert(
        alert_type=AlertType.DATABASE_ERROR,
        severity=AlertSeverity.HIGH,
        title="Database error",
        message=f"Database operation failed: {error}",
        details={"error": error},
        correlation_id=correlation_id
    )


async def alert_cost_threshold_exceeded(service: str, current_cost: float, threshold: float, correlation_id: str = None):
    """Create cost threshold exceeded alert"""
    await alert_manager.create_alert(
        alert_type=AlertType.COST_THRESHOLD_EXCEEDED,
        severity=AlertSeverity.HIGH,
        title=f"Cost threshold exceeded: {service}",
        message=f"{service} cost ${current_cost:.2f} exceeded threshold ${threshold:.2f}",
        details={"service": service, "current_cost": current_cost, "threshold": threshold},
        correlation_id=correlation_id
    )