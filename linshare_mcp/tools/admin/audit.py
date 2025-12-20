import requests
from requests.auth import HTTPBasicAuth
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL as LINSHARE_BASE_URL, LINSHARE_USERNAME, LINSHARE_PASSWORD
from ...utils.logging import logger

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
        begin_date: Start date for filtering logs (ISO 8601: YYYY-MM-DD)
        end_date: End date for filtering logs (ISO 8601: YYYY-MM-DD)
        max_results: Maximum number of results to return (default: 50)
    
    Returns:
        Formatted list of audit log entries
    """
    logger.info(f"Tool called: search_user_audit_logs({actor_uuid})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        params = {}
        if action: params["action"] = action
        if entry_type: params["type"] = entry_type
        if force_all: params["forceAll"] = "true"
        if begin_date: params["beginDate"] = begin_date
        if end_date: params["endDate"] = end_date
        
        url = f"{LINSHARE_BASE_URL}/audit/{actor_uuid}"
        
        response = requests.get(
            url,
            params=params,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
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
