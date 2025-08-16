"""
Main FastAPI application entry point for Jamaica Business Directory
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.health_api import router as health_router
from app.core.monitoring_api import router as monitoring_router
from app.core.middleware import LoggingMiddleware, PerformanceMonitoringMiddleware
from app.core.error_handlers import register_exception_handlers
from app.business_directory.api import router as business_router
from app.business_directory.export_api import router as export_router
from app.customer_360.api import router as customer_router
from app.core.tasks_api import router as tasks_router
from config.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Jamaica Business Directory API",
        description="Comprehensive business directory and customer 360 platform for Jamaica",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=2.0)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Include routers
    app.include_router(health_router)  # Health checks at /health/*
    app.include_router(monitoring_router)  # Monitoring at /monitoring/*
    app.include_router(business_router, prefix="/api/v1/business", tags=["business"])
    app.include_router(export_router, prefix="/api/v1", tags=["export"])
    app.include_router(customer_router, prefix="/api/v1/customer", tags=["customer"])
    app.include_router(tasks_router, prefix="/api/v1", tags=["tasks"])
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Root endpoint to serve the main application
    @app.get("/")
    async def read_root():
        """Serve the main application HTML"""
        from fastapi.responses import FileResponse
        return FileResponse('static/index.html')
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )