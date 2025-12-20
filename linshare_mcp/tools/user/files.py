import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL, LINSHARE_DOWNLOAD_DIR
from ...utils.logging import logger
from ...utils.auth import auth_manager

# ------------------------------------------------------------------------------
# USER FILES TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def user_download_document(document_uuid: str, filename: str | None = None) -> str:
    """Download a document from LinShare to the download directory.
    
    Args:
        document_uuid: UUID of the document to download
        filename: Optional filename to save as (defaults to original name)
    
    Returns:
        Confirmation of download
    """
    # Placeholder for file operations
    # TODO: Implement download logic using JWT auth
    return "Feature coming soon: Download document"
