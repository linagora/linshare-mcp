import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

# ------------------------------------------------------------------------------
# USER AUDIT TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def view_my_audit_logs(
    action: str | None = None,
    entry_type: str | None = None,
    begin_date: str | None = None,
    end_date: str | None = None,
    max_results: int = 50
) -> str:
    """View your own audit logs.
    
    Args:
        action: Filter by action type (CREATE, UPDATE, DELETE, GET, DOWNLOAD, etc.)
        entry_type: Filter by entry type (SHARE_ENTRY, DOCUMENT_ENTRY, etc.)
        begin_date: Start date (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        end_date: End date (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        max_results: Maximum number of results (default: 50)
    
    Returns:
        Formatted list of audit log entries
    """
    logger.info(f"Tool called: view_my_audit_logs(action={action}, type={entry_type})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        
        # Build query parameters
        params = {}
        if action:
            params["action"] = action
        if entry_type:
            params["type"] = entry_type
        if begin_date:
            params["beginDate"] = begin_date
        if end_date:
            params["endDate"] = end_date
        
        url = f"{LINSHARE_USER_URL}/audit/{user_uuid}"
        
        response = requests.get(
            url,
            params=params,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        logs = response.json()
        
        if not logs:
            return "No audit logs found."
        
        # Limit results
        total_count = len(logs)
        display_logs = logs[:max_results]
        
        result = f"My Audit Logs"
        if action:
            result += f" | Action: {action}"
        if entry_type:
            result += f" | Type: {entry_type}"
        
        result += f"\n({total_count} total"
        if total_count > max_results:
            result += f", showing first {max_results}"
        result += ")\n\n"
        
        for i, log in enumerate(display_logs, 1):
            result += f"{i}. [{log.get('action', 'N/A')}] {log.get('type', 'N/A')}\n"
            
            if log.get('creationDate'):
                result += f"   Date: {log['creationDate']}\n"
            
            if log.get('resource'):
                resource = log['resource']
                if resource.get('name'):
                    result += f"   Resource: {resource['name']}\n"
            
            result += "\n"
        
        if total_count > max_results:
            result += f"\n... and {total_count - max_results} more entries\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error viewing audit logs: {e}")
        return f"Error: {str(e)}"
