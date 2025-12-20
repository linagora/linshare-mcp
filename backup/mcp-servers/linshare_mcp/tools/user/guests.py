import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

# ------------------------------------------------------------------------------
# USER GUESTS TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def list_my_guests() -> str:
    """List all guests created by the logged-in user.
    
    Returns:
        List of guests with details
    """
    logger.info("Tool called: list_my_guests()")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        url = f"{LINSHARE_USER_URL}/{user_uuid}/guests"
        
        response = requests.get(
            url,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        guests = response.json()
        
        if not guests:
            return "No guests found."
            
        result = f"My Guests ({len(guests)} total):\n\n"
        
        for i, guest in enumerate(guests, 1):
            result += f"{i}. {guest.get('firstName', '')} {guest.get('lastName', '')}\n"
            result += f"   Email: {guest.get('mail')}\n"
            result += f"   UUID: {guest.get('uuid')}\n"
            result += f"   Can Upload: {guest.get('canUpload', False)}\n"
            result += f"   Restricted: {guest.get('restricted', False)}\n"
            
            if guest.get('expirationDate'):
                result += f"   Expires: {guest['expirationDate']}\n"
            
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing guests: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def create_guest(
    email: str,
    first_name: str,
    last_name: str,
    can_upload: bool = False,
    expiration_date: str | None = None
) -> str:
    """Create a new guest account.
    
    Args:
        email: Guest email address
        first_name: Guest first name
        last_name: Guest last name
        can_upload: Allow guest to upload files (default: False)
        expiration_date: Expiration date in ISO format (optional)
    
    Returns:
        Confirmation with guest details
    """
    logger.info(f"Tool called: create_guest({email})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        url = f"{LINSHARE_USER_URL}/{user_uuid}/guests"
        
        payload = {
            "mail": email,
            "firstName": first_name,
            "lastName": last_name,
            "canUpload": can_upload
        }
        
        if expiration_date:
            payload["expirationDate"] = expiration_date
        
        response = requests.post(
            url,
            json=payload,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        guest = response.json()
        
        result = f"✅ Guest created successfully!\n\n"
        result += f"Name: {guest.get('firstName')} {guest.get('lastName')}\n"
        result += f"Email: {guest.get('mail')}\n"
        result += f"UUID: {guest.get('uuid')}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating guest: {e}")
        return f"Error: {str(e)}"
