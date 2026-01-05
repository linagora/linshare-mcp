import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

# ------------------------------------------------------------------------------
# CONTACT LISTS TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def user_list_contact_lists(mine: bool = True) -> str:
    """[USER API] List contact lists.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/contact_lists)
    
    Args:
        mine: If true, lists your own contact lists (?mine=true). If false, lists all available lists (?mine=false).
    
    Returns:
        Formatted list of contact lists
    """
    logger.info(f"Tool called: user_list_contact_lists(mine={mine})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."

        auth_header = auth_manager.get_user_header()
        
        url = f"{LINSHARE_USER_URL}/contact_lists"
        params = {"mine": "true" if mine else "false"}
        
        response = requests.get(
            url,
            headers=auth_header,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        lists = response.json()
        
        if not lists:
            return f"No contact lists found ({'mine' if mine else 'all'})."
            
        result = f"Contact Lists ({'Mine' if mine else 'All'}, {len(lists)} total):\n\n"
        
        for i, lst in enumerate(lists, 1):
            result += f"{i}. {lst.get('name', 'Unnamed List')}\n"
            result += f"   UUID: {lst.get('uuid')}\n"
            if lst.get('comment'):
                result += f"   Comment: {lst['comment']}\n"
            if lst.get('creationDate'):
                result += f"   Created: {lst['creationDate']}\n"
            result += "\n"
            
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error listing contact lists: {str(e)}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_msg = f"API Error {e.response.status_code}: {e.response.text}"
        return f"Error listing contact lists: {error_msg}"
    except Exception as e:
        logger.error(f"Error listing contact lists: {e}")
        return f"Error: {str(e)}"
