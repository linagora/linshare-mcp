from ..app import mcp
from ..config import LINSHARE_UPLOAD_DIR
from ..utils.logging import logger
from ..utils.common import format_file_size, guess_mime_type

@mcp.tool()
def list_upload_files() -> str:
    """[SERVER SIDE] List local files on the remote server's disk available for pick-up.
    
    ⚠️ IMPORTANT: Use this ONLY if the user wants to upload a file already residing on the server.
    If the user has attached a file to the chat, it is automatically handled by the system 
    and you should check for 'BACKGROUND ACTION' history messages for its UUID instead.
    
    Returns:
        Formatted list of files on the server's disk
    """
    logger.info("Tool called: list_upload_files()")
    
    files = [f for f in LINSHARE_UPLOAD_DIR.glob("*") if f.is_file()]
    
    if not files:
        return f"No files found in upload directory: {LINSHARE_UPLOAD_DIR}\n\nPlace files there to upload them."
    
    result = f"📁 Files in Upload Directory ({len(files)} files):\n"
    result += f"Location: {LINSHARE_UPLOAD_DIR}\n\n"
    
    for i, file_path in enumerate(files, 1):
        result += f"{i}. {file_path.name}\n"
        result += f"   Size: {format_file_size(file_path.stat().st_size)}\n"
        result += f"   Type: {guess_mime_type(file_path.name)}\n\n"
    
    return result

@mcp.tool()
def get_directory_info() -> str:
    """Get information about upload and download directory configuration.
    
    Returns:
        Directory paths and status
    """
    from ..config import LINSHARE_DOWNLOAD_DIR
    
    upload_exists = LINSHARE_UPLOAD_DIR.exists()
    download_exists = LINSHARE_DOWNLOAD_DIR.exists()
    
    result = "📁 LinShare Directory Configuration:\n\n"
    result += f"Upload Directory: {LINSHARE_UPLOAD_DIR}\n"
    result += f"  Status: {'✅ Exists' if upload_exists else '❌ Not found'}\n"
    
    if upload_exists:
        files = [f for f in LINSHARE_UPLOAD_DIR.glob("*") if f.is_file()]
        result += f"  Files ready: {len(files)}\n"
    
    result += f"\nDownload Directory: {LINSHARE_DOWNLOAD_DIR}\n"
    result += f"  Status: {'✅ Exists' if download_exists else '❌ Not found'}\n"
    
    if download_exists:
        files = [f for f in LINSHARE_DOWNLOAD_DIR.glob("*") if f.is_file()]
        result += f"  Downloaded files: {len(files)}\n"
    
    return result
