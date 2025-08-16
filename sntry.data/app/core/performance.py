"""
Performance monitoring and metrics collection
"""
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from contextlib import asynccontextmanager
import psutil
import json

from app.core.redis import get_redis_client
from app.core.alerting import alert_manager, AlertType, AlertSeverity
from config.logging import get_logger

logger = get_logger("app.performance")


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags or {}
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.redis_client = None
        self.metrics_key_prefix = "metrics:"
        self.thresholds = {
            "response_time_ms": 2000,  # 2 seconds
            "cpu_usage_percent": 80,
            "memory_usage_percent": 85,
            "disk_usage_percent": 90,
            "database_query_time_ms": 1000,  # 1 second
            "geocoding_request_time_ms": 5000,  # 5 seconds
            "scraping_page_time_ms": 30000,  # 30 seconds
        }
    
    async def _get_redis(self):
        """Get Redis client"""
        if not self.redis_client:
            self.redis_client = get_redis_client()
        return self.redis_client
    
    async def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        try:
            redis = await self._get_redis()
            
            # Store metric with timestamp-based key
            timestamp_key = int(metric.timestamp.timestamp())
            metric_key = f"{self.metrics_key_prefix}{metric.name}:{timestamp_key}"
            
            await redis.setex(metric_key, 86400 * 7, json.dumps(metric.to_dict()))  # Keep for 7 days
            
            # Check thresholds and create alerts if needed
            await self._check_thresholds(metric)
            
            # Log metric
            logger.debug(
                f"Performance metric recorded: {metric.name}",
                extra={
                    "extra_fields": {
                        "metric_name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "tags": metric.tags,
                        "event_type": "performance_metric"
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error recording metric: {str(e)}")
    
    async def _check_thresholds(self, metric: PerformanceMetric):
        """Check if metric exceeds thresholds and create alerts"""
        threshold = self.thresholds.get(metric.name)
        if threshold and metric.value > threshold:
            await alert_manager.create_alert(
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.MEDIUM,
                title=f"Performance threshold exceeded: {metric.name}",
                message=f"{metric.name} value {metric.value} {metric.unit} exceeded threshold {threshold} {metric.unit}",
                details={
                    "metric_name": metric.name,
                    "value": metric.value,
                    "threshold": threshold,
                    "unit": metric.unit,
                    "tags": metric.tags
                }
            )
    
    async def record_response_time(self, endpoint: str, method: str, duration_ms: float, status_code: int):
        """Record API response time"""
        metric = PerformanceMetric(
            name="response_time_ms",
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            tags={
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code)
            }
        )
        await self.record_metric(metric)
    
    async def record_database_query_time(self, query_type: str, duration_ms: float, table: str = None):
        """Record database query time"""
        metric = PerformanceMetric(
            name="database_query_time_ms",
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            tags={
                "query_type": query_type,
                "table": table or "unknown"
            }
        )
        await self.record_metric(metric)
    
    async def record_geocoding_request_time(self, duration_ms: float, status: str, from_cache: bool = False):
        """Record geocoding request time"""
        metric = PerformanceMetric(
            name="geocoding_request_time_ms",
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            tags={
                "status": status,
                "from_cache": str(from_cache)
            }
        )
        await self.record_metric(metric)
    
    async def record_scraping_page_time(self, scraper_name: str, duration_ms: float, success: bool):
        """Record scraping page time"""
        metric = PerformanceMetric(
            name="scraping_page_time_ms",
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            tags={
                "scraper_name": scraper_name,
                "success": str(success)
            }
        )
        await self.record_metric(metric)
    
    async def record_system_metrics(self):
        """Record system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric(PerformanceMetric(
                name="cpu_usage_percent",
                value=cpu_percent,
                unit="percent",
                timestamp=datetime.utcnow()
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            await self.record_metric(PerformanceMetric(
                name="memory_usage_percent",
                value=memory.percent,
                unit="percent",
                timestamp=datetime.utcnow()
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            await self.record_metric(PerformanceMetric(
                name="disk_usage_percent",
                value=disk_percent,
                unit="percent",
                timestamp=datetime.utcnow()
            ))
            
            # Network I/O
            network = psutil.net_io_counters()
            await self.record_metric(PerformanceMetric(
                name="network_bytes_sent",
                value=network.bytes_sent,
                unit="bytes",
                timestamp=datetime.utcnow()
            ))
            await self.record_metric(PerformanceMetric(
                name="network_bytes_received",
                value=network.bytes_recv,
                unit="bytes",
                timestamp=datetime.utcnow()
            ))
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {str(e)}")
    
    async def get_metrics(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a specific time period"""
        try:
            redis = await self._get_redis()
            
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get all keys for the metric
            pattern = f"{self.metrics_key_prefix}{metric_name}:*"
            keys = await redis.keys(pattern)
            
            metrics = []
            for key in keys:
                # Extract timestamp from key
                timestamp_str = key.decode().split(':')[-1]
                timestamp = datetime.fromtimestamp(int(timestamp_str))
                
                # Filter by time range
                if start_time <= timestamp <= end_time:
                    metric_data = await redis.get(key)
                    if metric_data:
                        metrics.append(json.loads(metric_data))
            
            # Sort by timestamp
            metrics.sort(key=lambda x: x['timestamp'])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return []
    
    async def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for dashboard"""
        try:
            summary = {
                "time_range_hours": hours,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {}
            }
            
            # Get metrics for each type
            for metric_name in ["response_time_ms", "cpu_usage_percent", "memory_usage_percent", "disk_usage_percent"]:
                metrics = await self.get_metrics(metric_name, hours)
                
                if metrics:
                    values = [m["value"] for m in metrics]
                    summary["metrics"][metric_name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "latest": values[-1] if values else None
                    }
                else:
                    summary["metrics"][metric_name] = {
                        "count": 0,
                        "min": None,
                        "max": None,
                        "avg": None,
                        "latest": None
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {"error": str(e)}


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


@asynccontextmanager
async def measure_time(operation_name: str, tags: Dict[str, str] = None):
    """Context manager to measure operation time"""
    start_time = time.time()
    
    try:
        yield
        
        # Record successful operation
        duration_ms = (time.time() - start_time) * 1000
        metric = PerformanceMetric(
            name=f"{operation_name}_time_ms",
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            tags={**(tags or {}), "success": "true"}
        )
        await performance_monitor.record_metric(metric)
        
    except Exception as e:
        # Record failed operation
        duration_ms = (time.time() - start_time) * 1000
        metric = PerformanceMetric(
            name=f"{operation_name}_time_ms",
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            tags={**(tags or {}), "success": "false", "error": str(e)}
        )
        await performance_monitor.record_metric(metric)
        raise


async def start_system_monitoring():
    """Start background system monitoring"""
    while True:
        try:
            await performance_monitor.record_system_metrics()
            await asyncio.sleep(60)  # Record every minute
        except Exception as e:
            logger.error(f"Error in system monitoring: {str(e)}")
            await asyncio.sleep(60)