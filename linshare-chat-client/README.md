# LinShare Chat Assistant

A Chainlit-based chat interface that connects to the LinShare MCP server, allowing users to manage their LinShare files through natural language conversation.

## 🚀 Features

- **Multi-LLM Support**: Works with Google Gemini, DeepSeek, Groq, or local OpenAI-compatible models
- **Settings UI**: Re-configure MCP connection, Auth Mode, and JWT tokens directly from the chat interface
- **File Upload**: Drag-and-drop file uploads with chunked transfer
- **Tool Integration**: Full access to LinShare MCP tools (documents, shares, guests, audit)
- **LinShare Branding**: Custom sky-blue theme matching LinShare's design

## ⚙️ Settings UI

You can configure the Chat Assistant dynamically without restarting the server:

1. **Open Settings**: Click the gear icon (**⚙️**) in the bottom-left of the chat window.
2. **MCP Connection**: Update the `MCP Server SSE URL` (e.g., `http://localhost:8000/sse`).
3. **Authentication Mode**:
    - **User Mode**: Toggle "Admin Mode" **OFF**. Enter your LinShare JWT in the Manual JWT field or use the `LINSHARE_JWT_TOKEN` environment variable.
    - **Admin Mode**: Toggle "Admin Mode" **ON**. Enter your service account username and password.
4. **Manual JWT**: Toggle "Manual JWT" **ON** and paste your LinShare JWT token to authenticate User Mode tools. This is independent of the OIDC login used for the chat assistant itself.
5. **Persistence**: Your settings are saved per-user in `user_configs.json` and persist between sessions.

## 📦 Installation

From the repository root:

```bash
cd linshare-chat-client

# Option A — standard venv (recommended on Debian/Ubuntu)
python3 -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Option B — uv
uv venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
uv pip install -r requirements.txt
```

> [!NOTE]
> On Debian/Ubuntu the binary is `python3`, not `python` (unless the `python-is-python3` package is installed). Using `python` will fail with `command not found`.

> [!NOTE]
> `uv venv` does **not** install `pip` into the venv, so you must use `uv pip install ...` afterwards — plain `pip` would resolve to the system pip and fail with `error: externally-managed-environment` (PEP 668). `python3 -m venv` does install pip, so plain `pip` works there.

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

### 🔑 Authentication (OIDC)

The chat assistant supports native OpenID Connect (OIDC) login via Chainlit.

1. **Enable OIDC**: Set `AUTH_TYPE=oidc` in `.env`.
2. **Configure Provider**: Provide your `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and `OIDC_CONFIG_URL` (Discovery URL).
3. **Set Redirect URL**: Ensure your OIDC provider allows `http://localhost:8001/auth/oauth/LinShare/callback`.
4. **Session Security**: Generate a random `CHAINLIT_AUTH_SECRET` (e.g., `openssl rand -hex 32`).

When OIDC is enabled, users must log in via the identity provider to access the Chat Assistant. Note that this is independent of the LinShare API authentication, which must still be configured via the Settings UI or environment variables.
```

## 🏃 Usage

1. **Start the MCP Server**:
   ```bash
   # Navigate to the project root (mcp-servers/)
   cd ..
   python -m linshare_mcp.main --transport sse --port 8100
   ```

2. **Start the Chat Client**:
   ```bash
   # Navigate to the client directory
   cd linshare-chat-client
   
   # Activate venv and run
   source venv/bin/activate
   chainlit run chat_client.py -w
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
