import logging
import sys

def setup_logging(name: str):
    """Configure logging to stderr (important for MCP)."""
    # Force root logger to stderr and clear other handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    
    return logging.getLogger(name)

logger = setup_logging("linshare-mcp-server")
