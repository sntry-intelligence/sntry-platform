from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import uuid

from shared.config import get_settings
from shared.database import DatabaseManager
from shared.utils.logging import configure_logging, get_logger, RequestLogger
from shared.utils.rate_limiting import rate_limit_middleware
from shared.middleware.security import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    RequestValidationMiddleware,
    CorrelationIdMiddleware,
    SecurityAuditMiddleware
)
from shared.auth import AuthMiddleware
from routers import agents, workflows, tools, conversations, vectorstores, mcp_servers, evaluations, health

# Configure logging
configure_logging()
logger = get_logger("api-gateway")
request_logger = RequestLogger("api-gateway")

# Settings
settings = get_settings()

# Database manager
db_manager = DatabaseManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting API Gateway")
    await db_manager.startup()
    logger.info("API Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway")
    await db_manager.shutdown()
    logger.info("API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize authentication middleware
auth_middleware = AuthMiddleware()

# Add security middleware (order matters!)
app.add_middleware(SecurityAuditMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(HTTPSRedirectMiddleware, enforce_https=settings.enforce_https)
app.add_middleware(RequestValidationMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts if settings.allowed_hosts != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID", "X-RateLimit-*"]
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Request processing middleware with authentication and rate limiting"""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Start timing
    start_time = time.time()
    
    # Log request
    await request_logger.log_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host
    )
    
    # Check if path requires authentication
    if auth_middleware.is_protected_path(request.url.path):
        # Verify authentication for protected paths
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(
                "Authentication required but not provided",
                path=request.url.path,
                client_ip=request.client.host,
                request_id=request_id
            )
            return Response(
                content='{"detail":"Authentication required","error_code":"AUTH_REQUIRED"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={
                    "WWW-Authenticate": "Bearer",
                    "Content-Type": "application/json",
                    "X-Request-ID": request_id
                }
            )
    
    # Rate limiting
    try:
        await rate_limit_middleware(request)
    except HTTPException as e:
        logger.warning(
            "Rate limit exceeded",
            client_ip=request.client.host,
            path=request.url.path,
            request_id=request_id
        )
        # Add request ID to rate limit error response
        e.headers = e.headers or {}
        e.headers["X-Request-ID"] = request_id
        raise
    except Exception as e:
        logger.error("Rate limiting error", error=str(e), request_id=request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
            headers={"X-Request-ID": request_id}
        )
    
    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(
            "Request processing error",
            error=str(e),
            path=request.url.path,
            method=request.method,
            request_id=request_id
        )
        raise
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Add standard headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-API-Version"] = settings.api_version
    
    # Add rate limit headers if available
    if hasattr(request.state, 'rate_limit_headers'):
        for key, value in request.state.rate_limit_headers.items():
            response.headers[key] = value
    
    # Log response
    await request_logger.log_response(
        request_id=request_id,
        status_code=response.status_code,
        duration_ms=duration_ms
    )
    
    return response


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(agents.router, prefix="/v1/agents", tags=["Agents"])
app.include_router(workflows.router, prefix="/v1/agents", tags=["Workflows"])
app.include_router(tools.router, prefix="/v1/agents", tags=["Tools"])
app.include_router(conversations.router, prefix="/v1/agents", tags=["Conversations"])
app.include_router(vectorstores.router, prefix="/v1/vectorstores", tags=["Vector Stores"])
app.include_router(mcp_servers.router, prefix="/v1/mcp-servers", tags=["MCP Servers"])
app.include_router(evaluations.router, prefix="/v1/evaluations", tags=["Evaluations"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "sntry.app/ai/v1 REST API Development Framework",
        "version": settings.api_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)