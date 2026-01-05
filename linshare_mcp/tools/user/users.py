import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

# ------------------------------------------------------------------------------
# USER USERS TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def user_search_users(pattern: str) -> str:
    """Search for other users (e.g. for sharing).
    
    Note: If a user is not found here, you can still share with their email 
    using 'share_my_documents' - it will be treated as an anonymous share.

    Args:
        pattern: Search string (email, name)
    
    Returns:
        List of matching users
    """
    logger.info(f"Tool called: search_users({pattern})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_user_header()
        
        url = f"{LINSHARE_USER_URL}/users"
        params = {'pattern': pattern}
        
        response = requests.get(
            url,
            params=params,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        users = response.json()
        
        if not users:
            return "No users found."
            
        result = f"Found {len(users)} users:\n\n"
        for u in users:
            result += f"- {u.get('firstName', '')} {u.get('lastName', '')} ({u.get('mail')})\n"
            result += f"  UUID: {u.get('uuid')}\n"
            
        return result
        
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return f"Error: {str(e)}"
