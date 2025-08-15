import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from fastapi import FastAPI
from shared.interfaces.base_service import BaseService
from app.routes import router
from app.database import create_tables


class DataPipelineService(BaseService):
    """Data pipeline and processing service"""
    
    def __init__(self):
        super().__init__("data-pipeline-service")
        # Create database tables on startup
        create_tables()
    
    def _setup_routes(self, app: FastAPI):
        """Setup data pipeline service routes"""
        app.include_router(router, tags=["data-pipeline"])


# Create service instance
data_pipeline_service = DataPipelineService()
app = data_pipeline_service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)