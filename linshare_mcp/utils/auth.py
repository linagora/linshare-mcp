from typing import Optional, Dict, Any
from contextvars import ContextVar
import requests
from requests.auth import HTTPBasicAuth
from ..utils.logging import logger
from ..config import LINSHARE_USER_URL, LINSHARE_JWT_TOKEN

# ContextVars to store per-request credentials
# Stores either (username, password) tuple or JWT token string
request_auth: ContextVar[Optional[Dict[str, Any]]] = ContextVar("request_auth", default=None)

class AuthManager:
    """Manages user authentication and JWT tokens."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance.token = None
            cls._instance.user_info = None
            cls._instance._load_token_from_config()
        return cls._instance
    
    def _load_token_from_config(self):
        """Load JWT token from environment variable if available."""
        if LINSHARE_JWT_TOKEN:
            self.token = LINSHARE_JWT_TOKEN
            logger.info("JWT token loaded from configuration")
            self._fetch_user_info()
    
    def _get_auth_base_url(self) -> str:
        """Helper to get a version-agnostic auth base URL."""
        if not LINSHARE_USER_URL:
            return ""
        # Strip trailing versions like /v5, /v2, /v5/
        url = LINSHARE_USER_URL.rstrip('/')
        import re
        url = re.sub(r'/v\d+$', '', url)
        return url

    def provision_oidc_token(self, oidc_token: str, id_token: str, cookie_string: str) -> Dict[str, Any]:
        """Validate OIDC session and provision a permanent JWT.
        
        This is a bootstrap method that uses existing browser session data
        to authenticate a headless client with LinShare.
        """
        auth_base = self._get_auth_base_url()
        headers = {
            'Authorization': f'Bearer {oidc_token}',
            'accept': 'application/json',
            'Cookie': cookie_string
        }
        
        # 1. Validate the session
        authorized_url = f"{auth_base}/authentication/authorized"
        logger.info(f"Validating OIDC session at {authorized_url}")
        resp = requests.get(authorized_url, headers=headers, timeout=10)
        resp.raise_for_status()
        self.user_info = resp.json()
        
        # 2. Check for existing MCP JWT or create a new one
        # We try to find a token with a specific description if possible, or just creating a new one
        jwt_url = f"{auth_base}/jwt"
        logger.info(f"Fetching/Creating JWT at {jwt_url}")
        
        # Check existing
        jwt_resp = requests.get(jwt_url, headers=headers, timeout=10)
        tokens = jwt_resp.json() if jwt_resp.status_code == 200 else []
        
        mcp_token = next((t for t in tokens if t.get('description') == "MCP-Server-Token"), None)
        
        if not mcp_token:
            logger.info("No MCP-Server-Token found. Creating a new one.")
            create_resp = requests.post(
                jwt_url, 
                headers=headers,
                json={"description": "MCP-Server-Token", "expiryDate": None}, # Permanent
                timeout=10
            )
            create_resp.raise_for_status()
            mcp_token = create_resp.json()
            
        self.token = mcp_token.get('token')
        logger.info(f"OIDC bootstrap success. New JWT provisioned for {self.user_info.get('mail')}")
        
        return {
            "user": self.user_info,
            "token": self.token
        }

    def login(self, username, password) -> Dict[str, Any]:
        """Authenticate with LinShare and store the JWT token."""
        auth_base_norm = self._get_auth_base_url()
        auth_base_orig = LINSHARE_USER_URL.rstrip('/') if LINSHARE_USER_URL else ""
        
        urls_to_try = [auth_base_norm]
        if auth_base_orig and auth_base_orig != auth_base_norm:
            urls_to_try.append(auth_base_orig)
            
        last_error = None
        for base in urls_to_try:
            if not base: continue
            url = f"{base}/authentication/jwt"
            try:
                logger.debug(f"Attempting login at: {url}")
                response = requests.get(
                    url,
                    auth=(username, password),
                    headers={'accept': 'application/json'},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                self.token = data.get('token')
                self.user_info = data.get('user')
                logger.info(f"User {username} logged in successfully via {base}")
                return self.user_info
            except Exception as e:
                last_error = e
                logger.warning(f"Login failed at {base}: {e}")
                
        raise Exception(f"Login failed: {str(last_error)}")
    
    def _fetch_user_info(self):
        """Lazy fetch user info for the global token."""
        if self.token:
            self.user_info = self._fetch_user_info_for_token(self.token)

    def logout(self):
        """Clear the stored token."""
        self.token = None
        self.user_info = None
        logger.info("User logged out.")

    def get_token(self) -> Optional[str]:
        """Get the current JWT token, prioritizing the request context."""
        current_ctx = request_auth.get()
        if current_ctx and current_ctx.get('type') == 'Bearer':
            return current_ctx.get('token')
        return self.token

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get the current user info, lazy-fetching if missing (handles context)."""
        current_token = self.get_token()
        if current_token:
            # If it's the global token, we might already have user_info
            if current_token == self.token and self.user_info:
                return self.user_info
            
            # For context-based tokens or missing global info, we must fetch
            # Note: We don't cache context-based user info globally to avoid cross-request contamination
            return self._fetch_user_info_for_token(current_token)
        return None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the current user info (alias for get_user_info)."""
        return self.get_user_info()

    def get_user_header(self) -> Dict[str, str]:
        """Get the Authorization header for user JWT requests."""
        # Priority 1: Current request context (from HTTP header)
        current_ctx = request_auth.get()
        if current_ctx and current_ctx.get('type') == 'Bearer':
            return {
                'Authorization': f"Bearer {current_ctx['token']}",
                'accept': 'application/json'
            }

        # Priority 2: Stored/Configured token
        if not self.token:
            raise ValueError("User not logged in. Please use the 'login_user' tool first.")
        return {
            'Authorization': f'Bearer {self.token}',
            'accept': 'application/json'
        }

    def get_admin_auth(self) -> Any:
        """Get the HTTPBasicAuth object for admin requests."""
        # Priority 1: Current request context (from HTTP header)
        current_ctx = request_auth.get()
        if current_ctx and current_ctx.get('type') == 'Basic':
            return current_ctx['auth']

        # Priority 2: Legacy environment variables
        from ..config import LINSHARE_USERNAME, LINSHARE_PASSWORD
        
        if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
            raise ValueError("LinShare admin credentials not configured in environment and none provided in request header.")
            
        return HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD)

    def is_logged_in(self) -> bool:
        """Check if a user is logged in (either via config or request context)."""
        return self.get_token() is not None

    def _fetch_user_info_for_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Internal helper to fetch user info for a specific token without side effects."""
        auth_base_norm = self._get_auth_base_url()
        auth_base_orig = LINSHARE_USER_URL.rstrip('/') if LINSHARE_USER_URL else ""
        
        urls_to_try = [auth_base_norm]
        if auth_base_orig and auth_base_orig != auth_base_norm:
            urls_to_try.append(auth_base_orig)
            
        for base in urls_to_try:
            if not base: continue
            url = f"{base}/authentication/authorized"
            try:
                response = requests.get(
                    url,
                    headers={
                        'Authorization': f'Bearer {token}',
                        'accept': 'application/json'
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
        return None

# Global instance
auth_manager = AuthManager()
