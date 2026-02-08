# Dockerfile for LinShare Assistant (MCP + Chat)
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install all dependencies (Consolidated for better caching)
COPY requirements.txt /app/requirements-mcp.txt
COPY linshare-chat-client/requirements.txt /app/requirements-chat.txt

RUN pip install --no-cache-dir -r requirements-mcp.txt && \
    pip install --no-cache-dir -r requirements-chat.txt && \
    pip install --no-cache-dir uvicorn chainlit

# 2. Copy application code
COPY linshare_mcp /app/linshare_mcp
COPY linshare-chat-client /app/linshare-chat-client
COPY scripts /app/scripts

# 3. Setup Entrypoint Script
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Default environment variables
ENV PYTHONPATH=/app
ENV LINSHARE_MCP_MODE=all
ENV MCP_SERVER_SSE_URL=http://localhost:8000/sse

# Expose ports
EXPOSE 8000 8080

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
