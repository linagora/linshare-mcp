import requests
from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.logging import logger
from ...utils.auth import auth_manager

# ------------------------------------------------------------------------------
# GUESTS TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def list_guests(role: str | None = None) -> str:
    """[USER API] List guests with optional role-based filtering.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoints:
      - All guests: /guests
      - My guests: /guests?role=ALL
      - My moderators: /guests?role=SIMPLE
      - My administrators: /guests?role=ADMIN
    
    Args:
        role: Optional filter: "ALL", "SIMPLE", or "ADMIN". If not provided, lists all guests.
    
    Returns:
        Formatted list of guests with details
    """
    logger.info(f"Tool called: list_guests(role={role})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        # Ensure user is logged in (loads from config automatically)
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."

        auth_header = auth_manager.get_user_header()
        
        # Base URL /guests for user API v5
        url = f"{LINSHARE_USER_URL}/guests"
        params = {}
        if role:
            params["role"] = role
        
        response = requests.get(
            url,
            headers=auth_header,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        guests = response.json()
        
        if not guests:
            return f"No guests found{f' with role: {role}' if role else ''}."
            
        result = f"Guests ({f'Role: {role}, ' if role else 'All, '}{len(guests)} total):\n\n"
        
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
def user_create_guest(
    email: str,
    first_name: str,
    last_name: str,
    can_upload: bool = False,
    expiration_date: str | None = None
) -> str:
    """[USER API] Create a new guest account.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5
    
    Args:
        email: Guest email address
        first_name: Guest first name
        last_name: Guest last name
        can_upload: Allow guest to upload files (default: False)
        expiration_date: Expiration date in ISO format (optional)
    
    Returns:
        Confirmation with guest details
    """
    logger.info(f"Tool called: user_create_guest({email})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."

        auth_header = auth_manager.get_user_header()
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
