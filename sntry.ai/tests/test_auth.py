"""
Unit tests for authentication and authorization functionality.
Tests requirements 7.1, 7.2, and 7.3 for OAuth 2.0, JWT, and security.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
import httpx

from shared.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    verify_oauth_token,
    get_current_user,
    require_scopes,
    AuthenticationError,
    AuthorizationError,
    TokenData,
    User,
    Scopes
)


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_password_hashing_and_verification(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        
        # Verification should work
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail
        assert verify_password("wrong_password", hashed) is False
    
    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes"""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2


class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_create_and_verify_token(self):
        """Test JWT token creation and verification"""
        data = {
            "sub": "user123",
            "username": "testuser",
            "scopes": ["agent:read", "agent:write"]
        }
        
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token
        token_data = verify_token(token)
        assert token_data.user_id == "user123"
        assert token_data.username == "testuser"
        assert token_data.scopes == ["agent:read", "agent:write"]
        assert isinstance(token_data.exp, datetime)
    
    def test_create_token_with_custom_expiration(self):
        """Test JWT token creation with custom expiration"""
        data = {"sub": "user123", "username": "testuser"}
        expires_delta = timedelta(minutes=60)
        
        token = create_access_token(data, expires_delta)
        token_data = verify_token(token)
        
        # Check that expiration is approximately 60 minutes from now
        expected_exp = datetime.utcnow() + expires_delta
        time_diff = abs((token_data.exp - expected_exp).total_seconds())
        assert time_diff < 5  # Allow 5 seconds tolerance
    
    def test_verify_invalid_token(self):
        """Test verification of invalid JWT token"""
        with pytest.raises(AuthenticationError) as exc_info:
            verify_token("invalid.jwt.token")
        
        assert "Invalid token" in str(exc_info.value.detail)
    
    def test_verify_token_missing_user_id(self):
        """Test verification of token missing user ID"""
        data = {"username": "testuser"}  # Missing 'sub' field
        token = create_access_token(data)
        
        with pytest.raises(AuthenticationError) as exc_info:
            verify_token(token)
        
        assert "missing user ID" in str(exc_info.value.detail)


class TestOAuthVerification:
    """Test OAuth 2.0 token verification"""
    
    @pytest.mark.asyncio
    async def test_verify_oauth_token_success(self):
        """Test successful OAuth token verification"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "oauth_user_123",
            "name": "OAuth User",
            "email": "oauth@example.com",
            "scopes": ["agent:read"]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await verify_oauth_token("valid_oauth_token")
            
            assert result["sub"] == "oauth_user_123"
            assert result["name"] == "OAuth User"
            assert result["email"] == "oauth@example.com"
    
    @pytest.mark.asyncio
    async def test_verify_oauth_token_invalid(self):
        """Test OAuth token verification with invalid token"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(AuthenticationError) as exc_info:
                await verify_oauth_token("invalid_oauth_token")
            
            assert "Invalid OAuth token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_verify_oauth_token_network_error(self):
        """Test OAuth token verification with network error"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )
            
            with pytest.raises(AuthenticationError) as exc_info:
                await verify_oauth_token("token")
            
            assert "OAuth verification failed" in str(exc_info.value.detail)


class TestUserAuthentication:
    """Test user authentication functionality"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_jwt_success(self):
        """Test successful user authentication with JWT"""
        # Create a valid JWT token
        data = {
            "sub": "user123",
            "username": "testuser",
            "scopes": ["agent:read", "agent:write"]
        }
        token = create_access_token(data)
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        user = await get_current_user(credentials)
        
        assert isinstance(user, User)
        assert user.id == "user123"
        assert user.username == "testuser"
        assert user.scopes == ["agent:read", "agent:write"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_oauth_fallback(self):
        """Test user authentication falling back to OAuth"""
        # Mock OAuth verification
        mock_user_info = {
            "sub": "oauth_user_123",
            "preferred_username": "oauthuser",
            "email": "oauth@example.com",
            "scopes": ["agent:read"]
        }
        
        with patch("shared.auth.verify_oauth_token", return_value=mock_user_info):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="invalid_jwt_but_valid_oauth"
            )
            
            user = await get_current_user(credentials)
            
            assert isinstance(user, User)
            assert user.id == "oauth_user_123"
            assert user.username == "oauthuser"
            assert user.email == "oauth@example.com"
            assert user.scopes == ["agent:read"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test user authentication with invalid token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="completely_invalid_token"
        )
        
        with patch("shared.auth.verify_oauth_token", side_effect=AuthenticationError()):
            with pytest.raises(AuthenticationError):
                await get_current_user(credentials)


