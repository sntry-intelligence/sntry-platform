"""
Integration tests for authentication API routes
"""
import pytest
from fastapi import status


class TestAuthenticationRoutes:
    """Test authentication endpoints"""
    
    def test_register_user_success(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "api_user" in data["roles"]  # Default role
    
    def test_register_user_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email"""
        # Register user first time
        client.post("/auth/register", json=test_user_data)
        
        # Try to register again with same email
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "different_username"
        
        response = client.post("/auth/register", json=duplicate_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]
    
    def test_register_user_duplicate_username(self, client, test_user_data):
        """Test registration with duplicate username"""
        # Register user first time
        client.post("/auth/register", json=test_user_data)
        
        # Try to register again with same username
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        
        response = client.post("/auth/register", json=duplicate_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]
    
    def test_login_success(self, client, regular_user):
        """Test successful login"""
        login_data = {
            "username": "regularuser",
            "password": "userpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800
    
    def test_login_invalid_credentials(self, client, regular_user):
        """Test login with invalid credentials"""
        login_data = {
            "username": "regularuser",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        login_data = {
            "username": "nonexistent",
            "password": "password"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token_success(self, client, regular_user):
        """Test successful token refresh"""
        # First login to get tokens
        login_data = {
            "username": "regularuser",
            "password": "userpassword"
        }
        login_response = client.post("/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token"""
        refresh_data = {"refresh_token": "invalid_token"}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token" in response.json()["detail"]
    
    def test_logout_success(self, client, user_token):
        """Test successful logout"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.post("/auth/logout", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "Successfully logged out" in response.json()["message"]
    
    def test_logout_without_token(self, client):
        """Test logout without authentication token"""
        response = client.post("/auth/logout")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserManagementRoutes:
    """Test user management endpoints"""
    
    def test_get_current_user_info(self, client, user_token, regular_user):
        """Test getting current user information"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "regularuser"
        assert data["email"] == "user@example.com"
        assert "api_user" in data["roles"]
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting user info without authentication"""
        response = client.get("/auth/me")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_check_permissions_success(self, client, user_token):
        """Test checking user permissions"""
        headers = {"Authorization": f"Bearer {user_token}"}
        permission_data = {
            "resource": "agents",
            "action": "read"
        }
        
        response = client.get("/auth/permissions", params=permission_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["resource"] == "agents"
        assert data["action"] == "read"
        assert data["has_permission"] is True  # api_user can read agents
    
    def test_check_permissions_denied(self, client, user_token):
        """Test checking denied permissions"""
        headers = {"Authorization": f"Bearer {user_token}"}
        permission_data = {
            "resource": "agents",
            "action": "delete"
        }
        
        response = client.get("/auth/permissions", params=permission_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_permission"] is False  # api_user cannot delete agents


class TestRoleManagementRoutes:
    """Test role management endpoints"""
    
    def test_create_role_admin(self, client, admin_token):
        """Test creating a role as admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        role_data = {
            "name": "test_role",
            "description": "Test role for testing"
        }
        
        response = client.post("/auth/roles", json=role_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test_role"
        assert data["description"] == "Test role for testing"
        assert data["is_active"] is True
    
    def test_create_role_unauthorized(self, client, user_token):
        """Test creating a role as regular user (should fail)"""
        headers = {"Authorization": f"Bearer {user_token}"}
        role_data = {
            "name": "test_role",
            "description": "Test role"
        }
        
        response = client.post("/auth/roles", json=role_data, headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_list_roles(self, client, user_token):
        """Test listing roles (any authenticated user can do this)"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/auth/roles", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Check that default roles exist
        role_names = [role["name"] for role in data]
        assert "admin" in role_names
        assert "api_user" in role_names
        assert "viewer" in role_names


class TestPermissionManagementRoutes:
    """Test permission management endpoints"""
    
    def test_create_permission_admin(self, client, admin_token):
        """Test creating a permission as admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        permission_data = {
            "name": "test_permission",
            "resource": "test_resource",
            "action": "test_action",
            "description": "Test permission"
        }
        
        response = client.post("/auth/permissions", json=permission_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test_permission"
        assert data["resource"] == "test_resource"
        assert data["action"] == "test_action"
    
    def test_create_permission_unauthorized(self, client, user_token):
        """Test creating a permission as regular user (should fail)"""
        headers = {"Authorization": f"Bearer {user_token}"}
        permission_data = {
            "name": "test_permission",
            "resource": "test_resource",
            "action": "test_action"
        }
        
        response = client.post("/auth/permissions", json=permission_data, headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_list_permissions(self, client, user_token):
        """Test listing permissions"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/auth/permissions", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Check that default permissions exist
        permission_names = [perm["name"] for perm in data]
        assert "read_agent" in permission_names
        assert "create_agent" in permission_names


class TestRoleAssignmentRoutes:
    """Test role assignment endpoints"""
    
    def test_assign_user_roles_admin(self, client, admin_token, regular_user, db_session):
        """Test assigning roles to user as admin"""
        # Get role IDs
        from app.models import Role
        viewer_role = db_session.query(Role).filter(Role.name == "viewer").first()
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        assignment_data = {
            "user_id": regular_user.id,
            "role_ids": [viewer_role.id]
        }
        
        response = client.post(
            f"/auth/users/{regular_user.id}/roles",
            json=assignment_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "viewer" in data["assigned_roles"]
    
    def test_assign_user_roles_unauthorized(self, client, user_token, regular_user):
        """Test assigning roles as regular user (should fail)"""
        headers = {"Authorization": f"Bearer {user_token}"}
        assignment_data = {
            "user_id": regular_user.id,
            "role_ids": [1]
        }
        
        response = client.post(
            f"/auth/users/{regular_user.id}/roles",
            json=assignment_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN