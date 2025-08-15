import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.models import Base
from app.database import get_db

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_data_pipeline.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_csv_data():
    return """id,name,age,email
1,John Doe,30,john@example.com
2,Jane Smith,25,jane@example.com
3,Bob Johnson,35,bob@example.com"""


@pytest.fixture
def sample_json_data():
    return [
        {"id": 1, "name": "John Doe", "age": 30, "email": "john@example.com"},
        {"id": 2, "name": "Jane Smith", "age": 25, "email": "jane@example.com"},
        {"id": 3, "name": "Bob Johnson", "age": 35, "email": "bob@example.com"}
    ]