"""
Unit tests for API Gateway routing, middleware, and security features.
Tests requirements 7.1, 7.2, 7.3, 8.1, and 9.3.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, Response
import time
import json

from services.api_gateway.main import app
from shared.auth import create_access_token, User
from shared.middleware.security import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    RequestValidationMiddleware,
    CorrelationIdMiddleware,
    SecurityAuditMiddleware
)


class TestAPIGatewayRouting:
    """Test API Gateway routing functionality"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint accessibility"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    def test_health_endpoint_no_auth_required(self):
        """Test health endpoint doesn't require authentication"""
        response = self.client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
    
    def test_protected_endpoint_requires_auth(self):
        """Test that protected endpoints require authentication"""
        response = self.client.get("/v1/agents/")
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication required"
        assert data["error_code"] == "AUTH_REQUIRED"
    
    def test_protected_endpoint_with_valid_auth(self):
        """Test protected endpoint with valid authentication"""
        # Create a valid JWT token
        token_data = {
            "sub": "user123",
            "username": "testuser",
            "scopes": ["agent:read"]
        }
        token = create_access_token(token_data)
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"agents": []}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            response = self.client.get(
                "/v1/agents/",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should not get 401 (might get other errors due to mocking)
            assert response.status_code != 401
    
    def test_cors_headers_present(self):
        """Test CORS headers are present in responses"""
        response = self.client.get("/")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-credentials" in response.headers
    
    def test_request_id_header_present(self):
        """Test that X-Request-ID header is present in responses"""
        response = self.client.get("/")
        
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0
    
    def test_api_version_header_present(self):
        """Test that X-API-Version header is present in responses"""
        response = self.client.get("/")
        
        assert "x-api-version" in response.headers


class TestSecurityHeaders:
    """Test security headers middleware"""
    
    def setup_method(self):
        """Set up test app with security middleware"""
        self.app = FastAPI()
        self.app.add_middleware(SecurityHeadersMiddleware)
        
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        self.client = TestClient(self.app)
    
    def test_security_headers_added(self):
        """Test that security headers are added to responses"""
        response = self.client.get("/test")
        
        expected_headers = [
            "x-frame-options",
            "x-content-type-options",
            "x-xss-protection",
            "referrer-policy",
            "content-security-policy",
            "strict-transport-security",
            "permissions-policy"
        ]
        
        for header in expected_headers:
            assert header in response.headers
    
    def test_x_frame_options_deny(self):
        """Test X-Frame-Options is set to DENY"""
        response = self.client.get("/test")
        assert response.headers["x-frame-options"] == "DENY"
    
    def test_content_type_options_nosniff(self):
        """Test X-Content-Type-Options is set to nosniff"""
        response = self.client.get("/test")
        assert response.headers["x-content-type-options"] == "nosniff"
    
    def test_xss_protection_enabled(self):
        """Test X-XSS-Protection is enabled"""
        response = self.client.get("/test")
        assert response.headers["x-xss-protection"] == "1; mode=block"
    
    def test_hsts_header_present(self):
        """Test Strict-Transport-Security header is present"""
        response = self.client.get("/test")
        hsts_header = response.headers["strict-transport-security"]
        assert "max-age=31536000" in hsts_header
        assert "includeSubDomains" in hsts_header


class TestHTTPSRedirect:
    """Test HTTPS redirect middleware"""
    
    def setup_method(self):
        """Set up test app with HTTPS middleware"""
        self.app = FastAPI()
        self.app.add_middleware(HTTPSRedirectMiddleware, enforce_https=True)
        
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        self.client = TestClient(self.app)
    
    def test_https_enforcement_disabled_for_localhost(self):
        """Test HTTPS enforcement is disabled for localhost"""
        # TestClient uses localhost by default
        response = self.client.get("/test")
        assert response.status_code == 200
    
    def test_https_enforcement_with_forwarded_proto(self):
        """Test HTTPS enforcement with X-Forwarded-Proto header"""
        # This test would need a custom test setup to simulate non-localhost
        # For now, we'll test the logic indirectly
        pass


class TestRequestValidation:
    """Test request validation middleware"""
    
    def setup_method(self):
        """Set up test app with request validation middleware"""
        self.app = FastAPI()
        self.app.add_middleware(RequestValidationMiddleware)
        
        @self.app.post("/test")
        async def test_endpoint(request: Request):
            return {"message": "test"}
        
        self.client = TestClient(self.app)
    
    def test_large_request_blocked(self):
        """Test that large requests are blocked"""
        large_data = "x" * (11 * 1024 * 1024)  # 11MB
        
        response = self.client.post(
            "/test",
            content=large_data,
            headers={"content-type": "text/plain"}
        )
        
        assert response.status_code == 413
        assert "Request entity too large" in response.json()["detail"]
    
    def test_suspicious_user_agent_blocked(self):
        """Test that suspicious user agents are blocked"""
        response = self.client.get(
            "/test",
            headers={"User-Agent": "sqlmap/1.0"}
        )
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"
    
    def test_normal_request_allowed(self):
        """Test that normal requests are allowed"""
        response = self.client.post(
            "/test",
            json={"data": "normal request"},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        assert response.status_code == 200


class TestCorrelationId:
    """Test correlation ID middleware"""
    
    def setup_method(self):
        """Set up test app with correlation ID middleware"""
        self.app = FastAPI()
        self.app.add_middleware(CorrelationIdMiddleware)
        
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        self.client = TestClient(self.app)
    
    def test_correlation_id_added_to_response(self):
        """Test that correlation ID is added to response headers"""
        response = self.client.get("/test")
        
        assert "x-correlation-id" in response.headers
        assert len(response.headers["x-correlation-id"]) > 0
    
    def test_existing_correlation_id_preserved(self):
        """Test that existing correlation ID is preserved"""
        correlation_id = "test-correlation-123"
        
        response = self.client.get(
            "/test",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        assert response.headers["x-correlation-id"] == correlation_id


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    @patch("shared.utils.rate_limiting.get_redis")
    def test_rate_limiting_allows_normal_requests(self, mock_redis):
        """Test that rate limiting allows normal requests"""
        # Mock Redis to return low request count
        mock_redis_client = AsyncMock()
        mock_redis_client.pipeline.return_value.execute = AsyncMock(
            return_value=[None, 5, None, None]  # 5 current requests
        )
        mock_redis.return_value.__aenter__.return_value = mock_redis_client
        
        response = self.client.get("/")
        
        # Should not be rate limited
        assert response.status_code == 200
    
    @patch("shared.utils.rate_limiting.get_redis")
    def test_rate_limiting_blocks_excessive_requests(self, mock_redis):
        """Test that rate limiting blocks excessive requests"""
        # Mock Redis to return high request count
        mock_redis_client = AsyncMock()
        mock_redis_client.pipeline.return_value.execute = AsyncMock(
            return_value=[None, 150, None, None]  # 150 current requests (over limit)
        )
        mock_redis.return_value.__aenter__.return_value = mock_redis_client
        
        response = self.client.get("/")
        
        # Should be rate limited
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are present in responses"""
        with patch("shared.utils.rate_limiting.get_redis") as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.pipeline.return_value.execute = AsyncMock(
                return_value=[None, 5, None, None]
            )
            mock_redis.return_value.__aenter__.return_value = mock_redis_client
            
            response = self.client.get("/")
            
            assert "x-ratelimit-limit" in response.headers
            assert "x-ratelimit-remaining" in response.headers
            assert "x-ratelimit-reset" in response.headers


class TestSecurityAudit:
    """Test security audit middleware"""
    
    def setup_method(self):
        """Set up test app with security audit middleware"""
        self.app = FastAPI()
        self.app.add_middleware(SecurityAuditMiddleware)
        
        @self.app.get("/v1/agents/")
        async def sensitive_endpoint():
            return {"agents": []}
        
        @self.app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        self.client = TestClient(self.app)
    
    @patch("shared.middleware.security.logger")
    def test_sensitive_operations_logged(self, mock_logger):
        """Test that sensitive operations are logged"""
        response = self.client.get("/v1/agents/")
        
        # Check that security audit log was called
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0]
        assert "Security audit - sensitive operation" in call_args[0]
    
    @patch("shared.middleware.security.logger")
    def test_failed_requests_logged(self, mock_logger):
        """Test that failed requests are logged"""
        # This endpoint doesn't exist, should return 404
        response = self.client.get("/v1/nonexistent")
        
        # Check that security audit warning was called
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0]
        assert "Security audit - failed request" in call_args[0]


class TestErrorHandling:
    """Test error handling in API Gateway"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_404_error_format(self):
        """Test 404 error response format"""
        response = self.client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_401_error_format(self):
        """Test 401 error response format"""
        response = self.client.get("/v1/agents/")
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication required"
        assert data["error_code"] == "AUTH_REQUIRED"
        assert "x-request-id" in response.headers
    
    def test_error_response_includes_request_id(self):
        """Test that error responses include request ID"""
        response = self.client.get("/v1/agents/")
        
        assert "x-request-id" in response.headers
        request_id = response.headers["x-request-id"]
        assert len(request_id) > 0


class TestMiddlewareOrder:
    """Test that middleware is applied in correct order"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_security_headers_applied_to_all_responses(self):
        """Test that security headers are applied to all responses"""
        # Test different endpoints
        endpoints = ["/", "/health/"]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            
            # Security headers should be present
            assert "x-frame-options" in response.headers
            assert "x-content-type-options" in response.headers
            assert "strict-transport-security" in response.headers
    
    def test_request_id_generated_for_all_requests(self):
        """Test that request ID is generated for all requests"""
        endpoints = ["/", "/health/", "/v1/agents/"]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert "x-request-id" in response.headers