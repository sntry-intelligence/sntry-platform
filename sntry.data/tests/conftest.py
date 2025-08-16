"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import PostgresBase, get_postgres_db
from app.core.config import settings


# Test database URL (use in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_postgres_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create tables
    PostgresBase.metadata.create_all(bind=test_engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        PostgresBase.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""
    app.dependency_overrides[get_postgres_db] = override_get_postgres_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_business_data():
    """Sample business data for testing"""
    return {
        "name": "Test Business",
        "category": "Restaurant",
        "raw_address": "123 Main Street, Kingston, Jamaica",
        "phone_number": "+1-876-123-4567",
        "email": "test@business.com",
        "website": "https://testbusiness.com",
        "description": "A test business for unit testing",
        "source_url": "https://example.com/business/123"
    }


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing"""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+1-876-987-6543",
        "address": "456 Test Avenue, Kingston, Jamaica",
        "customer_type": "individual",
        "company_name": "Test Company Ltd"
    }