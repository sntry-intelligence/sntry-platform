"""
Database configuration and connection management with optimized connection pooling
"""
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# PostgreSQL engine for business data with optimized connection pooling
postgres_engine = create_engine(
    settings.postgres_url,
    poolclass=QueuePool,
    pool_size=10,  # Number of connections to maintain in the pool
    max_overflow=20,  # Additional connections that can be created on demand
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.DEBUG,
    connect_args={
        "options": "-c timezone=utc"  # Set timezone for all connections
    }
)

# SQL Server engine for customer data warehouse with connection pooling
sqlserver_engine = create_engine(
    settings.sqlserver_url,
    poolclass=QueuePool,
    pool_size=5,  # Smaller pool for data warehouse
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
) if hasattr(settings, 'SQLSERVER_PASSWORD') and settings.SQLSERVER_PASSWORD else None

# Session makers
PostgresSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
SQLServerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlserver_engine) if sqlserver_engine else None

# Base classes for models
PostgresBase = declarative_base()
SQLServerBase = declarative_base()


def get_postgres_db():
    """Get PostgreSQL database session"""
    db = PostgresSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sqlserver_db():
    """Get SQL Server database session"""
    if not SQLServerSessionLocal:
        raise RuntimeError("SQL Server not configured")
    db = SQLServerSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize databases and create schemas"""
    try:
        # Initialize PostgreSQL with PostGIS
        await init_postgres()
        
        # Initialize SQL Server if configured
        if sqlserver_engine:
            await init_sqlserver()
            
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def init_postgres():
    """Initialize PostgreSQL database with PostGIS extension and schemas"""
    try:
        with postgres_engine.connect() as conn:
            # Enable PostGIS extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            
            # Create business_data schema
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS business_data;"))
            
            # Create customer_data schema
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS customer_data;"))
            
            conn.commit()
            
        logger.info("PostgreSQL database initialized with PostGIS extension and schemas")
    except Exception as e:
        logger.error(f"PostgreSQL initialization failed: {e}")
        raise


async def init_sqlserver():
    """Initialize SQL Server data warehouse"""
    try:
        with sqlserver_engine.connect() as conn:
            # Create customer data warehouse schema
            conn.execute(text("""
                IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'customer_360')
                BEGIN
                    EXEC('CREATE SCHEMA customer_360')
                END
            """))
            
            conn.commit()
            
        logger.info("SQL Server data warehouse initialized")
    except Exception as e:
        logger.error(f"SQL Server initialization failed: {e}")
        raise


def test_connections():
    """Test database connections"""
    try:
        # Test PostgreSQL
        with postgres_engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            logger.info(f"PostgreSQL connection successful: {result.fetchone()[0]}")
        
        # Test SQL Server if configured
        if sqlserver_engine:
            with sqlserver_engine.connect() as conn:
                result = conn.execute(text("SELECT @@VERSION;"))
                logger.info(f"SQL Server connection successful: {result.fetchone()[0]}")
        
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False