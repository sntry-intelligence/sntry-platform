"""
Monitoring and alerting API endpoints
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

from app.core.alerting import alert_manager, AlertType, AlertSeverity
from app.core.performance import performance_monitor
from config.logging import get_api_logger

logger = get_api_logger()
router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/alerts", summary="Get recent alerts")
async def get_alerts(
    hours: int = Query(24, description="Hours to look back for alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity")
) -> Dict[str, Any]:
    """Get recent alerts with optional filtering."""
    try:
        # Convert string parameters to enums if provided
        alert_type_enum = None
        if alert_type:
            try:
                alert_type_enum = AlertType(alert_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        # Get alerts
        alerts = await alert_manager.get_recent_alerts(hours=hours, alert_type=alert_type_enum)
        
        # Filter by severity if provided
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
                alerts = [a for a in alerts if a.get("severity") == severity]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "time_range_hours": hours,
            "filters": {
                "alert_type": alert_type,
                "severity": severity
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/stats", summary="Get alert statistics")
async def get_alert_stats(
    days: int = Query(7, description="Number of days to include in statistics")
) -> Dict[str, Any]:
    """Get alert statistics for the specified time period."""
    try:
        stats = await alert_manager.get_alert_stats(days=days)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting alert stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{metric_name}", summary="Get performance metrics")
async def get_metrics(
    metric_name: str,
    hours: int = Query(24, description="Hours to look back for metrics")
) -> Dict[str, Any]:
    """Get performance metrics for a specific metric name."""
    try:
        metrics = await performance_monitor.get_metrics(metric_name, hours=hours)
        
        return {
            "metric_name": metric_name,
            "time_range_hours": hours,
            "count": len(metrics),
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", summary="Get performance summary")
async def get_performance_summary(
    hours: int = Query(24, description="Hours to include in summary")
) -> Dict[str, Any]:
    """Get performance metrics summary."""
    try:
        summary = await performance_monitor.get_performance_summary(hours=hours)
        return summary
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", summary="Get monitoring dashboard data")
async def get_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive monitoring dashboard data."""
    try:
        # Get recent alerts (last 24 hours)
        recent_alerts = await alert_manager.get_recent_alerts(hours=24)
        
        # Get alert stats (last 7 days)
        alert_stats = await alert_manager.get_alert_stats(days=7)
        
        # Get performance summary (last 24 hours)
        performance_summary = await performance_monitor.get_performance_summary(hours=24)
        
        # Count alerts by severity
        alert_counts = {
            "critical": len([a for a in recent_alerts if a.get("severity") == "critical"]),
            "high": len([a for a in recent_alerts if a.get("severity") == "high"]),
            "medium": len([a for a in recent_alerts if a.get("severity") == "medium"]),
            "low": len([a for a in recent_alerts if a.get("severity") == "low"])
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": {
                "recent_count": len(recent_alerts),
                "by_severity": alert_counts,
                "recent_alerts": recent_alerts[:10],  # Last 10 alerts
                "stats": alert_stats
            },
            "performance": performance_summary,
            "system_status": {
                "healthy": alert_counts["critical"] == 0 and alert_counts["high"] == 0,
                "degraded": alert_counts["critical"] == 0 and alert_counts["high"] > 0,
                "unhealthy": alert_counts["critical"] > 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-alert", summary="Create test alert")
async def create_test_alert(
    alert_type: str = Query("system_error", description="Type of test alert"),
    severity: str = Query("medium", description="Severity of test alert")
) -> Dict[str, Any]:
    """Create a test alert for testing the alerting system."""
    try:
        # Convert string parameters to enums
        try:
            alert_type_enum = AlertType(alert_type)
            severity_enum = AlertSeverity(severity)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
        
        # Create test alert
        alert = await alert_manager.create_alert(
            alert_type=alert_type_enum,
            severity=severity_enum,
            title="Test Alert",
            message="This is a test alert created via the monitoring API",
            details={
                "test": True,
                "created_via": "monitoring_api",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        if alert:
            return {
                "success": True,
                "message": "Test alert created successfully",
                "alert": alert.to_dict()
            }
        else:
            return {
                "success": False,
                "message": "Test alert was rate limited or failed to create"
            }
        
    except Exception as e:
        logger.error(f"Error creating test alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alert-types", summary="Get available alert types")
async def get_alert_types() -> Dict[str, List[str]]:
    """Get list of available alert types and severities."""
    return {
        "alert_types": [t.value for t in AlertType],
        "severities": [s.value for s in AlertSeverity]
    }