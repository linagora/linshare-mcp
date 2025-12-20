# Wrapper script to run the LinShare MCP server
import sys
import os
import runpy

# Ensure the current directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Run the module as a script, which handles relative imports correctly
    runpy.run_module("linshare_mcp.main", run_name="__main__", alter_sys=True)
