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
from starlette.middleware.trustedhost import TrustedHostMiddleware


class AuthMiddleware:
    """Pure ASGI auth middleware for the /sse and /messages endpoints.

    This is intentionally NOT a Starlette ``BaseHTTPMiddleware``: that base
    class buffers the response and is incompatible with SSE streaming, which
    surfaces as ``AssertionError: Unexpected message: http.response.start``
    and silently drops tool results. A raw ASGI middleware leaves the ``send``
    channel untouched, so the SSE stream flows through unmodified.

    Credentials are stashed in the ``request_auth`` contextvar before the
    request is handled; because the downstream app is awaited in the same
    task, the value propagates to the tool call and stays isolated per request.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") not in ("/sse", "/messages"):
            await self.app(scope, receive, send)
            return

        from .utils.auth import request_auth
        from requests.auth import HTTPBasicAuth

        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers", [])}
        auth_header = headers.get("authorization")

        async def reject(detail: str):
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": detail.encode()})

        if not auth_header:
            logger.warning(f"Auth failed: missing Authorization header for {scope['path']}")
            await reject("Unauthorized: Missing Authorization header")
            return

        # 1. Admin Basic Auth
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
                user, password = decoded.split(":", 1)
                request_auth.set({"type": "Basic", "auth": HTTPBasicAuth(user, password)})
                logger.info(f"Admin auth context set: {user}")
                # Always proceed; let the LinShare API reject bad creds.
                await self.app(scope, receive, send)
                return
            except Exception as e:
                logger.warning(f"Admin auth error: {e}")

        # 2. User JWT (Bearer)
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            if len(token.split(".")) == 3:
                request_auth.set({"type": "Bearer", "token": token})
                logger.info("User auth context set: JWT detected")
                await self.app(scope, receive, send)
                return
            logger.warning("User auth failed: invalid JWT format")

        logger.warning(f"Auth failed: no valid credentials for mode {MODE.upper()}")
        await reject(f"Unauthorized: Invalid credentials for mode {MODE}")

# Conditionally import tool modules based on mode
from .tools import files as common_files
from .resources import files as resource_files

if MODE in ["user", "all"]:
    from .tools.user import auth, myspace, users as user_users, files as user_files
    from .tools.user import received_shares, guests, audit as user_audit, contact_lists
    from .tools.user import shared_spaces as user_shared_spaces
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
