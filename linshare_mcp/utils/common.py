import mimetypes
from typing import Optional
from ..config import COMMON_ROLES

def guess_mime_type(filename: str) -> str:
    """Guess MIME type based on file extension."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def get_role_uuid(role_name: str) -> Optional[str]:
    """Get role UUID by name from COMMON_ROLES."""
    role_name_upper = role_name.upper().strip()

    # Look inside WORK_SPACE
    if 'WORK_SPACE' in COMMON_ROLES and role_name_upper in COMMON_ROLES['WORK_SPACE']:
        return COMMON_ROLES['WORK_SPACE'][role_name_upper]

    return None
