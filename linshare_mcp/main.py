import argparse
from .app import mcp
# Import all modules to register tools and resources
from .tools import files as common_files
from .tools.admin import workgroups as admin_workgroups, users as admin_users, myspace as admin_myspace, audit as admin_audit
from .tools.user import auth, myspace, users as user_users, files as user_files, received_shares, guests, audit as user_audit, contact_lists
from .resources import files as resource_files

def main():
    """Main entry point for the LinShare MCP server."""
    parser = argparse.ArgumentParser(description="LinShare MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="Transport protocol to use")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (for SSE)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (for SSE)")
    
    args = parser.parse_args()
    
    if args.transport == "sse":
        print(f"Starting LinShare MCP Server on http://{args.host}:{args.port} (SSE)")
        # FastMCP's run method handles the uvicorn server for SSE
        mcp.run(transport="sse", encoding="utf-8")
    else:
        # Default to stdio
        mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
