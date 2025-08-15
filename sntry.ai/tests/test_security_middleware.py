"""
Unit tests for security middleware components.
Tests requirements 7.3 for HTTPS enforcement and security headers.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
import time

from shared.middleware.security import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    RequestValidationMiddleware,
    CorrelationIdMiddleware,
    SecurityAuditMiddleware
)


class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware functionality"""
    
    def setup_method(self):
        """Set up test app with SecurityHeadersMiddleware"""
        self.app = FastAPI()
        self.app.add_middleware(SecurityHeadersMiddleware)
        
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @self.app.post("/test")
        async def test_post_endpoint():
            return {"message": "post test"}
        
        self.client = TestClient(self.app)
    
    def test_all_security_headers_added(self):
        """Test that all required security headers are added"""
        response = self.client.get("/test")
        
        expected_headers = {
            "x-frame-options": "DENY",
            "x-content-type-options": "nosniff",
            "x-xss-protection": "1; mode=block",
            "referrer-policy": "strict-origin-when-cross-origin",
            "strict-transport-security": "max-age=31536000; includeSubDomains"
        }
        
        for header, expected_value in expected_headers.items():
            assert header in response.headers
            assert response.headers[header] == expected_value
    
    def test_content_security_policy_header(self):
        """Test Content Security Policy header"""
        response = self.client.get("/test")
        
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "frame-ancestors 'none'" in csp
    
    def test_permissions_policy_header(self):
        """Test Permissions Policy header"""
        response = self.client.get("/test")
        
        permissions = response.headers["permissions-policy"]
        assert "geolocation=()" in permissions
        assert "microphone=()" in permissions
        assert "camera=()" in permissions
    
    def test_headers_added_to_all_methods(self):
        """Test that headers are added to all HTTP methods"""
        get_response = self.client.get("/test")
        post_response = self.client.post("/test")
        
        for response in [get_response, post_response]:
            assert "x-frame-options" in response.headers
            assert "x-content-type-options" in response.headers


class TestHTTPSRedirectMiddleware:
    """Test HTTPSRedirectMiddleware functionality"""
    
    def setup_method(self):
        """Set up test app with HTTPSRedirectMiddleware"""
        self.app = FastAPI()
        
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
    
    def test_https_enforcement_disabled_for_localhost(self):
        """Test HTTPS enforcement is disabled for localhost"""
        self.app.add_middleware(HTTPSRedirectMiddleware, enforce_https=True)
        client = TestClient(self.app)
        
        response = client.get("/test")
        assert response.status_code == 200
    
    def test_https_enforcement_disabled_when_configured(self):
        """Test HTTPS enforcement can be disabled"""
        self.app.add_middleware(HTTPSRedirectMiddleware, enforce_https=False)
        client = TestClient(self.app)
        
        response = client.get("/test")
        assert response.status_code == 200
    
    def test_https_enforcement_enabled_by_default(self):
        """Test HTTPS enforcement is enabled by default"""
        with patch("shared.config.get_settings") as mock_settings:
            mock_settings.return_value.enforce_https = True
            
            self.app.add_middleware(HTTPSRedirectMiddleware)
            client = TestClient(self.app)
            
            # TestClient uses localhost, so should still work
            response = client.get("/test")
            assert response.status_code == 200


