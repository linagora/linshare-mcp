import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Set mode from CLI or environment before importing tools
def get_mode():
    """Get mode from CLI args or environment."""
    # Check environment first (for when imported as module)
    env_mode = os.getenv("LINSHARE_MCP_MODE", "all").lower()
    if env_mode in ["user", "admin", "all"]:
        return env_mode
    return "all"

# Parse args early to get mode
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--mode", default=None, choices=["user", "admin", "all"])
_args, _ = _parser.parse_known_args()
MODE = _args.mode or get_mode()

from .app import mcp
from .utils.logging import logger

# --- Authentication Middleware ---
import base64
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # We only protect SSE related endpoints
        if request.url.path in ["/sse", "/messages"]:
            print(f"🔒 Auth Check: {request.method} {request.url.path}")
            print(f"🔍 DEBUG Headers: {dict(request.headers)}")
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                print(f"🔒 Auth Failed: Missing Authorization header for {request.url.path}")
                return Response("Unauthorized: Missing Authorization header", status_code=401)
            
            from .utils.auth import request_auth
            from requests.auth import HTTPBasicAuth
            
            # 1. Handle Admin Basic Auth
            if auth_header.startswith("Basic "):
                try:
                    encoded = auth_header.split(" ")[1]
                    decoded = base64.b64decode(encoded).decode("utf-8")
                    user, password = decoded.split(":")
                    
                    # Set the context for the current request
                    request_auth.set({
                        'type': 'Basic',
                        'auth': HTTPBasicAuth(user, password)
                    })
                    
                    print(f"🔒 Admin Auth Context Set: {user}")
                    # Note: We now ALWAYS proceed and let the LinShare API call fail if the creds are bad
                    return await call_next(request)
                except Exception as e:
                    print(f"🔒 Admin Auth Error: {e}")

            # 2. Handle User JWT (Bearer)
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                if len(token.split(".")) == 3:
                     request_auth.set({
                         'type': 'Bearer',
                         'token': token
                     })
                     print("🔒 User Auth Context Set: JWT detected")
                     return await call_next(request)
                else:
                    print("🔒 User Auth Failed: Invalid JWT format")

            print(f"🔒 Auth Failed: No valid credentials for mode {MODE.upper()}")
            status_msg = f"Unauthorized: Invalid credentials for mode {MODE}"
            return Response(status_msg, status_code=401)
            
        return await call_next(request)

# Conditionally import tool modules based on mode
from .tools import files as common_files
from .resources import files as resource_files

if MODE in ["user", "all"]:
    from .tools.user import auth, myspace, users as user_users, files as user_files
    from .tools.user import received_shares, guests, audit as user_audit, contact_lists
    logger.info("Loaded USER tools")

if MODE in ["admin", "all"]:
    from .tools.admin import workgroups as admin_workgroups, users as admin_users
    from .tools.admin import myspace as admin_myspace, audit as admin_audit
    logger.info("Loaded ADMIN tools")

def main():
    """Main entry point for the LinShare MCP server."""
    parser = argparse.ArgumentParser(description="LinShare MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], 
                        help="Transport protocol to use")
    parser.add_argument("--host", default="0.0.0.0", 
                        help="Host to bind to (for SSE)")
    parser.add_argument("--port", type=int, default=8000, 
                        help="Port to listen on (for SSE)")
    parser.add_argument("--mode", default="all", choices=["user", "admin", "all"],
                        help="Tool mode: 'user' (personal tools), 'admin' (delegation tools), 'all'")
    
    args = parser.parse_args()
    
    mode_emoji = {"user": "👤", "admin": "🛡️", "all": "🌐"}
    logger.info(f"{mode_emoji.get(MODE, '🌐')} LinShare MCP Server starting in {MODE.upper()} mode")
    
    if args.transport == "sse":
        logger.info(f"🔌 Listening on http://{args.host}:{args.port} (SSE)")
        import uvicorn
        # FastMCP creates an ASGI app for SSE transport
        app = mcp.sse_app()
        # Add TrustedHostMiddleware to allow all hosts (fix for potential 421 Misdirected Request)
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
        app.add_middleware(AuthMiddleware)
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        logger.info("🔌 Running in STDIO mode")
        mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
