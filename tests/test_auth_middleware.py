"""
Tests for the AuthMiddleware that protects SSE endpoints.
"""
import pytest
import base64
from unittest.mock import patch, MagicMock, AsyncMock
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def create_test_app(mode="all"):
    """Create a minimal test app with AuthMiddleware."""
    
    async def sse_endpoint(request):
        return PlainTextResponse("SSE OK")
    
    async def messages_endpoint(request):
        return PlainTextResponse("Messages OK")
    
    async def health_endpoint(request):
        return PlainTextResponse("Health OK")
    
    app = Starlette(routes=[
        Route("/sse", sse_endpoint),
        Route("/messages", messages_endpoint),
        Route("/health", health_endpoint),
    ])
    
    # Import and add middleware
    with patch.dict("os.environ", {
        "LINSHARE_USERNAME": "admin@test.org",
        "LINSHARE_PASSWORD": "secret123"
    }):
        from linshare_mcp.main import AuthMiddleware
        app.add_middleware(AuthMiddleware)
    
    return app


class TestBasicAuth:
    """Tests for Basic Authentication."""
    
    @pytest.mark.unit
    def test_valid_basic_auth_accepted(self):
        """Test that valid Basic Auth credentials are accepted."""
        with patch("linshare_mcp.config.LINSHARE_USERNAME", "admin@test.org"):
            with patch("linshare_mcp.config.LINSHARE_PASSWORD", "secret123"):
                app = create_test_app()
                client = TestClient(app)
                
                credentials = base64.b64encode(b"admin@test.org:secret123").decode()
                response = client.get("/sse", headers={"Authorization": f"Basic {credentials}"})
                
                assert response.status_code == 200
    
    @pytest.mark.unit
    def test_invalid_basic_auth_rejected(self):
        """Test that invalid Basic Auth credentials are rejected."""
        with patch("linshare_mcp.config.LINSHARE_USERNAME", "admin@test.org"):
            with patch("linshare_mcp.config.LINSHARE_PASSWORD", "secret123"):
                app = create_test_app()
                client = TestClient(app)
                
                credentials = base64.b64encode(b"wrong@test.org:badpass").decode()
                response = client.get("/sse", headers={"Authorization": f"Basic {credentials}"})
                
                assert response.status_code == 401
    
    @pytest.mark.unit
    def test_malformed_basic_auth_rejected(self):
        """Test that malformed Basic Auth is rejected."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/sse", headers={"Authorization": "Basic not-base64!"})
        
        assert response.status_code == 401


class TestBearerAuth:
    """Tests for Bearer JWT Authentication."""
    
    @pytest.mark.unit
    def test_valid_jwt_accepted(self):
        """Test that a valid JWT (3-part token) is accepted."""
        app = create_test_app()
        client = TestClient(app)
        
        # JWT format: header.payload.signature
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        response = client.get("/sse", headers={"Authorization": f"Bearer {jwt}"})
        
        assert response.status_code == 200
    
    @pytest.mark.unit
    def test_malformed_jwt_rejected(self):
        """Test that a malformed JWT (not 3 parts) is rejected."""
        app = create_test_app()
        client = TestClient(app)
        
        # Invalid: only 2 parts
        bad_jwt = "header.payload"
        response = client.get("/sse", headers={"Authorization": f"Bearer {bad_jwt}"})
        
        assert response.status_code == 401
    
    @pytest.mark.unit
    def test_empty_bearer_rejected(self):
        """Test that empty Bearer token is rejected."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/sse", headers={"Authorization": "Bearer "})
        
        assert response.status_code == 401


class TestMissingAuth:
    """Tests for missing Authorization header."""
    
    @pytest.mark.unit
    def test_missing_header_returns_401(self):
        """Test that requests without Authorization header return 401."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/sse")
        
        assert response.status_code == 401
        assert "Missing Authorization" in response.text or "Unauthorized" in response.text
    
    @pytest.mark.unit
    def test_non_protected_endpoint_allowed(self):
        """Test that non-protected endpoints don't require auth."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
