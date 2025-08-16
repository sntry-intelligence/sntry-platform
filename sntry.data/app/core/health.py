"""
Health check service for monitoring system components
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import redis
import psycopg2
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.config import settings
from config.logging import get_logger

logger = get_logger("app.health")


class HealthCheckResult:
    """Result of a health check"""
    
    def __init__(self, name: str, status: str, message: str = "", details: Dict[str, Any] = None, duration_ms: float = 0):
        self.name = name
        self.status = status  # "healthy", "unhealthy", "degraded"
        self.message = message
        self.details = details or {}
        self.duration_ms = duration_ms
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp
        }


class HealthChecker:
    """Health check service for system components"""
    
    def __init__(self):
        self.checks = {}
        self.last_check_time = None
        self.cache_duration = 30  # Cache results for 30 seconds
    
    async def check_database(self) -> HealthCheckResult:
        """Check PostgreSQL database connectivity and PostGIS extension"""
        start_time = time.time()
        
        try:
            # Test basic database connectivity
            async for db in get_db():
                # Test basic query
                result = await db.execute(text("SELECT 1"))
                basic_check = result.scalar()
                
                # Test PostGIS extension
                postgis_result = await db.execute(text("SELECT PostGIS_Version()"))
                postgis_version = postgis_result.scalar()
                
                # Test spatial query
                spatial_result = await db.execute(text("""
                    SELECT ST_AsText(ST_Point(-76.8, 18.0))
                """))
                spatial_test = spatial_result.scalar()
                
                duration = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    name="database",
                    status="healthy",
                    message="Database and PostGIS are operational",
                    details={
                        "postgis_version": postgis_version,
                        "spatial_test": spatial_test,
                        "basic_connectivity": basic_check == 1
                    },
                    duration_ms=duration
                )
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {str(e)}")
            
            return HealthCheckResult(
                name="database",
                status="unhealthy",
                message=f"Database check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            )
    
    async def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity and basic operations"""
        start_time = time.time()
        
        try:
            redis_client = get_redis_client()
            
            # Test basic connectivity
            await redis_client.ping()
            
            # Test set/get operations
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            await redis_client.set(test_key, test_value, ex=60)
            retrieved_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            # Get Redis info
            info = await redis_client.info()
            
            duration = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="redis",
                status="healthy",
                message="Redis is operational",
                details={
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "test_operation": retrieved_value.decode() == test_value if retrieved_value else False
                },
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Redis health check failed: {str(e)}")
            
            return HealthCheckResult(
                name="redis",
                status="unhealthy",
                message=f"Redis check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            )
    
    async def check_celery_workers(self) -> HealthCheckResult:
        """Check Celery worker availability"""
        start_time = time.time()
        
        try:
            from app.core.celery_app import celery_app
            
            # Get active workers
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            stats = inspect.stats()
            
            duration = (time.time() - start_time) * 1000
            
            if active_workers:
                worker_count = len(active_workers)
                return HealthCheckResult(
                    name="celery_workers",
                    status="healthy",
                    message=f"{worker_count} Celery workers active",
                    details={
                        "active_workers": list(active_workers.keys()),
                        "worker_count": worker_count,
                        "stats": stats
                    },
                    duration_ms=duration
                )
            else:
                return HealthCheckResult(
                    name="celery_workers",
                    status="unhealthy",
                    message="No active Celery workers found",
                    details={"active_workers": [], "worker_count": 0},
                    duration_ms=duration
                )
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Celery health check failed: {str(e)}")
            
            return HealthCheckResult(
                name="celery_workers",
                status="degraded",
                message=f"Celery check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            )
    
    async def check_google_geocoding_api(self) -> HealthCheckResult:
        """Check Google Geocoding API availability"""
        start_time = time.time()
        
        try:
            # Test with a simple Jamaica address
            test_address = "Kingston, Jamaica"
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": test_address,
                "key": settings.GOOGLE_MAPS_API_KEY
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                data = response.json()
            
            duration = (time.time() - start_time) * 1000
            
            if data.get("status") == "OK":
                return HealthCheckResult(
                    name="google_geocoding_api",
                    status="healthy",
                    message="Google Geocoding API is operational",
                    details={
                        "test_address": test_address,
                        "results_count": len(data.get("results", [])),
                        "api_status": data.get("status")
                    },
                    duration_ms=duration
                )
            elif data.get("status") == "OVER_QUERY_LIMIT":
                return HealthCheckResult(
                    name="google_geocoding_api",
                    status="degraded",
                    message="Google Geocoding API quota exceeded",
                    details={
                        "api_status": data.get("status"),
                        "error_message": data.get("error_message")
                    },
                    duration_ms=duration
                )
            else:
                return HealthCheckResult(
                    name="google_geocoding_api",
                    status="unhealthy",
                    message=f"Google Geocoding API error: {data.get('status')}",
                    details={
                        "api_status": data.get("status"),
                        "error_message": data.get("error_message")
                    },
                    duration_ms=duration
                )
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Google Geocoding API health check failed: {str(e)}")
            
            return HealthCheckResult(
                name="google_geocoding_api",
                status="unhealthy",
                message=f"Google Geocoding API check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            )
    
    async def check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        start_time = time.time()
        
        try:
            import shutil
            
            # Check disk space for logs directory
            logs_usage = shutil.disk_usage("logs")
            logs_free_gb = logs_usage.free / (1024**3)
            logs_total_gb = logs_usage.total / (1024**3)
            logs_used_percent = ((logs_usage.total - logs_usage.free) / logs_usage.total) * 100
            
            # Check disk space for current directory (app)
            app_usage = shutil.disk_usage(".")
            app_free_gb = app_usage.free / (1024**3)
            app_total_gb = app_usage.total / (1024**3)
            app_used_percent = ((app_usage.total - app_usage.free) / app_usage.total) * 100
            
            duration = (time.time() - start_time) * 1000
            
            # Determine status based on available space
            if logs_free_gb < 1.0 or app_free_gb < 1.0:  # Less than 1GB free
                status = "unhealthy"
                message = "Low disk space detected"
            elif logs_used_percent > 90 or app_used_percent > 90:  # More than 90% used
                status = "degraded"
                message = "Disk space usage high"
            else:
                status = "healthy"
                message = "Disk space is adequate"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "logs_directory": {
                        "free_gb": round(logs_free_gb, 2),
                        "total_gb": round(logs_total_gb, 2),
                        "used_percent": round(logs_used_percent, 2)
                    },
                    "app_directory": {
                        "free_gb": round(app_free_gb, 2),
                        "total_gb": round(app_total_gb, 2),
                        "used_percent": round(app_used_percent, 2)
                    }
                },
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Disk space health check failed: {str(e)}")
            
            return HealthCheckResult(
                name="disk_space",
                status="unhealthy",
                message=f"Disk space check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            )
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        start_time = time.time()
        
        # Run all checks concurrently
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_celery_workers(),
            self.check_google_geocoding_api(),
            self.check_disk_space(),
            return_exceptions=True
        )
        
        total_duration = (time.time() - start_time) * 1000
        
        # Process results
        results = {}
        overall_status = "healthy"
        unhealthy_count = 0
        degraded_count = 0
        
        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check exception: {str(check)}")
                continue
                
            results[check.name] = check.to_dict()
            
            if check.status == "unhealthy":
                unhealthy_count += 1
                overall_status = "unhealthy"
            elif check.status == "degraded" and overall_status != "unhealthy":
                degraded_count += 1
                overall_status = "degraded"
        
        # Cache the results
        self.checks = results
        self.last_check_time = datetime.utcnow()
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "total_duration_ms": round(total_duration, 2),
            "summary": {
                "total_checks": len(results),
                "healthy": len([r for r in results.values() if r["status"] == "healthy"]),
                "degraded": degraded_count,
                "unhealthy": unhealthy_count
            },
            "checks": results
        }
    
    async def get_cached_results(self) -> Optional[Dict[str, Any]]:
        """Get cached health check results if still valid"""
        if (self.last_check_time and 
            datetime.utcnow() - self.last_check_time < timedelta(seconds=self.cache_duration)):
            return {
                "status": "healthy" if all(c["status"] == "healthy" for c in self.checks.values()) else "degraded",
                "timestamp": self.last_check_time.isoformat(),
                "cached": True,
                "checks": self.checks
            }
        return None


# Global health checker instance
health_checker = HealthChecker()