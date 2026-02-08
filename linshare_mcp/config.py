import os
from pathlib import Path

# LinShare configuration from environment variables
# Support for separate admin (delegation) and user (JWT) URLs
LINSHARE_ADMIN_URL = os.getenv("LINSHARE_ADMIN_URL")
LINSHARE_USER_URL = os.getenv("LINSHARE_USER_URL")

# Backward compatibility and smart fallbacks
LINSHARE_BASE_URL = os.getenv("LINSHARE_BASE_URL")

# 1. If global base URL is set, use it for both
if LINSHARE_BASE_URL:
    if not LINSHARE_ADMIN_URL: LINSHARE_ADMIN_URL = LINSHARE_BASE_URL
    if not LINSHARE_USER_URL: LINSHARE_USER_URL = LINSHARE_BASE_URL

# 2. Smart inferring: If only one is set, try to derive the other
if LINSHARE_ADMIN_URL and not LINSHARE_USER_URL:
    # Try to swap /delegation/v2 for /user/v5
    if "/delegation/v2" in LINSHARE_ADMIN_URL:
        LINSHARE_USER_URL = LINSHARE_ADMIN_URL.replace("/delegation/v2", "/user/v5")
    else:
        LINSHARE_USER_URL = LINSHARE_ADMIN_URL

if LINSHARE_USER_URL and not LINSHARE_ADMIN_URL:
    # Try to swap /user/v5 for /delegation/v2
    if "/user/v5" in LINSHARE_USER_URL:
        LINSHARE_ADMIN_URL = LINSHARE_USER_URL.replace("/user/v5", "/delegation/v2")
    else:
        LINSHARE_ADMIN_URL = LINSHARE_USER_URL

# Service Account credentials (for admin operations)
LINSHARE_USERNAME = os.getenv("LINSHARE_USERNAME")
LINSHARE_PASSWORD = os.getenv("LINSHARE_PASSWORD")

# JWT Token (for user operations) - optional, can be provided instead of using login_user
LINSHARE_JWT_TOKEN = os.getenv("LINSHARE_JWT_TOKEN")

# Directory configurations with sensible defaults
LINSHARE_UPLOAD_DIR = Path(os.getenv('LINSHARE_UPLOAD_DIR', Path.home() / 'LinShareUploads'))
LINSHARE_DOWNLOAD_DIR = Path(os.getenv('LINSHARE_DOWNLOAD_DIR', Path.home() / 'LinShareDownloads'))

# Create directories if they don't exist
LINSHARE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LINSHARE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Common role UUIDs (from LinShare database)
COMMON_ROLES = {
    'WORK_SPACE': {
        'WORK_SPACE_ADMIN': '9e73e962-c233-4b4a-be1c-e8d9547acbdf',
        'WORK_SPACE_WRITER': '963025ca-8220-4915-b4fc-dba7b0b56100',
        'WORK_SPACE_READER': '556404b5-09b0-413e-a025-79ee40e043e4'
    }
}
