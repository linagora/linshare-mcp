"""
Unit tests for common tools: files.py.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestCommonTools:
    """Tests for tools in tools/files.py."""
    
    @pytest.mark.unit
    def test_list_upload_files_empty(self, tmp_path):
        """Test listing upload files when directory is empty."""
        with patch("linshare_mcp.tools.files.LINSHARE_UPLOAD_DIR", tmp_path):
            from linshare_mcp.tools.files import list_upload_files
            
            result = list_upload_files()
            
            assert "No files found" in result

    @pytest.mark.unit
    def test_list_upload_files_with_content(self, tmp_path):
        """Test listing upload files when directory has files."""
        # Create a dummy file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        
        with patch("linshare_mcp.tools.files.LINSHARE_UPLOAD_DIR", tmp_path):
            from linshare_mcp.tools.files import list_upload_files
            
            result = list_upload_files()
            
            assert "Files in Upload Directory" in result
            assert "test.txt" in result

    @pytest.mark.unit
    def test_get_directory_info(self, tmp_path):
        """Test get_directory_info."""
        upload_dir = tmp_path / "upload"
        upload_dir.mkdir()
        download_dir = tmp_path / "download"
        # don't create download_dir to test negative case
        
        with patch("linshare_mcp.tools.files.LINSHARE_UPLOAD_DIR", upload_dir):
            with patch("linshare_mcp.config.LINSHARE_DOWNLOAD_DIR", download_dir):
                from linshare_mcp.tools.files import get_directory_info
                
                result = get_directory_info()
                
                assert "Upload Directory" in result
                assert "Exists" in result
                assert "Not found" in result # for download_dir
