# LinShare Chat Assistant

A Chainlit-based chat interface that connects to the LinShare MCP server, allowing users to manage their LinShare files through natural language conversation.

## 🚀 Features

- **Multi-LLM Support**: Works with Google Gemini, DeepSeek, Groq, or local OpenAI-compatible models
- **Settings UI**: Re-configure MCP connection, Auth Mode, and JWT tokens directly from the chat interface
- **File Upload**: Drag-and-drop file uploads with chunked transfer
- **Tool Integration**: Full access to LinShare MCP tools (documents, shares, guests, audit)
- **LinShare Branding**: Custom sky-blue theme matching LinShare's design

## 📦 Installation

```bash
cd linshare-chat-client
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

```bash
# LLM Provider (google, deepseek, groq, local)
LLM_PROVIDER=google
GOOGLE_API_KEY=your_key_here

# MCP Server URL (SSE transport)
MCP_SERVER_SSE_URL=http://127.0.0.1:8100/sse

# LinShare API (These can also be configured via Settings UI)
LINSHARE_USER_URL=https://your-instance.com/linshare/webservice/rest/user/v5
LINSHARE_JWT_TOKEN=your_jwt_token

> [!NOTE]
> The chat client automatically includes an `Authorization` header in all requests to the MCP server. It uses **Bearer** auth (with your JWT) in User mode and **Basic** auth (with your credentials) in Admin mode.
```

## 🏃 Usage

1. **Start the MCP Server** (in a separate terminal):
   ```bash
   python -m linshare_mcp.main --transport sse --port 8100
   ```

2. **Start the Chat Client**:
   ```bash
   ./venv/bin/chainlit run chat_client.py -w
   ```

3. Open http://localhost:8000 in your browser.

## 🎨 Customization

- **Theme**: Edit `public/style.css` for UI styling
- **Welcome**: Edit `chainlit.md` for the welcome screen
- **Config**: Edit `.chainlit/config.toml` for Chainlit settings

## 📁 Files

| File | Description |
|------|-------------|
| `chat_client.py` | Main application with LLM and MCP integration |
| `server_sse.py` | SSE server entrypoint for MCP |
| `public/` | Static assets (CSS, images) |
| `.chainlit/` | Chainlit configuration |
