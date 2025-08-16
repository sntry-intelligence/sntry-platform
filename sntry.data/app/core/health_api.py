"""
Health check API endpoints
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.health import health_checker, HealthCheckResult
from config.logging import get_api_logger

logger = get_api_logger()
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="Overall health status")
async def health_check(
    force_refresh: bool = Query(False, description="Force refresh of health checks")
) -> Dict[str, Any]:
    """
    Get overall application health status.
    
    Returns cached results by default (30s cache), use force_refresh=true to get fresh results.
    """
    try:
        # Try to get cached results first
        if not force_refresh:
            cached_results = await health_checker.get_cached_results()
            if cached_results:
                return cached_results
        
        # Run fresh health checks
        results = await health_checker.run_all_checks()
        
        # Log health check results
        logger.info(
            f"Health check completed: {results['status']}",
            extra={
                "extra_fields": {
                    "overall_status": results["status"],
                    "total_duration_ms": results["total_duration_ms"],
                    "summary": results["summary"],
                    "event_type": "health_check_complete"
                }
            }
        )
        
        # Return appropriate HTTP status
        if results["status"] == "unhealthy":
            return JSONResponse(
                status_code=503,
                content=results
            )
        elif results["status"] == "degraded":
            return JSONResponse(
                status_code=200,
                content=results
            )
        else:
            return results
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "message": f"Health check system error: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/live", summary="Liveness probe")
async def liveness_check() -> Dict[str, str]:
    """
    Simple liveness check for container orchestration.
    Returns 200 if the application is running.
    """
    return {"status": "alive", "message": "Application is running"}


@router.get("/ready", summary="Readiness probe")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for container orchestration.
    Returns 200 if the application is ready to serve traffic.
    """
    try:
        # Check critical dependencies only
        db_check = await health_checker.check_database()
        redis_check = await health_checker.check_redis()
        
        if db_check.status == "healthy" and redis_check.status == "healthy":
            return {
                "status": "ready",
                "message": "Application is ready to serve traffic",
                "checks": {
                    "database": db_check.to_dict(),
                    "redis": redis_check.to_dict()
                }
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "message": "Application is not ready to serve traffic",
                    "checks": {
                        "database": db_check.to_dict(),
                        "redis": redis_check.to_dict()
                    }
                }
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "message": f"Readiness check error: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/database", summary="Database health check")
async def database_health() -> Dict[str, Any]:
    """Check database connectivity and PostGIS extension."""
    try:
        result = await health_checker.check_database()
        
        if result.status == "healthy":
            return result.to_dict()
        else:
            return JSONResponse(
                status_code=503,
                content=result.to_dict()
            )
            
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "name": "database",
                "status": "unhealthy",
                "message": f"Database health check error: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/redis", summary="Redis health check")
async def redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and basic operations."""
    try:
        result = await health_checker.check_redis()
        
        if result.status == "healthy":
            return result.to_dict()
        else:
            return JSONResponse(
                status_code=503,
                content=result.to_dict()
            )
            
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "name": "redis",
                "status": "unhealthy",
                "message": f"Redis health check error: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/workers", summary="Celery workers health check")
async def workers_health() -> Dict[str, Any]:
    """Check Celery worker availability."""
    try:
        result = await health_checker.check_celery_workers()
        
        if result.status == "healthy":
            return result.to_dict()
        else:
            return JSONResponse(
                status_code=503,
                content=result.to_dict()
            )
            
    except Exception as e:
        logger.error(f"Workers health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "name": "celery_workers",
                "status": "unhealthy",
                "message": f"Workers health check error: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/external-apis", summary="External APIs health check")
async def external_apis_health() -> Dict[str, Any]:
    """Check external API dependencies."""
    try:
        google_check = await health_checker.check_google_geocoding_api()
        
        return {
            "status": google_check.status,
            "message": "External APIs health check completed",
            "checks": {
                "google_geocoding_api": google_check.to_dict()
            }
        }
        
    except Exception as e:
        logger.error(f"External APIs health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "message": f"External APIs health check error: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/system", summary="System resources health check")
async def system_health() -> Dict[str, Any]:
    """Check system resources like disk space."""
    try:
        disk_check = await health_checker.check_disk_space()
        
        return {
            "status": disk_check.status,
            "message": "System resources health check completed",
            "checks": {
                "disk_space": disk_check.to_dict()
            }
        }
        
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "message": f"System health check error: {str(e)}",
                "error": str(e)
            }
        )