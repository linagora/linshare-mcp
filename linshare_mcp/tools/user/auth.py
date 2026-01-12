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
        return "Error: Token exists but user info could not be fetched. This usually means the token is invalid or the LinShare URL is incorrect. Please run 'user_check_config' to diagnose."
        
    result = "Current User Session:\n\n"
    result += f"User: {user_info.get('firstName', '')} {user_info.get('lastName', '')}\n"
    result += f"Email: {user_info.get('mail', '')}\n"
    result += f"UUID: {user_info.get('uuid', '')}\n"
    result += f"Role: {user_info.get('role', '')}\n"
    
    return result
@mcp.tool()
def user_check_config() -> str:
    """[COMMON] Check the server configuration and test authentication.
    
    This tool verifies if the environment variables are set and performs a
    live connectivity test to the LinShare authentication API.
    
    Returns:
        A detailed report of the configuration and connection status.
    """
    import os
    import requests
    from ...config import LINSHARE_USER_URL, LINSHARE_ADMIN_URL, LINSHARE_JWT_TOKEN
    
    auth_base = auth_manager._get_auth_base_url()
    results = ["🔍 LinShare Configuration & Connection Check:\n"]
    
    results.append(f"🌐 USER API URL: {'✅ SET' if LINSHARE_USER_URL else '❌ MISSING'}")
    if LINSHARE_USER_URL:
         results.append(f"   - Raw: {LINSHARE_USER_URL}")
         results.append(f"   - Auth Base (Normalized): {auth_base}")

    if LINSHARE_JWT_TOKEN:
        # Re-trigger fetch to ensure we have latest status
        results.append("\n🔄 Refreshing user session...")
        auth_manager._fetch_user_info()

    if auth_manager.is_logged_in():
        results.append("\n🟢 Current Session: LOGGED IN")
        user = auth_manager.get_user_info()
        if user:
            results.append(f"   - User: {user.get('mail')} ({user.get('firstName')} {user.get('lastName')})")
            results.append(f"   - UUID: {user.get('uuid')}")
        else:
            results.append("   ⚠️ Token is present but User Details are MISSING. (Fetch failed)")
    else:
        results.append("\n🔴 Current Session: NOT LOGGED IN")
        
    # PERFORM LIVE TEST
    if LINSHARE_JWT_TOKEN:
        results.append("\n⚡ Performing Connectivity Test...")
        auth_base_norm = auth_manager._get_auth_base_url()
        auth_base_orig = LINSHARE_USER_URL.rstrip('/') if LINSHARE_USER_URL else ""
        
        urls_to_test = [auth_base_norm]
        if auth_base_orig and auth_base_orig != auth_base_norm:
            urls_to_test.append(auth_base_orig)
            
        for test_base in urls_to_test:
            if not test_base: continue
            test_url = f"{test_base}/authentication/authorized"
            results.append(f"📡 Testing: {test_url}")
            try:
                resp = requests.get(
                    test_url,
                    headers={'Authorization': f'Bearer {LINSHARE_JWT_TOKEN}', 'accept': 'application/json'},
                    timeout=10
                )
                results.append(f"   🔢 Status: {resp.status_code}")
                if resp.status_code == 200:
                    results.append("   ✅ SUCCESS: This endpoint works!")
                elif resp.status_code == 401:
                    results.append("   ❌ FAILED: 401 Unauthorized (Invalid Token)")
                elif resp.status_code == 404:
                    results.append("   ❌ FAILED: 404 Not Found")
                else:
                    results.append(f"   ⚠️ Warning: Received status {resp.status_code}")
            except Exception as e:
                results.append(f"   ❌ Error: {str(e)}")

    return "\n".join(results)
