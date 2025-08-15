from contextlib import asynccontextmanager
from fastapi import FastAPI

from shared.config import get_settings
from shared.database import DatabaseManager
from shared.utils.logging import configure_logging, get_logger
from routers import agents, conversations, evaluations, health

# Configure logging
configure_logging()
logger = get_logger("agent-management")

# Settings
settings = get_settings()

# Database manager
db_manager = DatabaseManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Agent Management Service")
    await db_manager.startup()
    logger.info("Agent Management Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Management Service")
    await db_manager.shutdown()
    logger.info("Agent Management Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Agent Management Service",
    version="1.0.0",
    description="AI Agent lifecycle management and ADK integration",
    lifespan=lifespan
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(conversations.router, prefix="/agents", tags=["Conversations"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Agent Management Service",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)