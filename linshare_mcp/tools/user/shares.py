import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager
from ...utils.common import format_file_size

# ------------------------------------------------------------------------------
# USER SHARES TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def user_list_my_received_shares() -> str:
    """List all shares received by the logged-in user.
    
    Returns:
        List of received shares with details
    """
    logger.info("Tool called: list_my_received_shares()")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        url = f"{LINSHARE_USER_URL}/{user_uuid}/received_shares"
        
        response = requests.get(
            url,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        shares = response.json()
        
        if not shares:
            return "No received shares found."
            
        result = f"Received Shares ({len(shares)} total):\n\n"
        
        for i, share in enumerate(shares, 1):
            result += f"{i}. {share.get('name', 'Unnamed')}\n"
            result += f"   UUID: {share.get('uuid')}\n"
            result += f"   Size: {format_file_size(share.get('size', 0))}\n"
            result += f"   Type: {share.get('type', 'N/A')}\n"
            
            if share.get('sender'):
                sender = share['sender']
                sender_name = f"{sender.get('firstName', '')} {sender.get('lastName', '')}".strip()
                if sender_name:
                    result += f"   From: {sender_name}"
                if sender.get('mail'):
                    result += f" ({sender['mail']})"
                result += "\n"
            
            if share.get('creationDate'):
                result += f"   Shared: {share['creationDate']}\n"
            if share.get('expirationDate'):
                result += f"   Expires: {share['expirationDate']}\n"
            
            result += f"   Downloaded: {share.get('downloaded', 0)} times\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing received shares: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_copy_received_share_to_my_space(share_uuid: str) -> str:
    """Copy a received share to your personal space.
    
    Args:
        share_uuid: UUID of the received share
    
    Returns:
        Confirmation of copy
    """
    logger.info(f"Tool called: copy_received_share_to_my_space({share_uuid})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        url = f"{LINSHARE_USER_URL}/{user_uuid}/received_shares/{share_uuid}/copy"
        
        response = requests.post(
            url,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        doc = response.json()
        
        return f"✅ Share copied to your personal space!\n\nDocument: {doc.get('name')}\nUUID: {doc.get('uuid')}"
        
    except Exception as e:
        logger.error(f"Error copying share: {e}")
        return f"Error: {str(e)}"
