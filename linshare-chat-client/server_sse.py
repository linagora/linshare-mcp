
import os
from pathlib import Path
from dotenv import load_dotenv

# Load API Keys relative to script
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from linshare_mcp.main import mcp

# Expose the Starlette/FastAPI app for Uvicorn
# FastMCP doesn't expose the 'app' property directly in all versions, 
# but usually `mcp._sse_app` or similar if mounting manually.
# However, the easiest way with modern FastMCP is often just:
# `fastmcp run linshare_mcp.main:mcp --transport sse`
# But for code-based execution:

def start():
    """Entry point for production SSE server"""
    # This assumes FastMCP has a run method that handles sse
    # Or strict ASGI export.
    # If using 'mcp' CLI is preferred, we can put that in Docker.
    pass

# For now, let's create a script that just re-exports the mcp object
# so `fastmcp run` work.
app = mcp
