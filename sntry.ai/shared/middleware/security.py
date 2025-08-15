"""
Security middleware for HTTPS enforcement and security headers.
Implements requirements 7.3 for HTTPS enforcement and security headers.
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

from shared.config import get_settings
from shared.utils.logging import get_logger

logger = get_logger("security")
settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            
            # Strict Transport Security (HSTS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Permissions Policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            ),
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS connections"""
    
    def __init__(self, app, enforce_https: bool = None):
        super().__init__(app)
        self.enforce_https = enforce_https if enforce_https is not None else settings.enforce_https
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip HTTPS enforcement for health checks and local development
        if not self.enforce_https or request.url.hostname in ["localhost", "127.0.0.1"]:
            return await call_next(request)
        
        # Check if request is using HTTPS
        if request.url.scheme != "https":
            # Check for forwarded protocol headers (common in load balancers)
            forwarded_proto = request.headers.get("X-Forwarded-Proto")
            forwarded_scheme = request.headers.get("X-Forwarded-Scheme")
            
            if forwarded_proto != "https" and forwarded_scheme != "https":
                logger.warning(
                    "HTTP request blocked - HTTPS required",
                    url=str(request.url),
                    client_ip=request.client.host,
                    user_agent=request.headers.get("User-Agent", "unknown")
                )
                
                raise HTTPException(
                    status_code=status.HTTP_426_UPGRADE_REQUIRED,
                    detail="HTTPS required. Please use https:// instead of http://",
                    headers={"Upgrade": "TLS/1.2, HTTP/1.1"}
                )
        
        return await call_next(request)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and security checks"""
    
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    BLOCKED_USER_AGENTS = [
        "sqlmap",
        "nikto",
        "nmap",
        "masscan",
        "nessus",
        "openvas",
        "w3af",
        "skipfish"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
            logger.warning(
                "Request blocked - size too large",
                content_length=content_length,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request entity too large"
            )
        
        # Check User-Agent for known malicious patterns
        user_agent = request.headers.get("User-Agent", "").lower()
        for blocked_agent in self.BLOCKED_USER_AGENTS:
            if blocked_agent in user_agent:
                logger.warning(
                    "Request blocked - suspicious user agent",
                    user_agent=user_agent,
                    client_ip=request.client.host
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-host",
            "x-originating-ip",
            "x-remote-ip",
            "x-remote-addr"
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                # Basic validation - in production, implement more sophisticated checks
                if any(char in value for char in ["<", ">", "\"", "'"]):
                    logger.warning(
                        "Request blocked - suspicious header value",
                        header=header,
                        value=value,
                        client_ip=request.client.host
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid header value"
                    )
        
        return await call_next(request)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure correlation IDs are present in requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if correlation ID already exists (from upstream services)
        correlation_id = request.headers.get("X-Correlation-ID")
        
        if not correlation_id:
            # Use the request ID generated in the main middleware
            correlation_id = getattr(request.state, 'request_id', None)
        
        if correlation_id:
            # Store correlation ID in request state for logging
            request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        
        # Add correlation ID to response headers
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """Middleware for security event logging and audit trails"""
    
    SENSITIVE_PATHS = [
        "/v1/agents",
        "/v1/evaluations",
        "/v1/mcp-servers"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Check if this is a sensitive operation
        is_sensitive = any(request.url.path.startswith(path) for path in self.SENSITIVE_PATHS)
        
        if is_sensitive:
            # Log security-relevant request details for security audit
            logger.info(
                "Security audit - sensitive operation",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host,
                user_agent=request.headers.get("User-Agent", "unknown"),
                request_id=getattr(request.state, 'request_id', 'unknown'),
                correlation_id=getattr(request.state, 'correlation_id', 'unknown')
            )
        
        response = await call_next(request)
        
        # Log security events for failed requests
        if response.status_code >= 400:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.warning(
                "Security audit - failed request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host,
                user_agent=request.headers.get("User-Agent", "unknown"),
                request_id=getattr(request.state, 'request_id', 'unknown'),
                correlation_id=getattr(request.state, 'correlation_id', 'unknown')
            )
        
        return response