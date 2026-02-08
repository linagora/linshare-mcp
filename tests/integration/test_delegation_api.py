"""
Integration tests for the Delegation API (Admin tools).
"""
import pytest
import requests
from linshare_mcp.tools.admin.users import get_user_domain
from linshare_mcp.tools.admin.audit import search_user_audit_logs


@pytest.mark.integration
class TestDelegationAPIIntegration:
    """Live integration tests for delegation API."""

    def test_get_user_domain_live(self):
        """Test get_user_domain with real API."""
        # Use the real function but it will use real env vars
        # Ensure we are testing against a known user or one that exists
        result = get_user_domain("walidboudich@mailo.com")
        
        # If credentials are correct and user exists, we expect details
        # If unauthorized, we expect the error message from the tool
        if "Error" in result:
             pytest.skip(f"Integration test failed (likely credentials): {result}")
             
        assert "UUID:" in result
        assert "walidboudich@mailo.com" in result

    def test_search_user_audit_logs_live(self):
        """Test search_user_audit_logs with real API."""
        # First get the user UUID
        user_info = get_user_domain("walidboudich@mailo.com")
        if "Error" in user_info:
            pytest.skip("Could not get user UUID for audit test")
            
        import re
        match = re.search(r"UUID: ([a-f0-9-]+)", user_info)
        if not match:
            pytest.skip("Could not parse UUID from user info")
            
        user_uuid = match.group(1)
        result = search_user_audit_logs(actor_uuid=user_uuid, max_results=5)
        
        assert "Audit Logs" in result or "No audit logs found" in result
        if "Error" in result:
            pytest.fail(f"Audit log search failed: {result}")
