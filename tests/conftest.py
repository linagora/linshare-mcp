"""
Pytest fixtures and configuration for LinShare MCP Server tests.
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from requests.auth import HTTPBasicAuth

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load test environment
from dotenv import load_dotenv
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


# --- Fixtures: Authentication ---

@pytest.fixture
def admin_credentials():
    """Return admin credentials from environment."""
    return {
        "username": os.getenv("LINSHARE_USERNAME", "admin@linshare.org"),
        "password": os.getenv("LINSHARE_PASSWORD", "adminpassword")
    }


@pytest.fixture
def admin_auth(admin_credentials):
    """Return HTTPBasicAuth object for admin requests."""
    return HTTPBasicAuth(
        admin_credentials["username"],
        admin_credentials["password"]
    )


@pytest.fixture
def user_jwt():
    """Return a sample JWT token for user requests."""
    return os.getenv("LINSHARE_JWT_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature")


@pytest.fixture
def bearer_header(user_jwt):
    """Return Authorization header with Bearer token."""
    return {"Authorization": f"Bearer {user_jwt}"}


# --- Fixtures: URLs ---

@pytest.fixture
def admin_url():
    """Return LinShare Admin API URL."""
    return os.getenv(
        "LINSHARE_ADMIN_URL",
        "https://user.linshare-6-3-on-commit.integration-linshare.org/linshare/webservice/rest/delegation/v2"
    )


@pytest.fixture
def user_url():
    """Return LinShare User API URL."""
    return os.getenv(
        "LINSHARE_USER_URL",
        "https://user.linshare-6-4-on-commit.integration-linshare.org/linshare/webservice/rest/user/v5"
    )


@pytest.fixture
def mcp_server_url():
    """Return local MCP server URL."""
    return "http://localhost:8000"


# --- Fixtures: Mock Responses ---

@pytest.fixture
def mock_user_response():
    """Return a mock user data response."""
    return {
        "uuid": "4343bca5-dd12-48c3-a43d-50a0b10fbafc",
        "domain": "2547db7a-6606-40d9-8dee-d45fdf75bd38",
        "firstName": "Amy",
        "lastName": "Wolsh",
        "mail": "amy.wolsh@linshare.org",
        "accountType": "INTERNAL",
        "external": False
    }


@pytest.fixture
def mock_audit_response():
    """Return a mock audit log response."""
    return [
        {
            "action": "DELETE",
            "type": "SHARE_ENTRY",
            "creationDate": 1768609800759,
            "resource": {
                "name": "test_document.pdf",
                "uuid": "b0ae0575-0f2b-46ce-9e5b-7b266bc14f98"
            }
        }
    ]


@pytest.fixture
def mock_document_response():
    """Return a mock document data response."""
    return {
        "uuid": "doc-uuid-1234",
        "name": "test_file.txt",
        "size": 1024,
        "type": "text/plain",
        "creationDate": 1768609800000,
        "modificationDate": 1768609800000
    }


# --- Fixtures: Mocked Auth Manager ---

@pytest.fixture
def mock_auth_manager():
    """Return a mocked AuthManager instance."""
    with patch("linshare_mcp.utils.auth.auth_manager") as mock:
        mock.get_admin_auth.return_value = HTTPBasicAuth("admin@test.org", "password")
        mock.get_user_header.return_value = {"Authorization": "Bearer test-token"}
        mock.token = "test-jwt-token"
        mock.user_info = {"mail": "user@test.org", "firstName": "Test"}
        yield mock


# --- Markers ---

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
