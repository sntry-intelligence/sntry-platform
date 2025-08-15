from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.database import DatabaseManager
from shared.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("vector-database")
settings = get_settings()
db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Vector Database Service")
    await db_manager.startup()
    yield
    await db_manager.shutdown()

app = FastAPI(
    title="Vector Database Service",
    version="1.0.0",
    description="RAG capabilities and semantic search",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"service": "Vector Database Service", "version": "1.0.0", "status": "running"}