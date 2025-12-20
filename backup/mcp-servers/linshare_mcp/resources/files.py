import base64
from ..app import mcp
from ..config import LINSHARE_UPLOAD_DIR

@mcp.resource("file://upload/{filename}")
def get_upload_file(filename: str) -> str:
    """Read a file from the upload directory."""
    file_path = LINSHARE_UPLOAD_DIR / filename
    
    # Security check
    if not file_path.resolve().is_relative_to(LINSHARE_UPLOAD_DIR.resolve()):
        raise ValueError("Access denied: path outside upload directory")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    return base64.b64encode(content).decode('utf-8')
