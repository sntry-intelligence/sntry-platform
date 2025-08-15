from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

# Database configuration
def get_database_url(db_name: str) -> str:
    """Get database URL for specific database"""
    # Use SQLite for testing if PostgreSQL is not available
    postgres_url = os.getenv("DATABASE_URL")
    if postgres_url and "postgresql" in postgres_url:
        return f"{postgres_url}/{db_name}"
    else:
        # Fallback to SQLite
        return f"sqlite:///./{db_name}.db"

DATABASE_URL = get_database_url("data_pipeline_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()