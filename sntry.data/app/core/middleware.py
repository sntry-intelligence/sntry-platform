"""
Middleware for logging, correlation IDs, and monitoring
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from config.logging import set_correlation_id, get_api_logger

logger = get_api_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation IDs"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "correlation_id": correlation_id,
                    "event_type": "request_start"
                }
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration * 1000, 2),
                        "correlation_id": correlation_id,
                        "event_type": "request_complete"
                    }
                }
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "correlation_id": correlation_id,
                        "event_type": "request_error"
                    }
                },
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id
                },
                headers={"X-Correlation-ID": correlation_id}
            )


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for performance monitoring and metrics"""
    
    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                "Slow request detected",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "threshold_ms": self.slow_request_threshold * 1000,
                        "event_type": "slow_request"
                    }
                }
            )
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response