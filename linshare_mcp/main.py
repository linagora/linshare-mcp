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

# Conditionally import tool modules based on mode
from .tools import files as common_files
from .resources import files as resource_files

if MODE in ["user", "all"]:
    from .tools.user import auth, myspace, users as user_users, files as user_files
    from .tools.user import received_shares, guests, audit as user_audit, contact_lists
    print(f"📦 Loaded USER tools")

if MODE in ["admin", "all"]:
    from .tools.admin import workgroups as admin_workgroups, users as admin_users
    from .tools.admin import myspace as admin_myspace, audit as admin_audit
    print(f"📦 Loaded ADMIN tools")

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
    print(f"{mode_emoji.get(MODE, '🌐')} LinShare MCP Server starting in {MODE.upper()} mode")
    
    if args.transport == "sse":
        print(f"🔌 Listening on http://{args.host}:{args.port} (SSE)")
        import uvicorn
        # FastMCP creates an ASGI app for SSE transport
        uvicorn.run(mcp.sse_app(), host=args.host, port=args.port)
    else:
        print(f"🔌 Running in STDIO mode")
        mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
