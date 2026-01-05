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
    can_upload: bool = True,
    restricted: bool = True,
    comment: str = "",
    expiration_date: str | int | None = None,
    restricted_contacts: list[dict] | None = None,
    restricted_contact_lists: list[dict] | None = None,
    contact_list_view_permissions: dict[str, bool] | None = None
) -> str:
    """[USER API] Create a new guest account with advanced restrictions (contacts and lists).
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/users/{uuid}/guests)
    
    Args:
        email: Guest email address
        first_name: Guest first name
        last_name: Guest last name
        can_upload: Allow guest to upload files (default: True)
        restricted: Restrict guest contacts (default: True)
        comment: Optional description/note for the guest
        expiration_date: Expiration date (millisecond timestamp or ISO date string)
        restricted_contacts: List of extra contacts to share with the guest: [{"firstName": "...", "lastName": "...", "domain": "...", "mail": "..."}]
        restricted_contact_lists: List of contact lists to share: [{"name": "...", "uuid": "..."}]
        contact_list_view_permissions: Permissions for each list: {"list_uuid": false}
    
    Returns:
        Confirmation with guest details
    """
    logger.info(f"Tool called: user_create_guest({email})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        from datetime import datetime, timezone
        
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."

        auth_header = auth_manager.get_user_header()
        current_user = auth_manager.get_current_user()
        
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        url = f"{LINSHARE_USER_URL}/guests"
        # Determine expiration timestamp
        expires = expiration_date
        if isinstance(expires, str):
            try:
                dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                expires = int(dt.timestamp() * 1000)
            except: pass

        payload = {
            "canUpload": can_upload,
            "comment": comment,
            "firstName": first_name,
            "lastName": last_name,
            "mail": email,
            "restricted": restricted
        }
        
        if expires:
            payload["expirationDate"] = expires

        if restricted:
            owner_contact = {
                "firstName": current_user.get('firstName', ''),
                "lastName": current_user.get('lastName', ''),
                "domain": current_user.get('domain', ''),
                "mail": current_user.get('mail', '')
            }
            if restricted_contacts:
                if not any(c.get('mail') == owner_contact['mail'] for c in restricted_contacts):
                    restricted_contacts.insert(0, owner_contact)
            else:
                restricted_contacts = [owner_contact]

        if restricted_contacts:
            payload["restrictedContacts"] = restricted_contacts
            
        if restricted_contact_lists:
            payload["restrictedContactList"] = restricted_contact_lists
            
        if contact_list_view_permissions:
            payload["contactListViewPermissions"] = contact_list_view_permissions
        
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
        
        if guest.get('restrictedContacts'):
            result += f"Restricted Contacts: {len(guest['restrictedContacts'])}\n"
        if guest.get('restrictedContactList'):
            result += f"Restricted Lists: {len(guest['restrictedContactList'])}\n"
            
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error creating guest: {str(e)}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_msg = f"API Error {e.response.status_code}: {e.response.text}"
        return f"Error creating guest: {error_msg}"
    except Exception as e:
        logger.error(f"Error creating guest: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_delete_guest(guest_uuid: str) -> str:
    """[USER API] Delete a guest account.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/guests/{guest_uuid})
    
    Args:
        guest_uuid: UUID of the guest to delete
        
    Returns:
        Confirmation of deletion
    """
    logger.info(f"Tool called: user_delete_guest({guest_uuid})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."

        auth_header = auth_manager.get_user_header()
        
        url = f"{LINSHARE_USER_URL}/guests/{guest_uuid}"
        
        response = requests.delete(
            url,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        return f"✅ Guest ({guest_uuid}) deleted successfully."
        
    except requests.RequestException as e:
        logger.error(f"Error deleting guest: {str(e)}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             try:
                error_msg = f"API Error {e.response.status_code}: {e.response.text}"
             except: pass
        return f"Error deleting guest: {error_msg}"
    except Exception as e:
        logger.error(f"Error deleting guest: {e}")
        return f"Error: {str(e)}"
