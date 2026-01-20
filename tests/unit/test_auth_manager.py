"""
Unit tests for AuthManager class.
Patches config module directly to avoid import-time caching issues.
"""
import pytest
from unittest.mock import patch, MagicMock
from requests.auth import HTTPBasicAuth


class TestAuthManagerGetAdminAuth:
    """Tests for get_admin_auth method."""
    
    @pytest.mark.unit
    def test_returns_basic_auth_with_credentials(self):
        """Test that get_admin_auth returns HTTPBasicAuth when credentials are set."""
        with patch("linshare_mcp.config.LINSHARE_USERNAME", "admin@test.org"):
            with patch("linshare_mcp.config.LINSHARE_PASSWORD", "secret123"):
                from linshare_mcp.utils.auth import AuthManager
                manager = AuthManager.__new__(AuthManager)
                manager.token = None
                manager.user_info = None
                
                auth = manager.get_admin_auth()
                
                assert isinstance(auth, HTTPBasicAuth)
                assert auth.username == "admin@test.org"
                assert auth.password == "secret123"
    
    @pytest.mark.unit
    def test_raises_without_username(self):
        """Test that get_admin_auth raises when username is missing."""
        with patch("linshare_mcp.config.LINSHARE_USERNAME", None):
            with patch("linshare_mcp.config.LINSHARE_PASSWORD", "secret"):
                from linshare_mcp.utils.auth import AuthManager
                manager = AuthManager.__new__(AuthManager)
                manager.token = None
                manager.user_info = None
                
                with pytest.raises(ValueError, match="admin credentials not configured"):
                    manager.get_admin_auth()
    
    @pytest.mark.unit
    def test_raises_without_password(self):
        """Test that get_admin_auth raises when password is missing."""
        with patch("linshare_mcp.config.LINSHARE_USERNAME", "admin@test.org"):
            with patch("linshare_mcp.config.LINSHARE_PASSWORD", None):
                from linshare_mcp.utils.auth import AuthManager
                manager = AuthManager.__new__(AuthManager)
                manager.token = None
                manager.user_info = None
                
                with pytest.raises(ValueError, match="admin credentials not configured"):
                    manager.get_admin_auth()


class TestAuthManagerUserHeader:
    """Tests for get_user_header method."""
    
    @pytest.mark.unit
    def test_returns_bearer_header_when_logged_in(self):
        """Test that get_user_header returns correct Authorization header."""
        from linshare_mcp.utils.auth import AuthManager
        manager = AuthManager.__new__(AuthManager)
        manager.token = "test-jwt-token-12345"
        manager.user_info = {"mail": "user@test.org"}
        
        header = manager.get_user_header()
        
        assert header["Authorization"] == "Bearer test-jwt-token-12345"
        assert header["accept"] == "application/json"
    
    @pytest.mark.unit
    def test_raises_when_not_logged_in(self):
        """Test that get_user_header raises when no token is set."""
        from linshare_mcp.utils.auth import AuthManager
        manager = AuthManager.__new__(AuthManager)
        manager.token = None
        manager.user_info = None
        
        with pytest.raises(ValueError, match="not logged in"):
            manager.get_user_header()


class TestAuthManagerLogin:
    """Tests for login method."""
    
    @pytest.mark.unit
    def test_login_stores_token_on_success(self):
        """Test that login stores the JWT token on successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "received-jwt-token",
            "user": {"mail": "user@test.org", "firstName": "Test"}
        }
        mock_response.raise_for_status = MagicMock()
        
        # Patch at the module where it's imported
        with patch("linshare_mcp.utils.auth.requests.get", return_value=mock_response):
            with patch("linshare_mcp.utils.auth.LINSHARE_USER_URL", "https://test.com/api/v5"):
                from linshare_mcp.utils.auth import AuthManager
                manager = AuthManager.__new__(AuthManager)
                manager.token = None
                manager.user_info = None
                
                result = manager.login("user@test.org", "password123")
                
                assert manager.token == "received-jwt-token"
                assert result["mail"] == "user@test.org"
    
    @pytest.mark.unit
    def test_login_raises_on_failure(self):
        """Test that login raises exception on authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        
        with patch("requests.get", return_value=mock_response):
            with patch("linshare_mcp.config.LINSHARE_USER_URL", "https://test.com/api/v5"):
                from linshare_mcp.utils.auth import AuthManager
                manager = AuthManager.__new__(AuthManager)
                manager.token = None
                manager.user_info = None
                
                with pytest.raises(Exception, match="Login failed"):
                    manager.login("wrong@test.org", "badpassword")
