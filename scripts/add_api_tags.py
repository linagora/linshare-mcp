#!/usr/bin/env python3
"""
Script to add API type tags to all tool descriptions.
This makes it clear which tools use Admin API vs User API.
"""

import os
import re
from pathlib import Path

# Define the tags
ADMIN_TAG = """[ADMIN API] """
USER_TAG = """[USER API] """
COMMON_TAG = """[COMMON] """

# Admin API description addition
ADMIN_AUTH = """
    🔐 Authentication: Service Account (LINSHARE_USERNAME + LINSHARE_PASSWORD)
    🌐 API Endpoint: Admin delegation v2"""

# User API description addition
USER_AUTH = """
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5"""

# Common tools description
COMMON_AUTH = """
    🔐 Authentication: None required (local filesystem operation)"""

def update_admin_tools():
    """Update all admin tool descriptions."""
    admin_dir = Path("/home/walidboudiche/mcp-servers/linshare_mcp/tools/admin")
    
    for file in admin_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        
        print(f"Processing admin tool: {file.name}")
        content = file.read_text()
        
        # Find all @mcp.tool() decorators and their docstrings
        # Add [ADMIN API] tag if not present
        if '[ADMIN API]' not in content and '[USER API]' not in content:
            # This is a simple approach - in production you'd use AST parsing
            content = content.replace('"""', f'"""{ADMIN_TAG}', 1)
            file.write_text(content)
            print(f"  ✓ Updated {file.name}")

def update_user_tools():
    """Update all user tool descriptions."""
    user_dir = Path("/home/walidboudiche/mcp-servers/linshare_mcp/tools/user")
    
    for file in user_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        
        print(f"Processing user tool: {file.name}")
        content = file.read_text()
        
        # Add [USER API] tag if not present
        if '[USER API]' not in content and '[ADMIN API]' not in content:
            content = content.replace('"""', f'"""{USER_TAG}', 1)
            file.write_text(content)
            print(f"  ✓ Updated {file.name}")

def update_common_tools():
    """Update common tool descriptions."""
    files_path = Path("/home/walidboudiche/mcp-servers/linshare_mcp/tools/files.py")
    
    print(f"Processing common tool: files.py")
    content = files_path.read_text()
    
    # Add [COMMON] tag if not present
    if '[COMMON]' not in content:
        content = content.replace('"""', f'"""{COMMON_TAG}', 1)
        files_path.write_text(content)
        print(f"  ✓ Updated files.py")

if __name__ == "__main__":
    print("Adding API type tags to tool descriptions...\n")
    update_admin_tools()
    print()
    update_user_tools()
    print()
    update_common_tools()
    print("\n✅ All tools updated!")
