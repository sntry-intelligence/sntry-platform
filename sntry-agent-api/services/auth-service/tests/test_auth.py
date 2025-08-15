"""
Unit tests for authentication functionality
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt
from app.auth import AuthManager, SECRET_KEY, ALGORITHM
from app.models import User, Role, Permission


class TestAuthManager:
    """Test AuthManager functionality"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = AuthManager.get_password_hash(password)
        
        assert hashed != password
        assert AuthManager.verify_password(password, hashed)
        assert not AuthManager.verify_password("wrongpassword", hashed)
    
    def test_create_access_token(self):
        """Test JWT access token creation"""
        data = {"sub": "123", "username": "testuser"}
        token = AuthManager.create_access_token(data)
        
        # Decode token to verify contents
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test JWT refresh token creation"""
        data = {"sub": "123", "username": "testuser"}
        token = AuthManager.create_refresh_token(data)
        
        # Decode token to verify contents
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        data = {"sub": "123", "username": "testuser"}
        token = AuthManager.create_access_token(data)
        
        payload = AuthManager.verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
    
    def test_verify_token_invalid_type(self):
        """Test token verification with wrong token type"""
        data = {"sub": "123", "username": "testuser"}
        access_token = AuthManager.create_access_token(data)
        
        # Try to verify access token as refresh token
        payload = AuthManager.verify_token(access_token, "refresh")
        
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test token verification with expired token"""
        data = {"sub": "123", "username": "testuser"}
        # Create token that expires immediately
        expired_token = AuthManager.create_access_token(
            data, expires_delta=timedelta(seconds=-1)
        )
        
        payload = AuthManager.verify_token(expired_token, "access")
        
        assert payload is None
    
    def test_authenticate_user_valid(self, db_session, regular_user):
        """Test user authentication with valid credentials"""
        user = AuthManager.authenticate_user(db_session, "regularuser", "userpassword")
        
        assert user is not None
        assert user.username == "regularuser"
        assert user.email == "user@example.com"
    
    def test_authenticate_user_invalid_password(self, db_session, regular_user):
        """Test user authentication with invalid password"""
        user = AuthManager.authenticate_user(db_session, "regularuser", "wrongpassword")
        
        assert user is None
    
    def test_authenticate_user_nonexistent(self, db_session):
        """Test user authentication with nonexistent user"""
        user = AuthManager.authenticate_user(db_session, "nonexistent", "password")
        
        assert user is None
    
    def test_authenticate_user_inactive(self, db_session):
        """Test user authentication with inactive user"""
        # Create inactive user
        hashed_password = AuthManager.get_password_hash("password")
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            hashed_password=hashed_password,
            is_active=False
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        user = AuthManager.authenticate_user(db_session, "inactive", "password")
        
        assert user is None
    
    def test_get_user_permissions(self, db_session, admin_user):
        """Test getting user permissions"""
        permissions = AuthManager.get_user_permissions(db_session, admin_user.id)
        
        assert "*:*" in permissions  # Admin should have all permissions
    
    def test_check_permission_admin(self, db_session, admin_user):
        """Test permission checking for admin user"""
        # Admin should have all permissions
        assert AuthManager.check_permission(db_session, admin_user.id, "agents", "create")
        assert AuthManager.check_permission(db_session, admin_user.id, "models", "delete")
        assert AuthManager.check_permission(db_session, admin_user.id, "any_resource", "any_action")
    
    def test_check_permission_regular_user(self, db_session, regular_user):
        """Test permission checking for regular user"""
        # Regular user (api_user role) should only have read permissions for agents and models
        assert AuthManager.check_permission(db_session, regular_user.id, "agents", "read")
        assert AuthManager.check_permission(db_session, regular_user.id, "models", "read")
        assert not AuthManager.check_permission(db_session, regular_user.id, "agents", "create")
        assert not AuthManager.check_permission(db_session, regular_user.id, "models", "delete")
    
    def test_check_permission_nonexistent_user(self, db_session):
        """Test permission checking for nonexistent user"""
        assert not AuthManager.check_permission(db_session, 99999, "agents", "read")


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    def test_user_roles_assignment(self, db_session):
        """Test assigning roles to users"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True
        )
        db_session.add(user)
        db_session.flush()
        
        # Get roles
        admin_role = db_session.query(Role).filter(Role.name == "admin").first()
        viewer_role = db_session.query(Role).filter(Role.name == "viewer").first()
        
        # Assign roles
        user.roles.extend([admin_role, viewer_role])
        db_session.commit()
        
        # Verify assignment
        user_roles = [role.name for role in user.roles]
        assert "admin" in user_roles
        assert "viewer" in user_roles
    
    def test_role_permissions_assignment(self, db_session):
        """Test assigning permissions to roles"""
        # Create custom role
        custom_role = Role(name="custom_role", description="Custom test role")
        db_session.add(custom_role)
        db_session.flush()
        
        # Get permissions
        read_agent_perm = db_session.query(Permission).filter(
            Permission.name == "read_agent"
        ).first()
        create_agent_perm = db_session.query(Permission).filter(
            Permission.name == "create_agent"
        ).first()
        
        # Assign permissions
        custom_role.permissions.extend([read_agent_perm, create_agent_perm])
        db_session.commit()
        
        # Verify assignment
        role_permissions = [f"{p.resource}:{p.action}" for p in custom_role.permissions]
        assert "agents:read" in role_permissions
        assert "agents:create" in role_permissions
    
    def test_inherited_permissions(self, db_session):
        """Test that users inherit permissions from their roles"""
        # Create user with ai_engineer role
        ai_role = db_session.query(Role).filter(Role.name == "ai_engineer").first()
        
        user = User(
            email="engineer@example.com",
            username="engineer",
            hashed_password="hashed",
            is_active=True
        )
        user.roles.append(ai_role)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Check permissions
        permissions = AuthManager.get_user_permissions(db_session, user.id)
        
        # AI engineer should have agent and model permissions
        assert "agents:create" in permissions
        assert "agents:read" in permissions
        assert "models:create" in permissions
        assert "training:create" in permissions