class TestRequestValidationMiddleware:
    """Test RequestValidationMiddleware functionality"""
    
    def setup_method(self):
        """Set up test app with RequestValidationMiddleware"""
        self.app = FastAPI()
        self.app.add_middleware(RequestValidationMiddleware)
        
        @self.app.get("/test")
        async def test_get_endpoint():
            return {"message": "test"}
        
        @self.app.post("/test")
        async def test_post_endpoint():
            return {"message": "post test"}
        
        self.client = TestClient(self.app)
    
    def test_normal_request_allowed(self):
        """Test that normal requests are allowed"""
        response = self.client.get("/test")
        assert response.status_code == 200
    
    def test_large_request_blocked(self):
        """Test that requests exceeding size limit are blocked"""
        # Create content larger than 10MB limit
        large_content = "x" * (11 * 1024 * 1024)
        
        response = self.client.post(
            "/test",
            content=large_content,
            headers={"content-type": "text/plain"}
        )
        
        assert response.status_code == 413
        assert "Request entity too large" in response.json()["detail"]
    
    def test_malicious_user_agents_blocked(self):
        """Test that malicious user agents are blocked"""
        malicious_agents = [
            "sqlmap/1.0",
            "nikto/2.1.6",
            "nmap scripting engine",
            "masscan/1.0",
            "nessus",
            "openvas",
            "w3af.org",
            "skipfish/2.10b"
        ]
        
        for agent in malicious_agents:
            response = self.client.get(
                "/test",
                headers={"User-Agent": agent}
            )
            
            assert response.status_code == 403
            assert response.json()["detail"] == "Access denied"
    
    def test_normal_user_agents_allowed(self):
        """Test that normal user agents are allowed"""
        normal_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "curl/7.68.0",
            "PostmanRuntime/7.28.4",
            "python-requests/2.25.1"
        ]
        
        for agent in normal_agents:
            response = self.client.get(
                "/test",
                headers={"User-Agent": agent}
            )
            
            assert response.status_code == 200
    
    def test_suspicious_headers_blocked(self):
        """Test that suspicious header values are blocked"""
        suspicious_headers = {
            "x-forwarded-host": "evil.com<script>alert('xss')</script>",
            "x-originating-ip": "192.168.1.1\"malicious",
            "x-remote-ip": "10.0.0.1'injection",
            "x-remote-addr": "127.0.0.1>redirect"
        }
        
        for header, value in suspicious_headers.items():
            response = self.client.get(
                "/test",
                headers={header: value}
            )
            
            assert response.status_code == 400
            assert "Invalid header value" in response.json()["detail"]
    
    def test_normal_headers_allowed(self):
        """Test that normal header values are allowed"""
        normal_headers = {
            "x-forwarded-host": "api.example.com",
            "x-originating-ip": "192.168.1.100",
            "x-remote-ip": "10.0.0.50",
            "x-remote-addr": "127.0.0.1"
        }
        
        for header, value in normal_headers.items():
            response = self.client.get(
                "/test",
                headers={header: value}
            )
            
            assert response.status_code == 200


class TestCorrelationIdMiddleware:
    """Test CorrelationIdMiddleware functionality"""
    
    def setup_method(self):
        """Set up test app with CorrelationIdMiddleware"""
        self.app = FastAPI()
        self.app.add_middleware(CorrelationIdMiddleware)
        
        @self.app.get("/test")
        async def test_endpoint(request: Request):
            # Return correlation ID from request state for testing
            correlation_id = getattr(request.state, 'correlation_id', None)
            return {"correlation_id": correlation_id}
        
        self.client = TestClient(self.app)
    
    def test_correlation_id_added_to_response_header(self):
        """Test that correlation ID is added to response header"""
        response = self.client.get("/test")
        
        assert "x-correlation-id" in response.headers
        correlation_id = response.headers["x-correlation-id"]
        assert len(correlation_id) > 0
    
    def test_existing_correlation_id_preserved(self):
        """Test that existing correlation ID from request is preserved"""
        test_correlation_id = "test-correlation-123"
        
        response = self.client.get(
            "/test",
            headers={"X-Correlation-ID": test_correlation_id}
        )
        
        assert response.headers["x-correlation-id"] == test_correlation_id
        
        # Also check it's available in request state
        data = response.json()
        assert data["correlation_id"] == test_correlation_id
    
    def test_correlation_id_generated_when_missing(self):
        """Test that correlation ID is generated when not provided"""
        response = self.client.get("/test")
        
        correlation_id = response.headers["x-correlation-id"]
        assert correlation_id is not None
        assert len(correlation_id) > 0


