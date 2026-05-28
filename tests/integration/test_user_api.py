"""
Integration tests for the User API.
"""
import pytest
import requests
from linshare_mcp.tools.user.myspace import user_list_documents
from linshare_mcp.tools.user.auth import user_get_current_user_info


@pytest.mark.integration
class TestUserAPIIntegration:
    """Live integration tests for user API."""

    def test_get_current_user_info_live(self):
        """Test getting current user info with real JWT."""
        result = user_get_current_user_info()
        
        if "No user is currently logged in" in result:
            pytest.skip("No LINSHARE_JWT_TOKEN configured for integration tests")
            
        assert "Current User Session" in result
        assert "Email:" in result

    def test_list_my_documents_live(self):
        """Test listing documents with real JWT."""
        result = user_list_documents(limit=5)
        
        if "Error" in result and "logged in" in result.lower():
            pytest.skip("No LINSHARE_JWT_TOKEN configured for integration tests")
            
        assert "Personal Documents" in result or "No documents found" in result
        if "Error" in result:
            pytest.fail(f"List documents failed: {result}")
