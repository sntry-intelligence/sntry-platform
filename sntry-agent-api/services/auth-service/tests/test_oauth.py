"""
Unit tests for OAuth 2.0 functionality
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import status
from app.auth import OAuth2Config
from app.models import OAuthProvider


class TestOAuth2Config:
    """Test OAuth 2.0 configuration and utilities"""
    
    def test_get_authorization_url_google(self):
        """Test Google OAuth authorization URL generation"""
        with patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_client_id'}, clear=False):
            # Reload the OAuth2Config to pick up the new environment variable
            from app.auth import OAuth2Config
            OAuth2Config.PROVIDERS["google"]["client_id"] = "test_client_id"
            
            url = OAuth2Config.get_authorization_url(
                "google", 
                "http://localhost:8000/callback", 
                "test_state"
            )
            
            assert "accounts.google.com/o/oauth2/v2/auth" in url
            assert "client_id=test_client_id" in url
            assert "redirect_uri=http://localhost:8000/callback" in url
            assert "state=test_state" in url
            assert "scope=openid email profile" in url
    
    def test_get_authorization_url_github(self):
        """Test GitHub OAuth authorization URL generation"""
        with patch.dict('os.environ', {'GITHUB_CLIENT_ID': 'test_client_id'}, clear=False):
            # Reload the OAuth2Config to pick up the new environment variable
            from app.auth import OAuth2Config
            OAuth2Config.PROVIDERS["github"]["client_id"] = "test_client_id"
            
            url = OAuth2Config.get_authorization_url(
                "github", 
                "http://localhost:8000/callback", 
                "test_state"
            )
            
            assert "github.com/login/oauth/authorize" in url
            assert "client_id=test_client_id" in url
            assert "scope=user:email" in url
    
    def test_get_authorization_url_unsupported_provider(self):
        """Test authorization URL generation with unsupported provider"""
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            OAuth2Config.get_authorization_url(
                "unsupported", 
                "http://localhost:8000/callback", 
                "test_state"
            )
    
    def test_get_authorization_url_missing_client_id(self):
        """Test authorization URL generation with missing client ID"""
        from app.auth import OAuth2Config
        # Clear the client ID
        OAuth2Config.PROVIDERS["google"]["client_id"] = None
        
        with pytest.raises(ValueError, match="Client ID not configured"):
            OAuth2Config.get_authorization_url(
                "google", 
                "http://localhost:8000/callback", 
                "test_state"
            )
    
    def test_normalize_user_data_google(self):
        """Test user data normalization for Google"""
        google_data = {
            "id": "123456789",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        normalized = OAuth2Config.normalize_user_data("google", google_data)
        
        assert normalized["id"] == "123456789"
        assert normalized["email"] == "user@gmail.com"
        assert normalized["name"] == "Test User"
        assert normalized["picture"] == "https://example.com/avatar.jpg"
        assert normalized["verified_email"] is True
    
    def test_normalize_user_data_github(self):
        """Test user data normalization for GitHub"""
        github_data = {
            "id": 123456789,
            "login": "testuser",
            "name": "Test User",
            "email": "user@example.com",
            "avatar_url": "https://github.com/avatar.jpg"
        }
        
        normalized = OAuth2Config.normalize_user_data("github", github_data)
        
        assert normalized["id"] == "123456789"
        assert normalized["email"] == "user@example.com"
        assert normalized["name"] == "Test User"
        assert normalized["picture"] == "https://github.com/avatar.jpg"
        assert normalized["verified_email"] is True
    
    def test_normalize_user_data_microsoft(self):
        """Test user data normalization for Microsoft"""
        microsoft_data = {
            "id": "abc123-def456",
            "displayName": "Test User",
            "mail": "user@outlook.com",
            "userPrincipalName": "user@company.com"
        }
        
        normalized = OAuth2Config.normalize_user_data("microsoft", microsoft_data)
        
        assert normalized["id"] == "abc123-def456"
        assert normalized["email"] == "user@outlook.com"
        assert normalized["name"] == "Test User"
        assert normalized["verified_email"] is True
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self):
        """Test successful code exchange for token"""
        mock_token_response = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token"
        }
        
        mock_user_info = {
            "id": "123456789",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }, clear=False):
            # Update the OAuth2Config providers
            from app.auth import OAuth2Config
            OAuth2Config.PROVIDERS["google"]["client_id"] = "test_client_id"
            OAuth2Config.PROVIDERS["google"]["client_secret"] = "test_client_secret"
            
            with patch('app.auth.OAuth2Config.get_user_info', new_callable=AsyncMock) as mock_get_user_info:
                mock_get_user_info.return_value = mock_user_info
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = mock_token_response
                    
                    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                    
                    result = await OAuth2Config.exchange_code_for_token(
                        "google",
                        "test_code",
                        "http://localhost:8000/callback"
                    )
                    
                    assert result["access_token"] == "test_access_token"
                    assert result["token_type"] == "Bearer"
                    assert result["user_info"] == mock_user_info
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_unsupported_provider(self):
        """Test code exchange with unsupported provider"""
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            await OAuth2Config.exchange_code_for_token(
                "unsupported",
                "test_code",
                "http://localhost:8000/callback"
            )
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful user info retrieval"""
        mock_user_data = {
            "id": "123456789",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            from app.auth import OAuth2Config
            result = await OAuth2Config.get_user_info("google", "test_access_token")
            
            assert result["id"] == "123456789"
            assert result["email"] == "user@gmail.com"
            assert result["name"] == "Test User"


class TestOAuthRoutes:
    """Test OAuth 2.0 API routes"""
    
    def test_oauth_authorize_success(self, client):
        """Test successful OAuth authorization request"""
        with patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_client_id'}):
            request_data = {
                "provider": "google",
                "redirect_uri": "http://localhost:8000/callback"
            }
            
            response = client.post("/auth/oauth/authorize", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert "accounts.google.com" in data["authorization_url"]
    
    def test_oauth_authorize_unsupported_provider(self, client):
        """Test OAuth authorization with unsupported provider"""
        request_data = {
            "provider": "unsupported",
            "redirect_uri": "http://localhost:8000/callback"
        }
        
        response = client.post("/auth/oauth/authorize", json=request_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported OAuth provider" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_oauth_callback_new_user(self, client, db_session):
        """Test OAuth callback with new user creation"""
        mock_oauth_data = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "user_info": {
                "id": "123456789",
                "email": "newuser@gmail.com",
                "name": "New User",
                "picture": "https://example.com/avatar.jpg",
                "verified_email": True
            }
        }
        
        with patch('app.auth.OAuth2Config.exchange_code_for_token', new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = mock_oauth_data
            
            request_data = {
                "provider": "google",
                "code": "test_code",
                "state": "test_state",
                "redirect_uri": "http://localhost:8000/callback"
            }
            
            response = client.post("/auth/oauth/callback", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["user"]["email"] == "newuser@gmail.com"
            assert data["user"]["full_name"] == "New User"
    
    def test_get_oauth_providers_unauthorized(self, client):
        """Test getting OAuth providers without authentication"""
        response = client.get("/auth/oauth/providers")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_oauth_providers_success(self, client, user_token, regular_user, db_session):
        """Test getting OAuth providers for authenticated user"""
        # Create OAuth provider for user
        oauth_provider = OAuthProvider(
            user_id=regular_user.id,
            provider="google",
            provider_user_id="123456789",
            email="user@gmail.com",
            name="Test User",
            access_token="test_token"
        )
        db_session.add(oauth_provider)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/auth/oauth/providers", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "google"
        assert data[0]["email"] == "user@gmail.com"
    
    def test_set_password_success(self, client, user_token):
        """Test setting password for OAuth user"""
        headers = {"Authorization": f"Bearer {user_token}"}
        password_data = {"password": "newpassword123"}
        
        response = client.post("/auth/set-password", json=password_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "Password set successfully" in response.json()["message"]
    
    def test_set_password_too_short(self, client, user_token):
        """Test setting password that's too short"""
        headers = {"Authorization": f"Bearer {user_token}"}
        password_data = {"password": "short"}
        
        response = client.post("/auth/set-password", json=password_data, headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least 8 characters" in response.json()["detail"]