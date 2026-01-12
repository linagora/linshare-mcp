
# Dockerfile for Production LinShare MCP Setup

# --- Stage 1: MCP Server ---
FROM python:3.11-slim as server

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn fastmcp

COPY linshare_mcp /app/linshare_mcp
COPY server_sse.py /app/

# Expose SSE port
EXPOSE 8000
CMD ["fastmcp", "run", "linshare_mcp.main:mcp", "--transport", "sse", "--port", "8000", "--host", "0.0.0.0"]

# --- Stage 2: Chat Client (Optional, separate container usually) ---
# You would usually run this in a separate container/service
# CMD ["chainlit", "run", "chat_client.py", "--port", "8080"]
