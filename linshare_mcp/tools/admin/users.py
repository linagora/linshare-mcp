import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import quote
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL as LINSHARE_BASE_URL, LINSHARE_USERNAME, LINSHARE_PASSWORD
from ...utils.logging import logger

@mcp.tool()
def get_user_domain(email: str) -> str:
    """Get the domain UUID for a LinShare user by their email address.
    
    Args:
        email: The user's email address (e.g., abbey.curry@linshare.org)
    
    Returns:
        JSON string with user information including domain UUID
    """
    logger.info(f"Tool called: get_user_domain({email})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        encoded_email = quote(email, safe='')
        
        url = f"{LINSHARE_BASE_URL}/users/{encoded_email}"
        
        response = requests.get(
            url,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        user_data = response.json()
        
        result = f"""User Information:
- UUID: {user_data.get('uuid')}
- Domain UUID: {user_data.get('domain')}
- Name: {user_data.get('firstName')} {user_data.get('lastName')}
- Email: {user_data.get('mail')}
- Account Type: {user_data.get('accountType')}
- External: {user_data.get('external')}
"""
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error fetching user data: {str(e)}")
        return f"Error fetching user data: {str(e)}"
