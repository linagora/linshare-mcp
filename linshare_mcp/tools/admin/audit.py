import requests
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL as LINSHARE_BASE_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

@mcp.tool()
def search_user_audit_logs(
    actor_uuid: str,
    action: str | None = None,
    entry_type: str | None = None,
    force_all: bool = False,
    begin_date: str | None = None,
    end_date: str | None = None,
    max_results: int = 50
) -> str:
    """Search and filter audit logs for a specific LinShare user.
    
    Args:
        actor_uuid: UUID of the user whose audit logs to retrieve
        action: Filter by action type (CREATE, UPDATE, DELETE, GET, DOWNLOAD, SUCCESS, FAILURE, PURGE)
        entry_type: Filter by entry type (SHARE_ENTRY, DOCUMENT_ENTRY, GUEST, WORK_SPACE, etc.)
        force_all: If true, returns all audit entries for the user (default: false)
        begin_date: Start date for filtering logs (Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
        end_date: End date for filtering logs (Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
        max_results: Maximum number of results to return (default: 50)
    
    Returns:
        Formatted list of audit log entries
    """
    logger.info(f"Tool called: search_user_audit_logs({actor_uuid})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    def normalize_date(d_str):
        if not d_str: return None
        # If it's just YYYY-MM-DD, try to append T00:00:00Z for API compatibility if needed
        # But most LinShare APIs accept YYYY-MM-DD if it's delegation.
        # We'll just ensure it's a string and trimmed.
        return d_str.strip()

    try:
        params = {}
        if action: params["action"] = action
        if entry_type: params["type"] = entry_type
        if force_all: params["forceAll"] = "true"
        if begin_date: params["beginDate"] = normalize_date(begin_date)
        if end_date: params["endDate"] = normalize_date(end_date)
        
        url = f"{LINSHARE_BASE_URL}/audit/{actor_uuid}"
        admin_auth = auth_manager.get_admin_auth()
        
        response = requests.get(
            url,
            params=params,
            auth=admin_auth,
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        logs = response.json()
        if not logs: return "No audit logs found matching the specified criteria."
        
        display_logs = logs[:max_results]
        result = f"Audit Logs for User {actor_uuid} ({len(logs)} total)\n\n"
        
        for i, log in enumerate(display_logs, 1):
            result += f"{i}. [{log.get('action', 'N/A')}] {log.get('type', 'N/A')} | {log.get('creationDate', 'N/A')}\n"
            if 'resource' in log:
                result += f"   Resource: {log['resource'].get('name', 'N/A')} ({log['resource'].get('uuid', 'N/A')})\n"
            result += "\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"
