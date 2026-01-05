#!/usr/bin/env python3
"""Add API tags to all tool docstrings."""

import re
from pathlib import Path

def add_admin_tag(file_path):
    """Add [ADMIN API] tag and auth info to admin tools."""
    content = file_path.read_text()
    
    # Pattern to find @mcp.tool() followed by def and docstring
    pattern = r'(@mcp\.tool\(\))\s+(def\s+\w+\([^)]*\)\s*->\s*str:)\s+(""")'
    
    def replace_docstring(match):
        decorator = match.group(1)
        func_def = match.group(2)
        doc_start = match.group(3)
        
        # Check if already has a tag
        next_chars = content[match.end():match.end()+50]
        if '[ADMIN API]' in next_chars or '[USER API]' in next_chars or '[COMMON]' in next_chars:
            return match.group(0)
        
        return f'{decorator}\n{func_def}\n{doc_start}[ADMIN API] '
    
    updated = re.sub(pattern, replace_docstring, content)
    
    if updated != content:
        file_path.write_text(updated)
        return True
    return False

def add_user_tag(file_path):
    """Add [USER API] tag and auth info to user tools."""
    content = file_path.read_text()
    
    pattern = r'(@mcp\.tool\(\))\s+(def\s+\w+\([^)]*\)\s*->\s*str:)\s+(""")'
    
    def replace_docstring(match):
        decorator = match.group(1)
        func_def = match.group(2)
        doc_start = match.group(3)
        
        # Check if already has a tag
        next_chars = content[match.end():match.end()+50]
        if '[ADMIN API]' in next_chars or '[USER API]' in next_chars or '[COMMON]' in next_chars:
            return match.group(0)
        
        return f'{decorator}\n{func_def}\n{doc_start}[USER API] '
    
    updated = re.sub(pattern, replace_docstring, content)
    
    if updated != content:
        file_path.write_text(updated)
        return True
    return False

def add_common_tag(file_path):
    """Add [COMMON] tag to common tools."""
    content = file_path.read_text()
    
    pattern = r'(@mcp\.tool\(\))\s+(def\s+\w+\([^)]*\)\s*->\s*str:)\s+(""")'
    
    def replace_docstring(match):
        decorator = match.group(1)
        func_def = match.group(2)
        doc_start = match.group(3)
        
        # Check if already has a tag
        next_chars = content[match.end():match.end()+50]
        if '[ADMIN API]' in next_chars or '[USER API]' in next_chars or '[COMMON]' in next_chars:
            return match.group(0)
        
        return f'{decorator}\n{func_def}\n{doc_start}[COMMON] '
    
    updated = re.sub(pattern, replace_docstring, content)
    
    if updated != content:
        file_path.write_text(updated)
        return True
    return False

# Process admin tools
admin_dir = Path('/home/walidboudiche/mcp-servers/linshare_mcp/tools/admin')
print("Updating ADMIN tools:")
for file in admin_dir.glob('*.py'):
    if file.name != '__init__.py':
        if add_admin_tag(file):
            print(f"  ✓ {file.name}")
        else:
            print(f"  - {file.name} (already tagged)")

# Process user tools
user_dir = Path('/home/walidboudiche/mcp-servers/linshare_mcp/tools/user')
print("\nUpdating USER tools:")
for file in user_dir.glob('*.py'):
    if file.name != '__init__.py':
        if add_user_tag(file):
            print(f"  ✓ {file.name}")
        else:
            print(f"  - {file.name} (already tagged)")

# Process common tools
common_file = Path('/home/walidboudiche/mcp-servers/linshare_mcp/tools/files.py')
print("\nUpdating COMMON tools:")
if add_common_tag(common_file):
    print(f"  ✓ files.py")
else:
    print(f"  - files.py (already tagged)")

print("\n✅ All tools updated!")
