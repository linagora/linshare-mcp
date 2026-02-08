"""
Unit tests for Admin tools (audit, users, myspace, workgroups).
Patches config module directly to avoid import-time caching issues.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestGetUserDomain:
    """Tests for get_user_domain tool."""
    
    @pytest.mark.unit
    def test_formats_response_correctly(self, mock_user_response):
        """Test that get_user_domain formats the response correctly."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_user_response
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.users.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.users.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.users import get_user_domain
                    
                    result = get_user_domain("amy.wolsh@linshare.org")
                    
                    assert "UUID: 4343bca5" in result
                    assert "Amy" in result
                    assert "Wolsh" in result
    
    @pytest.mark.unit
    def test_returns_error_without_url(self):
        """Test that get_user_domain returns error when URL not configured."""
        with patch("linshare_mcp.tools.admin.users.LINSHARE_BASE_URL", None):
            from linshare_mcp.tools.admin.users import get_user_domain
            result = get_user_domain("test@test.org")
            
            assert "Error" in result or "not configured" in result.lower()
    
    @pytest.mark.unit
    def test_handles_404_error(self):
        """Test that get_user_domain handles user not found."""
        from requests.exceptions import HTTPError
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = HTTPError("404 Not Found")
        
        with patch("linshare_mcp.tools.admin.users.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.users.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("linshare_mcp.tools.admin.users.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.users import get_user_domain
                    
                    result = get_user_domain("notfound@test.org")
                    
                    assert "Error" in result


class TestSearchUserAuditLogs:
    """Tests for search_user_audit_logs tool."""
    
    @pytest.mark.unit
    def test_builds_params_correctly(self, mock_audit_response):
        """Test that search_user_audit_logs builds request params correctly."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_audit_response
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.audit.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.audit.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("requests.get", return_value=mock_resp) as mock_get:
                    from linshare_mcp.tools.admin.audit import search_user_audit_logs
                    
                    search_user_audit_logs(
                        actor_uuid="uuid-123",
                        action="DELETE",
                        entry_type="SHARE_ENTRY",
                        begin_date="2026-01-16",
                        end_date="2026-01-17"
                    )
                    
                    # Verify params were passed
                    call_args = mock_get.call_args
                    params = call_args.kwargs.get("params", {})
                    assert params.get("action") == "DELETE"
                    assert params.get("type") == "SHARE_ENTRY"
    
    @pytest.mark.unit
    def test_formats_audit_entries(self, mock_audit_response):
        """Test that audit log entries are formatted correctly."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_audit_response
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.audit.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.audit.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.audit import search_user_audit_logs
                    
                    result = search_user_audit_logs(actor_uuid="uuid-123")
                    
                    assert "DELETE" in result
                    assert "SHARE_ENTRY" in result
                    assert "test_document.pdf" in result
    
    @pytest.mark.unit
    def test_returns_no_logs_message(self):
        """Test message when no audit logs are found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.audit.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.audit.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.audit import search_user_audit_logs
                    
                    result = search_user_audit_logs(actor_uuid="uuid-123")
                    
                    assert "No audit logs found" in result
    
    @pytest.mark.unit
    def test_respects_max_results(self, mock_audit_response):
        """Test that max_results parameter limits output."""
        # Create multiple audit entries
        many_logs = mock_audit_response * 10
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = many_logs
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.audit.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.audit.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.audit import search_user_audit_logs
                    
                    result = search_user_audit_logs(actor_uuid="uuid-123", max_results=3)
                    
                    # Count numbered entries (1., 2., 3., etc.)
                    entry_count = result.count(". [")
                    assert entry_count <= 3


class TestAdminMySpaceTools:
    """Tests for tools in admin/myspace.py."""
    
    @pytest.mark.unit
    def test_list_user_documents_success(self, mock_document_response):
        """Test listing a user's documents."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [mock_document_response]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.myspace.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.myspace.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("linshare_mcp.tools.admin.myspace.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.myspace import list_user_documents
                    
                    result = list_user_documents("user-uuid")
                    
                    assert "Personal Documents" in result
                    assert "test_file.txt" in result


class TestAdminWorkgroupsTools:
    """Tests for tools in admin/workgroups.py."""
    
    @pytest.mark.unit
    def test_list_workgroup_entries_success(self):
        """Test listing workgroup entries."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"name": "WG File", "type": "DOCUMENT", "uuid": "wg-f-uuid", "size": 100}
        ]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.workgroups.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.workgroups.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("linshare_mcp.tools.admin.workgroups.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.workgroups import list_workgroup_entries
                    
                    result = list_workgroup_entries("actor-uuid", "wg-uuid")
                    
                    assert "Workgroup Entries" in result
                    assert "WG File" in result

    @pytest.mark.unit
    def test_list_user_shared_spaces_success(self):
        """Test listing shared spaces for a user."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"node": {"name": "My Workspace", "uuid": "ws-uuid", "nodeType": "WORK_SPACE"}}
        ]
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.admin.workgroups.LINSHARE_BASE_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.admin.workgroups.auth_manager") as mock_auth:
                mock_auth.get_admin_auth.return_value = MagicMock()
                with patch("linshare_mcp.tools.admin.workgroups.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.admin.workgroups import list_user_shared_spaces
                    
                    result = list_user_shared_spaces("actor-uuid")
                    
                    assert "Shared Spaces" in result
                    assert "My Workspace" in result
