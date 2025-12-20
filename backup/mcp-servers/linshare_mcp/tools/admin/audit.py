import requests
from requests.auth import HTTPBasicAuth
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL, LINSHARE_USERNAME, LINSHARE_PASSWORD
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
        begin_date: Start date for filtering logs (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        end_date: End date for filtering logs (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        max_results: Maximum number of results to return for readability (default: 50)
    
    Returns:
        Formatted list of audit log entries
    """
    logger.info(f"Tool called: search_user_audit_logs({actor_uuid}, action={action}, type={entry_type})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_BASE_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        # Build query parameters
        params = {}
        if action:
            params["action"] = action
        if entry_type:
            params["type"] = entry_type
        if force_all:
            params["forceAll"] = "true"
        if begin_date:
            params["beginDate"] = begin_date
        if end_date:
            params["endDate"] = end_date
        
        url = f"{LINSHARE_ADMIN_URL}/audit/{actor_uuid}"
        
        response = requests.get(
            url,
            params=params,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        logs = response.json()
        
        if not logs:
            return "No audit logs found matching the specified criteria."
        
        # Limit results for readability
        total_count = len(logs)
        display_logs = logs[:max_results]
        
        # Format the response nicely
        result = f"Audit Logs for User {actor_uuid}"
        if action:
            result += f" | Action: {action}"
        if entry_type:
            result += f" | Type: {entry_type}"
        if begin_date or end_date:
            result += f" | Date Range: {begin_date or 'start'} to {end_date or 'end'}"
        
        result += f"\n({total_count} total"
        if total_count > max_results:
            result += f", showing first {max_results}"
        result += ")\n\n"
        
        for i, log in enumerate(display_logs, 1):
            result += f"{i}. "
            result += f"[{log.get('action', 'N/A')}] "
            result += f"{log.get('type', 'N/A')}"
            
            # Date
            creation_date = log.get('creationDate', 'N/A')
            if creation_date != 'N/A':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
                    creation_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            result += f" | {creation_date}"
            
            # Actor
            if 'actor' in log:
                actor = log['actor']
                actor_name = f"{actor.get('firstName', '')} {actor.get('lastName', '')}".strip()
                if actor_name:
                    result += f" | Actor: {actor_name}"
                if actor.get('mail'):
                    result += f" ({actor['mail']})"
            
            # Resource
            if 'resource' in log:
                resource = log['resource']
                if resource.get('name'):
                    result += f"\n   Resource: {resource['name']}"
                if resource.get('uuid'):
                    result += f" (UUID: {resource['uuid']})"
            
            # Auth user if different from actor
            if 'authUser' in log and log['authUser'] != log.get('actor'):
                auth_user = log['authUser']
                auth_name = f"{auth_user.get('firstName', '')} {auth_user.get('lastName', '')}".strip()
                if auth_name:
                    result += f"\n   Auth User: {auth_name}"
            
            result += "\n\n"
        
        if total_count > max_results:
            result += f"\n... and {total_count - max_results} more entries (use max_results parameter to see more)"
        
        return result
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error searching audit logs: {e}")
        return f"Error retrieving audit logs: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        logger.error(f"Error searching audit logs: {e}")
        return f"Error: {str(e)}"