class TestSecurityAuditMiddleware:
    """Test SecurityAuditMiddleware functionality"""
    
    def setup_method(self):
        """Set up test app with SecurityAuditMiddleware"""
        self.app = FastAPI()
        self.app.add_middleware(SecurityAuditMiddleware)
        
        @self.app.get("/v1/agents")
        async def sensitive_endpoint():
            return {"agents": []}
        
        @self.app.get("/v1/evaluations")
        async def another_sensitive_endpoint():
            return {"evaluations": []}
        
        @self.app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @self.app.get("/v1/agents/error")
        async def error_endpoint():
            raise HTTPException(status_code=400, detail="Test error")
        
        self.client = TestClient(self.app)
    
    @patch("shared.middleware.security.logger")
    def test_sensitive_operations_logged(self, mock_logger):
        """Test that sensitive operations are logged"""
        response = self.client.get("/v1/agents")
        
        # Verify security audit log was called
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0]
        assert "Security audit - sensitive operation" in call_args[0]
    
    @patch("shared.middleware.security.logger")
    def test_multiple_sensitive_paths_logged(self, mock_logger):
        """Test that multiple sensitive paths are logged"""
        sensitive_paths = ["/v1/agents", "/v1/evaluations"]
        
        for path in sensitive_paths:
            mock_logger.reset_mock()
            response = self.client.get(path)
            
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args[0]
            assert "Security audit - sensitive operation" in call_args[0]
    
    @patch("shared.middleware.security.logger")
    def test_public_endpoints_not_logged_as_sensitive(self, mock_logger):
        """Test that public endpoints are not logged as sensitive"""
        response = self.client.get("/public")
        
        # Should not have called info for sensitive operation
        info_calls = [call for call in mock_logger.info.call_args_list 
                     if "sensitive operation" in str(call)]
        assert len(info_calls) == 0
    
    @patch("shared.middleware.security.logger")
    def test_failed_requests_logged(self, mock_logger):
        """Test that failed requests are logged"""
        response = self.client.get("/v1/agents/error")
        
        # Should have logged the failed request
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0]
        assert "Security audit - failed request" in call_args[0]
    
    @patch("shared.middleware.security.logger")
    def test_successful_requests_not_logged_as_failed(self, mock_logger):
        """Test that successful requests are not logged as failed"""
        response = self.client.get("/v1/agents")
        
        # Should not have called warning for failed request
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                        if "failed request" in str(call)]
        assert len(warning_calls) == 0
    
    @patch("shared.middleware.security.logger")
    def test_audit_log_includes_request_details(self, mock_logger):
        """Test that audit logs include relevant request details"""
        response = self.client.get(
            "/v1/agents",
            headers={"User-Agent": "test-agent/1.0"}
        )
        
        # Check that log includes request details
        mock_logger.info.assert_called()
        call_kwargs = mock_logger.info.call_args[1]
        
        assert "method" in call_kwargs
        assert "path" in call_kwargs
        assert "client_ip" in call_kwargs
        assert "user_agent" in call_kwargs
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["path"] == "/v1/agents"
        assert call_kwargs["user_agent"] == "test-agent/1.0"


class TestMiddlewareIntegration:
    """Test middleware integration and interaction"""
    
    def setup_method(self):
        """Set up test app with multiple middleware"""
        self.app = FastAPI()
        
        # Add middleware in order (reverse of execution order)
        self.app.add_middleware(SecurityAuditMiddleware)
        self.app.add_middleware(CorrelationIdMiddleware)
        self.app.add_middleware(SecurityHeadersMiddleware)
        self.app.add_middleware(RequestValidationMiddleware)
        
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        self.client = TestClient(self.app)
    
    def test_all_middleware_applied(self):
        """Test that all middleware is applied correctly"""
        response = self.client.get("/test")
        
        # Security headers should be present
        assert "x-frame-options" in response.headers
        assert "x-content-type-options" in response.headers
        
        # Correlation ID should be present
        assert "x-correlation-id" in response.headers
        
        # Request should be successful (validation passed)
        assert response.status_code == 200
    
    def test_middleware_order_preserved(self):
        """Test that middleware execution order is preserved"""
        # This is more of an integration test
        # The fact that all middleware works together indicates correct ordering
        response = self.client.get("/test")
        assert response.status_code == 200
    
    @patch("shared.middleware.security.logger")
    def test_middleware_logging_integration(self, mock_logger):
        """Test that middleware logging works together"""
        response = self.client.get("/test")
        
        # Should have correlation ID available for logging
        assert "x-correlation-id" in response.headers
        correlation_id = response.headers["x-correlation-id"]
        assert len(correlation_id) > 0