class TestAuthorizationScopes:
    """Test authorization scope functionality"""
    
    @pytest.mark.asyncio
    async def test_require_scopes_success(self):
        """Test successful scope authorization"""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            scopes=["agent:read", "agent:write", "workflow:read"]
        )
        
        @require_scopes(Scopes.AGENT_READ, Scopes.AGENT_WRITE)
        async def test_endpoint(current_user: User):
            return {"message": "success", "user": current_user.username}
        
        result = await test_endpoint(user)
        assert result["message"] == "success"
        assert result["user"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_require_scopes_insufficient_permissions(self):
        """Test scope authorization with insufficient permissions"""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            scopes=["agent:read"]  # Missing agent:write
        )
        
        @require_scopes(Scopes.AGENT_READ, Scopes.AGENT_WRITE)
        async def test_endpoint(current_user: User):
            return {"message": "success"}
        
        with pytest.raises(AuthorizationError) as exc_info:
            await test_endpoint(user)
        
        assert "Missing required scopes" in str(exc_info.value.detail)
        assert "agent:write" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_scopes_no_user(self):
        """Test scope authorization with no user in context"""
        @require_scopes(Scopes.AGENT_READ)
        async def test_endpoint():
            return {"message": "success"}
        
        with pytest.raises(AuthenticationError) as exc_info:
            await test_endpoint()
        
        assert "User not found in request context" in str(exc_info.value.detail)


class TestAuthenticationErrors:
    """Test authentication error handling"""
    
    def test_authentication_error_creation(self):
        """Test AuthenticationError creation"""
        error = AuthenticationError("Custom auth error")
        
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.detail == "Custom auth error"
        assert error.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_authentication_error_default_message(self):
        """Test AuthenticationError with default message"""
        error = AuthenticationError()
        
        assert error.detail == "Authentication failed"
    
    def test_authorization_error_creation(self):
        """Test AuthorizationError creation"""
        error = AuthorizationError("Custom auth error")
        
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Custom auth error"
    
    def test_authorization_error_default_message(self):
        """Test AuthorizationError with default message"""
        error = AuthorizationError()
        
        assert error.detail == "Insufficient permissions"


class TestScopesConstants:
    """Test scope constants"""
    
    def test_scope_constants_exist(self):
        """Test that all required scope constants exist"""
        expected_scopes = [
            "AGENT_READ", "AGENT_WRITE", "AGENT_DELETE",
            "WORKFLOW_READ", "WORKFLOW_WRITE", "WORKFLOW_EXECUTE",
            "TOOL_READ", "TOOL_WRITE",
            "VECTOR_READ", "VECTOR_WRITE",
            "EVALUATION_READ", "EVALUATION_WRITE",
            "ADMIN"
        ]
        
        for scope in expected_scopes:
            assert hasattr(Scopes, scope)
            assert isinstance(getattr(Scopes, scope), str)
    
    def test_scope_values_are_correct(self):
        """Test that scope values follow expected format"""
        assert Scopes.AGENT_READ == "agent:read"
        assert Scopes.AGENT_WRITE == "agent:write"
        assert Scopes.WORKFLOW_EXECUTE == "workflow:execute"
        assert Scopes.ADMIN == "admin"