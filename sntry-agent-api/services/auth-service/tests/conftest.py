"""
Test configuration and fixtures for auth service tests
"""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import Mock

# Set test environment variables
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["AUTH_DATABASE_URL"] = "sqlite:///./test_auth.db"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"

from app.models import Base, User, Role, Permission
from app.database import get_db, init_default_data
from app.auth import AuthManager


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Initialize default data
        init_default_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""
    # Import app here to avoid circular imports
    from main import app
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock Redis for testing
    import app.auth
    app.auth.redis_client = Mock()
    app.auth.redis_client.get.return_value = None
    app.auth.redis_client.setex.return_value = True
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing"""
    # Get admin role
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    
    # Create admin user
    hashed_password = AuthManager.get_password_hash("adminpassword")
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=hashed_password,
        full_name="Admin User",
        is_active=True,
        is_verified=True
    )
    
    db_session.add(admin)
    db_session.flush()
    
    if admin_role:
        admin.roles.append(admin_role)
    
    db_session.commit()
    db_session.refresh(admin)
    
    return admin


@pytest.fixture
def admin_token(admin_user):
    """Create an admin JWT token for testing"""
    return AuthManager.create_access_token(
        data={"sub": str(admin_user.id), "username": admin_user.username}
    )


@pytest.fixture
def regular_user(db_session):
    """Create a regular user for testing"""
    # Get api_user role
    api_role = db_session.query(Role).filter(Role.name == "api_user").first()
    
    # Create regular user
    hashed_password = AuthManager.get_password_hash("userpassword")
    user = User(
        email="user@example.com",
        username="regularuser",
        hashed_password=hashed_password,
        full_name="Regular User",
        is_active=True,
        is_verified=True
    )
    
    db_session.add(user)
    db_session.flush()
    
    if api_role:
        user.roles.append(api_role)
    
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def user_token(regular_user):
    """Create a regular user JWT token for testing"""
    return AuthManager.create_access_token(
        data={"sub": str(regular_user.id), "username": regular_user.username}
    )