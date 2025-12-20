from ...app import mcp
from ...utils.auth import auth_manager
from ...utils.logging import logger

@mcp.tool()
def user_login_user(username: str, password: str) -> str:
    """Authenticate with LinShare using username and password.
    
    This is required before using any tools that act on behalf of a user
    (e.g., listing personal documents, sharing files).
    
    Args:
        username: The user's email address
        password: The user's password
    
    Returns:
        Confirmation of successful login with user details.
    """
    logger.info(f"Tool called: login_user({username})")
    
    try:
        user_info = auth_manager.login(username, password)
        
        result = f"✅ Login Successful!\n\n"
        result += f"User: {user_info.get('firstName', '')} {user_info.get('lastName', '')}\n"
        result += f"Email: {user_info.get('mail', '')}\n"
        result += f"UUID: {user_info.get('uuid', '')}\n"
        result += f"Role: {user_info.get('role', '')}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return f"❌ Login Failed: {str(e)}"

@mcp.tool()
def user_logout_user() -> str:
    """Log out the current user and clear the session.
    
    Returns:
        Logout confirmation.
    """
    logger.info("Tool called: logout_user()")
    auth_manager.logout()
    return "✅ Logged out successfully."

@mcp.tool()
def user_get_current_user_info() -> str:
    """Get information about the currently logged-in user.
    
    Returns:
        User details or a message indicating no user is logged in.
    """
    logger.info("Tool called: get_current_user_info()")
    
    if not auth_manager.is_logged_in():
        return "No user is currently logged in."
    
    user_info = auth_manager.get_user_info()
    if not user_info:
        return "Error: Token exists but user info is missing."
        
    result = "Current User Session:\n\n"
    result += f"User: {user_info.get('firstName', '')} {user_info.get('lastName', '')}\n"
    result += f"Email: {user_info.get('mail', '')}\n"
    result += f"UUID: {user_info.get('uuid', '')}\n"
    result += f"Role: {user_info.get('role', '')}\n"
    
    return result
