"""
Unit tests for User tools (auth, users, audit).
Patches config module directly to avoid import-time caching issues.
"""
import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError


class TestUserAuthTools:
    """Tests for tools in user/auth.py."""
    
    @pytest.mark.unit
    def test_user_login_user_success(self):
        """Test successful login tool."""
        with patch("linshare_mcp.tools.user.auth.auth_manager") as mock_auth:
            mock_auth.login.return_value = {
                "firstName": "Test",
                "lastName": "User",
                "mail": "test@test.org",
                "uuid": "uuid-123",
                "role": "USER"
            }
            from linshare_mcp.tools.user.auth import user_login_user
            
            result = user_login_user("test@test.org", "pass")
            
            assert "Login Successful" in result
            assert "Test User" in result
            assert "uuid-123" in result

    @pytest.mark.unit
    def test_user_login_user_failure(self):
        """Test failed login tool."""
        with patch("linshare_mcp.tools.user.auth.auth_manager") as mock_auth:
            mock_auth.login.side_effect = Exception("Invalid credentials")
            from linshare_mcp.tools.user.auth import user_login_user
            
            result = user_login_user("test@test.org", "pass")
            
            assert "Login Failed" in result
            assert "Invalid credentials" in result

    @pytest.mark.unit
    def test_user_logout_user(self):
        """Test logout tool."""
        with patch("linshare_mcp.tools.user.auth.auth_manager") as mock_auth:
            from linshare_mcp.tools.user.auth import user_logout_user
            
            result = user_logout_user()
            
            assert "Logged out successfully" in result
            mock_auth.logout.assert_called_once()

    @pytest.mark.unit
    def test_user_get_current_user_info_logged_in(self):
        """Test get_current_user_info when logged in."""
        with patch("linshare_mcp.tools.user.auth.auth_manager") as mock_auth:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_info.return_value = {
                "firstName": "Amy",
                "lastName": "Wolsh",
                "mail": "amy@test.org",
                "uuid": "amy-uuid",
                "role": "USER"
            }
            from linshare_mcp.tools.user.auth import user_get_current_user_info
            
            result = user_get_current_user_info()
            
            assert "Current User Session" in result
            assert "Amy Wolsh" in result
            assert "amy-uuid" in result

    @pytest.mark.unit
    def test_user_get_current_user_info_logged_out(self):
        """Test get_current_user_info when logged out."""
        with patch("linshare_mcp.tools.user.auth.auth_manager") as mock_auth:
            mock_auth.is_logged_in.return_value = False
            from linshare_mcp.tools.user.auth import user_get_current_user_info
            
            result = user_get_current_user_info()
            
            assert "No user is currently logged in" in result


class TestUserUsersTools:
    """Tests for tools in user/users.py."""
    
    @pytest.mark.unit
    def test_user_search_users_success(self, mock_user_response):
        """Test successful user search."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [mock_user_response]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.users.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.users.auth_manager") as mock_auth:
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.users.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.users import user_search_users
                    
                    result = user_search_users("amy")
                    
                    assert "Found 1 users" in result
                    assert "Amy Wolsh" in result
                    assert "4343bca5" in result

    @pytest.mark.unit
    def test_user_search_users_empty(self):
        """Test user search with no results."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.users.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.users.auth_manager") as mock_auth:
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.users.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.users import user_search_users
                    
                    result = user_search_users("nonexistent")
                    
                    assert "No users found" in result


class TestUserAuditTools:
    """Tests for tools in user/audit.py."""
    
    @pytest.mark.unit
    def test_user_search_audit_success(self, mock_audit_response):
        """Test successful audit search."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_audit_response
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.audit.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.audit.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.audit.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.audit import user_search_audit
                    
                    result = user_search_audit(action="DELETE")
                    
                    assert "Audit Logs" in result
                    assert "DELETE" in result
                    assert "test_document.pdf" in result

    @pytest.mark.unit
    def test_user_search_audit_date_normalization(self, mock_audit_response):
        """Test that dates are normalized correctly in audit tool."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_audit_response
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.audit.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.audit.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.audit.requests.get", return_value=mock_resp) as mock_get:
                    from linshare_mcp.tools.user.audit import user_search_audit
                    
                    user_search_audit(begin_date="2026-01-16")
                    
                    params = mock_get.call_args.kwargs.get("params", {})
                    assert params.get("beginDate") == "2026-01-16T00:00:00.000Z"


class TestUserGuestTools:
    """Tests for tools in user/guests.py."""
    
    @pytest.mark.unit
    def test_list_guests_success(self):
        """Test successful guest listing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"firstName": "Guest", "lastName": "1", "mail": "g1@test.org", "uuid": "g1-uuid"}
        ]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.guests.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.guests.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.guests.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.guests import list_guests
                    
                    result = list_guests()
                    
                    assert "Guests" in result
                    assert "Guest 1" in result

    @pytest.mark.unit
    def test_user_create_guest_success(self):
        """Test successful guest creation."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "firstName": "New", "lastName": "Guest", "mail": "new@test.org", "uuid": "new-uuid"
        }
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.guests.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.guests.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                mock_auth.get_current_user.return_value = {"uuid": "me-uuid", "mail": "me@test.org"}
                with patch("linshare_mcp.tools.user.guests.requests.post", return_value=mock_resp):
                    from linshare_mcp.tools.user.guests import user_create_guest
                    
                    result = user_create_guest("new@test.org", "New", "Guest")
                    
                    assert "Guest created successfully" in result
                    assert "New Guest" in result


class TestUserContactListTools:
    """Tests for tools in user/contact_lists.py."""
    
    @pytest.mark.unit
    def test_user_list_contact_lists_success(self):
        """Test successful contact list listing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"name": "My List", "uuid": "l-uuid"}]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.contact_lists.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.contact_lists.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.contact_lists.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.contact_lists import user_list_contact_lists
                    
                    result = user_list_contact_lists()
                    
                    assert "Contact Lists" in result
                    assert "My List" in result


class TestUserReceivedSharesTools:
    """Tests for tools in user/received_shares.py."""
    
    @pytest.mark.unit
    def test_user_list_my_received_shares_success(self):
        """Test successful received shares listing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"name": "Received File", "uuid": "s-uuid", "size": 1024}]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.received_shares.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.received_shares.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True # Not explicitly used but good practice
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                mock_auth.get_current_user.return_value = {"uuid": "me-uuid"}
                with patch("linshare_mcp.tools.user.received_shares.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.received_shares import user_list_my_received_shares
                    
                    result = user_list_my_received_shares()
                    
                    assert "Received Shares" in result
                    assert "Received File" in result

    @pytest.mark.unit
    def test_user_copy_received_share_success(self):
        """Test successful copying of a received share."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "Copied File", "uuid": "new-doc-uuid"}
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.received_shares.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.received_shares.auth_manager") as mock_auth:
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                mock_auth.get_current_user.return_value = {"uuid": "me-uuid"}
                with patch("linshare_mcp.tools.user.received_shares.requests.post", return_value=mock_resp):
                    from linshare_mcp.tools.user.received_shares import user_copy_received_share_to_my_space
                    
                    result = user_copy_received_share_to_my_space("s-uuid")
                    
                    assert "Share copied to your personal space" in result
                    assert "Copied File" in result
