from .app import mcp
# Import all modules to register tools and resources
from .tools import files as common_files
from .tools.admin import workgroups as admin_workgroups, users as admin_users, myspace as admin_myspace, audit as admin_audit
from .tools.user import auth, myspace, workgroups as user_workgroups, users as user_users, files as user_files, shares, guests, audit as user_audit
from .resources import files as resource_files

def main():
    """Main entry point for the LinShare MCP server."""
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
