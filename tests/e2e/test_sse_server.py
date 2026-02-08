"""
End-to-End tests for the SSE server transport.
"""
import pytest
import base64
import json
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient


@pytest.mark.e2e
class TestSSEServerE2E:
    """End-to-end tests for the SSE server."""

    @pytest.fixture
    def app(self):
        """Setup the real MCP app for E2E testing."""
        # Ensure we are in SSE mode for the app
        with patch("sys.argv", ["main.py", "--transport", "sse"]):
            with patch("linshare_mcp.config.LINSHARE_USERNAME", "admin@test.org"):
                with patch("linshare_mcp.config.LINSHARE_PASSWORD", "secret123"):
                    from linshare_mcp.main import mcp, AuthMiddleware
                    
                    # FastMCP creates an ASGI app for SSE transport
                    app = mcp.sse_app()
                    app.add_middleware(AuthMiddleware)
                    return app

    def test_sse_heartbeat_unauthorized(self, app):
        """Test that SSE endpoint requires authorization."""
        client = TestClient(app)
        response = client.get("/sse")
        assert response.status_code == 401
