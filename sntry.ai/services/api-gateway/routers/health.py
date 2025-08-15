"""
Health check router for the API Gateway.
This endpoint does not require authentication as per security best practices.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime
import time

from shared.config import get_settings

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float


# Track startup time for uptime calculation
startup_time = time.time()


@router.get("/", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint - does not require authentication"""
    current_time = time.time()
    uptime = current_time - startup_time
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.api_version,
        uptime_seconds=uptime
    )


@router.get("/ready", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness check endpoint - indicates if service is ready to accept traffic"""
    current_time = time.time()
    uptime = current_time - startup_time
    
    # In a real implementation, you would check dependencies like database, Redis, etc.
    # For now, we'll assume ready if we've been up for more than 5 seconds
    is_ready = uptime > 5.0
    
    return HealthResponse(
        status="ready" if is_ready else "not_ready",
        timestamp=datetime.utcnow(),
        version=settings.api_version,
        uptime_seconds=uptime
    )


@router.get("/live", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness check endpoint - indicates if service is alive"""
    current_time = time.time()
    uptime = current_time - startup_time
    
    return HealthResponse(
        status="alive",
        timestamp=datetime.utcnow(),
        version=settings.api_version,
        uptime_seconds=uptime
    )