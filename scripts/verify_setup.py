import sys
import os

# Add the current directory to sys.path so we can import linshare_mcp
sys.path.append(os.getcwd())

try:
    from linshare_mcp.app import mcp
    # Import main to ensure tools are registered
    from linshare_mcp import main
    
    print("Successfully imported mcp")
    
    # FastMCP stores tools in _tools or similar, but let's just check if we can list them
    # The implementation details of FastMCP might vary, but usually there's a way to inspect.
    # Let's try to access the underlying list if possible, or just print the object.
    print(f"MCP Object: {mcp}")
    
    # In FastMCP, tools are decorated. We can check if the functions are registered.
    # Let's check if the tool names are in the registry if accessible.
    # If not, we can just assume if imports worked and decorators ran, it's fine.
    
    # Let's try to list tools using the list_tools capability if exposed, 
    # but for now just printing success of import is a good start.
    
    # We can also check our specific tools
    from linshare_mcp.tools import files, workgroups, users, roles
    print("Successfully imported all tool modules")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
