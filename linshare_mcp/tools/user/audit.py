import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

from typing import Literal

@mcp.tool()
def user_search_audit(
    action: Literal["CREATE", "UPDATE", "DELETE", "GET", "DOWNLOAD", "SUCCESS", "FAILURE", "CONVERT", "PURGE"] | None = None,
    type: Literal["SHARE_ENTRY", "DOCUMENT_ENTRY", "GUEST", "WORK_SPACE", "WORK_SPACE_MEMBER", "WORK_GROUP", "WORKGROUP_MEMBER", "WORKGROUP_FOLDER", "WORKGROUP_DOCUMENT", "WORKGROUP_DOCUMENT_REVISION", "DOMAIN", "USER", "DOMAIN_PATTERN", "GROUP_FILTER", "WORKSPACE_FILTER", "FUNCTIONALITY", "CONTACTS_LISTS", "CONTACTS_LISTS_CONTACTS", "UPLOAD_REQUEST_GROUP", "UPLOAD_REQUEST", "UPLOAD_REQUEST_URL", "UPLOAD_REQUEST_ENTRY", "UPLOAD_PROPOSITION", "ANONYMOUS_SHARE_ENTRY", "AUTHENTICATION", "USER_PREFERENCE", "RESET_PASSWORD", "SAFE_DETAIL", "PUBLIC_KEY", "JWT_PERMANENT_TOKEN", "SHARED_SPACE_NODE", "MAIL_ATTACHMENT", "SHARED_SPACE_MEMBER", "DRIVE_MEMBER", "DRIVE", "WORKGROUP", "GUEST_MODERATOR"] | None = None,
    force_all: bool = False,
    begin_date: str | None = None,
    end_date: str | None = None
) -> str:
    """[USER API] Search user audit logs (User v5).
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/audit)
    
    Args:
        action: Filter by action
        type: Filter by resource type
        force_all: Force retrieval of all logs (default: False)
        begin_date: Start date (ISO 8601: YYYY-MM-DDTHH:MM:SS.sssZ)
        end_date: End date (ISO 8601: YYYY-MM-DDTHH:MM:SS.sssZ)
        
    Returns:
        Formatted audit logs
    """
    logger.info(f"Tool called: user_search_audit(action={action}, type={type})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."
            
        url = f"{LINSHARE_USER_URL}/audit"
        
        params = {
            "forceAll": str(force_all).lower()
        }
        if action: params["action"] = action
        if type: params["type"] = type
        if begin_date: params["beginDate"] = begin_date
        if end_date: params["endDate"] = end_date
        
        response = requests.get(
            url,
            params=params,
            headers=auth_manager.get_user_header(),
            timeout=10
        )
        response.raise_for_status()
        
        logs = response.json()
        
        if not logs:
            return "No audit logs found matching criteria."
            
        result = f"Audit Logs ({len(logs)} entries):\n\n"
        
        # Determine format based on response structure (list of audit entries)
        for i, log in enumerate(logs, 1):
            timestamp = log.get('creationDate', 'N/A')
            # If timestamp is ms, convert? API usually returns long or ISO. 
            # User example shows ISO in query params, assume response might be formatted or ms.
            # Usually LinShare returns timestamps as long (ms). Let's just print as is or try to format if int.
            
            act = log.get('action', 'UNKNOWN')
            res_type = log.get('type', 'UNKNOWN')
            
            entry_str = f"{i}. [{timestamp}] {act} on {res_type}"
            
            # Additional details
            if 'uuid' in log:
                entry_str += f" (UUID: {log['uuid']})"
                
            result += entry_str + "\n"
            
            # Print select details if available
            details = {k:v for k,v in log.items() if k not in ['uuid', 'creationDate', 'action', 'type']}
            if details:
                 # Flatten a bit for readability
                 import json
                 try:
                     result += f"   Details: {json.dumps(details, ensure_ascii=False)}\n"
                 except:
                     result += f"   Details: {str(details)}\n"
            result += "\n"
            
        return result

    except requests.RequestException as e:
        logger.error(f"Error searching audit: {str(e)}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             try:
                error_msg = f"API Error {e.response.status_code}: {e.response.text}"
             except: pass
        return f"Error searching audit: {error_msg}"
    except Exception as e:
        return f"Error: {str(e)}"
