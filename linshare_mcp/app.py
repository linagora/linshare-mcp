from mcp.server.fastmcp import FastMCP

name = "linshare-mcp-server"

# Create FastMCP instance
mcp = FastMCP(name=name)

# Disable DNS rebinding protection to allow connections from other Docker containers
# Fixes: 421 Misdirected Request when connecting with valid auth from non-localhost (e.g. 172.x.x.x)
if hasattr(mcp, "settings") and mcp.settings.transport_security:
    mcp.settings.transport_security.enable_dns_rebinding_protection = False
