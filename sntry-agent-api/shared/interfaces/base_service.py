from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from fastapi import FastAPI
from shared.utils.logging import setup_logging


class BaseService(ABC):
    """Base class for all microservices"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = setup_logging(service_name)
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application with common configuration"""
        app = FastAPI(
            title=f"{self.service_name.title()} Service",
            description=f"AI Agent Framework - {self.service_name.title()} Service",
            version="1.0.0"
        )
        
        # Add common middleware and exception handlers
        self._setup_middleware(app)
        self._setup_exception_handlers(app)
        
        # Setup routes
        self._setup_routes(app)
        
        return app
    
    def _setup_middleware(self, app: FastAPI):
        """Setup common middleware"""
        from fastapi.middleware.cors import CORSMiddleware
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_exception_handlers(self, app: FastAPI):
        """Setup common exception handlers"""
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse
        
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": f"HTTP_{exc.status_code}",
                        "message": exc.detail,
                        "service": self.service_name
                    }
                }
            )
        
        @app.exception_handler(Exception)
        async def general_exception_handler(request, exc):
            self.logger.error(f"Unhandled exception: {str(exc)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred",
                        "service": self.service_name
                    }
                }
            )
    
    @abstractmethod
    def _setup_routes(self, app: FastAPI):
        """Setup service-specific routes"""
        pass
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": self.service_name,
            "status": "healthy",
            "version": "1.0.0"
        }