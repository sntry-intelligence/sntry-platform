import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.interfaces.base_service import BaseService

# Import guardrails service components
from app.routes import router as guardrails_router
from app.database import initialize_database


class GuardrailsService(BaseService):
    """AI guardrails and safety service"""
    
    def __init__(self):
        super().__init__("guardrails-service")
        # Initialize database on startup
        initialize_database()
    
    def _setup_routes(self, app: FastAPI):
        """Setup guardrails service routes"""
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            return self.get_health_status()
        
        # Include guardrails routes
        app.include_router(guardrails_router, tags=["guardrails"])


# Create service instance
guardrails_service = GuardrailsService()
app = guardrails_service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)  # Use port 8003 for guardrails service