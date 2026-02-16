#!/bin/bash
set -e

# Helper to wait for the SSE server to be ready
wait_for_sse() {
    echo "⏳ Waiting for MCP SSE server to be ready at $MCP_SERVER_SSE_URL..."
    until curl -s "$MCP_SERVER_SSE_URL" > /dev/null; do
        sleep 2
    done
    echo "✅ MCP SSE server is UP!"
}

case "$1" in
    "mcp")
        echo "🚀 Starting LinShare MCP Server (SSE Mode)..."
        exec python -m linshare_mcp.main --transport sse --host 0.0.0.0 --port 8000
        ;;
    "chat")
        echo "🚀 Starting LinShare Chat Assistant..."
        cd /app/linshare-chat-client
        exec chainlit run chat_client.py --port 8080 --host 0.0.0.0
        ;;
    "all")
        echo "🚀 Starting both MCP Server and Chat Assistant..."
        # Run MCP server in background
        python -m linshare_mcp.main --transport sse --host 0.0.0.0 --port 8000 &
        
        # Wait for SSE to be ready before starting chat
        wait_for_sse
        
        # Start Chat Assistant
        echo "🚀 Starting LinShare Chat Assistant..."
        cd /app/linshare-chat-client
        exec chainlit run chat_client.py --port 8080 --host 0.0.0.0
        ;;
    *)
        exec "$@"
        ;;
esac
