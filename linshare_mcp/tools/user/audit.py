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
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> str:
    """[USER API] Search user audit logs (User v5).
    
    Arg 'begin_date' and 'end_date' are normalized to strict ISO 8601 (YYYY-MM-DDTHH:MM:SS.sssZ).
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/audit)
    
    Args:
        action: Filter by action
        type: Filter by resource type
        force_all: Force retrieval of all logs (default: False)
        begin_date: Start date (ISO 8601)
        end_date: End date (ISO 8601)
        limit: Max entries to return (default: 100)
        offset: Offset for pagination (default: 0)
    """
    logger.info(f"Tool called: user_search_audit(action={action}, type={type}, limit={limit})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."
            
        url = f"{LINSHARE_USER_URL}/audit"
        
        # ✂️ Aggressive Date Normalization
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        today_str = now_utc.strftime("%Y-%m-%d")

        def normalize_date_strict(d: str, end_of_day: bool = False) -> str | None:
            if not d: return d
            
            logger.debug(f"Aggressively normalizing: {d}")
            try:
                # 1. Try to extract YYYY-MM-DD
                import re
                match = re.search(r"(\d{4}-\d{2}-\d{2})", d)
                if match:
                    base_date = match.group(1)
                    # If it's today and we want end_of_day, omit to use server "now"
                    if base_date == today_str and end_of_day:
                        return None
                        
                    suffix = "T23:59:59.999Z" if end_of_day else "T00:00:00.000Z"
                    return base_date + suffix
                
                # 2. Fallback: Parse anything else and re-emit strict
                clean_d = d.replace('Z', '').replace(' ', 'T')
                dt = datetime.fromisoformat(clean_d.split('+')[0].split('.')[0]) # Simplify
                if dt.year < 1970: return d # Too old
                
                if dt > now_utc and end_of_day:
                    return None
                    
                return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            except Exception as e:
                logger.warning(f"Strict normalization failed for {d}: {e}")
                return d # Return as is if we can't improve it

        begin_date = normalize_date_strict(begin_date)
        end_date = normalize_date_strict(end_date, end_of_day=True)
        
        params = {
            "forceAll": str(force_all).lower(),
            "limit": limit,
            "offset": offset
        }
        if action: params["action"] = action
        if type: params["type"] = type
        if begin_date: params["beginDate"] = begin_date
        if end_date: params["endDate"] = end_date
        
        logger.info(f"Sending Audit Request: {url} with params {params}")
        
        response = requests.get(
            url,
            params=params,
            headers=auth_manager.get_user_header(),
            timeout=15
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
