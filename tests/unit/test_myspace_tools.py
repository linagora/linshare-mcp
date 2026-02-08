"""
Unit tests for MySpace and MySpace Helpers.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


class TestMySpaceHelpers:
    """Tests for helper functions in user/myspace_helpers.py."""

    @pytest.mark.unit
    def test_calculate_expiration_timestamp_days(self):
        """Test expiration calculation for days."""
        from linshare_mcp.tools.user.myspace_helpers import _calculate_expiration_timestamp
        
        # We need to be careful with 'now' in tests
        ts = _calculate_expiration_timestamp(5, "DAYS")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        expected_ms = now_ms + (5 * 24 * 3600 * 1000)
        
        # Allow 2 seconds difference for execution time
        assert abs(ts - expected_ms) < 2000

    @pytest.mark.unit
    def test_validate_expiration_range_valid(self):
        """Test validation of expiration range (valid case)."""
        from linshare_mcp.tools.user.myspace_helpers import _validate_expiration_range
        
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        target_ms = now_ms + (10 * 24 * 3600 * 1000) # 10 days
        
        config = {
            "minValue": 1, "minUnit": "HOUR",
            "maxValue": 30, "maxUnit": "DAY"
        }
        
        is_valid, msg = _validate_expiration_range(target_ms, config)
        assert is_valid is True
        assert msg == ""

    @pytest.mark.unit
    def test_validate_expiration_range_too_long(self):
        """Test validation of expiration range (too long)."""
        from linshare_mcp.tools.user.myspace_helpers import _validate_expiration_range
        
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        target_ms = now_ms + (40 * 24 * 3600 * 1000) # 40 days
        
        config = {
            "maxValue": 30, "maxUnit": "DAY"
        }
        
        is_valid, msg = _validate_expiration_range(target_ms, config)
        assert is_valid is False
        assert "too long" in msg


class TestMySpaceTools:
    """Tests for tools in user/myspace.py."""

    @pytest.mark.unit
    def test_list_my_documents_success(self, mock_document_response):
        """Test listing personal documents."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [mock_document_response]
        mock_resp.headers = {"X-Total-Count": "1"}
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.myspace.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.myspace.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.myspace.requests.get", return_value=mock_resp):
                    from linshare_mcp.tools.user.myspace import list_my_documents
                    
                    result = list_my_documents()
                    
                    assert "Personal Documents" in result
                    assert "test_file.txt" in result
                    assert "doc-uuid-1234" in result

    @pytest.mark.unit
    def test_share_my_documents_success(self):
        """Test sharing documents."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"uuid": "share-uuid-123"}
        mock_resp.raise_for_status = MagicMock()
        
        with patch("linshare_mcp.tools.user.myspace.LINSHARE_USER_URL", "https://test.com/api"):
            with patch("linshare_mcp.tools.user.myspace.auth_manager") as mock_auth:
                mock_auth.is_logged_in.return_value = True
                mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
                with patch("linshare_mcp.tools.user.myspace.requests.post", return_value=mock_resp):
                    # Mocking helpers to avoid network calls inside them
                    with patch("linshare_mcp.tools.user.myspace._get_share_expiration_policy", return_value=None):
                        from linshare_mcp.tools.user.myspace import share_my_documents
                        
                        result = share_my_documents(
                            document_uuids=["doc-1"],
                            recipient_emails=["recip@test.org"]
                        )
                        
                        assert "Successfully" in result
                        assert "UUID: share-uuid-123" in result
