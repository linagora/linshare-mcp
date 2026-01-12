import requests
from typing import Optional, Dict, Any
from ..config import LINSHARE_USER_URL
from .logging import logger

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
        from ..config import LINSHARE_JWT_TOKEN
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
        """Fetch user info using the current JWT token."""
        if not self.token:
            return
            
        auth_base_norm = self._get_auth_base_url()
        auth_base_orig = LINSHARE_USER_URL.rstrip('/') if LINSHARE_USER_URL else ""
        
        urls_to_try = [auth_base_norm]
        if auth_base_orig and auth_base_orig != auth_base_norm:
            urls_to_try.append(auth_base_orig)
            
        for base in urls_to_try:
            if not base: continue
            url = f"{base}/authentication/authorized"
            try:
                logger.debug(f"Attempting user info fetch at: {url}")
                response = requests.get(
                    url,
                    headers={
                        'Authorization': f'Bearer {self.token}',
                        'accept': 'application/json'
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    self.user_info = response.json()
                    logger.info(f"User info fetched successfully via {base}")
                    return # SUCCESS
                else:
                    logger.debug(f"Fetch failed at {base}: {response.status_code}")
            except Exception as e:
                logger.debug(f"Error at {base}: {e}")
                
        # If we reach here, all attempts failed
        logger.warning("Could not fetch user info from any known endpoint.")
        self.user_info = None

    def logout(self):
        """Clear the stored token."""
        self.token = None
        self.user_info = None
        logger.info("User logged out.")

    def get_token(self) -> Optional[str]:
        """Get the current JWT token."""
        return self.token

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get the current user info, fetching it if missing."""
        if self.token and not self.user_info:
            logger.info("User info missing but token present. Attempting lazy fetch...")
            self._fetch_user_info()
        return self.user_info
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the current user info (alias for get_user_info)."""
        return self.get_user_info()

    def get_user_header(self) -> Dict[str, str]:
        """Get the Authorization header for user JWT requests."""
        if not self.token:
            raise ValueError("User not logged in. Please use the 'login_user' tool first.")
        return {
            'Authorization': f'Bearer {self.token}',
            'accept': 'application/json'
        }

    def get_admin_auth(self) -> Any:
        """Get the HTTPBasicAuth object for admin requests."""
        from ..config import LINSHARE_USERNAME, LINSHARE_PASSWORD
        from requests.auth import HTTPBasicAuth
        
        if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
            raise ValueError("LinShare admin credentials not configured in environment (LINSHARE_USERNAME/PASSWORD).")
            
        return HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD)

    def is_logged_in(self) -> bool:
        return self.token is not None

# Global instance
auth_manager = AuthManager()
