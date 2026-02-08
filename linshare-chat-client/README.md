# LinShare Chat Client

A Chainlit-based chat interface that connects to the LinShare MCP server, allowing users to manage their LinShare files through natural language conversation.

## 🚀 Features

- **Multi-LLM Support**: Works with Google Gemini, DeepSeek, Groq, or local OpenAI-compatible models
- **Settings UI**: Re-configure MCP connection, Auth Mode, and JWT tokens directly from the chat interface
- **File Upload**: Drag-and-drop file uploads (documents, images, audio, video) with chunked transfer
- **Tool Integration**: Full access to LinShare MCP tools (documents, shares, guests, audit)
- **LinShare Branding**: Custom sky-blue theme matching LinShare's design

## 🐳 Docker (Recommended)

You can run the full stack (Chat + MCP Server) using Docker Compose located in this directory.

### 1. Requirements
- Docker & Docker Compose installed
- A `.env` file in the **project root** (parent directory) configured with your keys.

### 2. Build and Run

```bash
# Build the image and start
docker compose up --build -d
```

The Dockerfile is located in the parent directory and builds a unified image for both services.

### 3. Access
- **Chat Interface**: [http://localhost:8080](http://localhost:8080)
- **MCP Server SSE**: [http://localhost:8000/sse](http://localhost:8000/sse)

---

## ⚙️ Settings UI

You can configure the Chat Assistant dynamically without restarting the server:

1. **Open Settings**: Click the gear icon (**⚙️**) in the bottom-left of the chat window.
2. **MCP Connection**: Update the `MCP Server SSE URL` (e.g., `http://localhost:8000/sse`).
3. **Authentication Mode**:
    - **User Mode**: Toggle "Admin Mode" **OFF**. Enter your LinShare JWT in the Manual JWT field or use the `LINSHARE_JWT_TOKEN` environment variable.
    - **Admin Mode**: Toggle "Admin Mode" **ON**. Enter your service account username and password.
4. **Manual JWT**: Toggle "Manual JWT" **ON** and paste your LinShare JWT token to authenticate User Mode tools. This is independent of the OIDC login used for the chat assistant itself.
5. **Persistence**: Your settings are saved per-user in `user_configs.json` and persist between sessions.

## 📦 Local Installation (No Docker)

```bash
cd linshare-chat-client
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

```bash
# --- LLM Configuration ---
# Options: google, deepseek, groq, local
LLM_PROVIDER=google

# 1. Google Gemini (Default)
GOOGLE_API_KEY=your_gemini_key

# 2. DeepSeek
# DEEPSEEK_API_KEY=your_deepseek_key

# 3. Groq (Llama 3)
# GROQ_API_KEY=your_groq_key

# 4. Local LLM (OpenAI Compatible)
# LOCAL_LLM_URL=http://localhost:1234/v1
# LOCAL_LLM_MODEL=local-model
# LOCAL_LLM_API_KEY=not-needed

# --- Voice Transcription (Optional) ---
# Required if you want to use voice prompts (Microphone)
# Uses Groq's Whisper-Large-V3 for fast transcription
TRANSCRIPTION_PROVIDER=groq
GROQ_API_KEY=your_groq_key  # Required for voice even if using Google/DeepSeek for chat

# MCP Server URL (SSE transport)
MCP_SERVER_SSE_URL=http://127.0.0.1:8100/sse

# LinShare API
LINSHARE_USER_URL=https://your-instance.com/linshare/webservice/rest/user/v5

# Note: Authentication credentials (JWT) should be configured 
# directly in the Chat Interface Settings for better security.
```

> [!NOTE]
> The chat client automatically includes an `Authorization` header in all requests to the MCP server. It uses **Bearer** auth (with your JWT) in User mode and **Basic** auth (with your credentials) in Admin mode.

### 🔑 Authentication (OIDC)

The chat assistant supports native OpenID Connect (OIDC) login via Chainlit.

1. **Enable OIDC**: Set `AUTH_TYPE=oidc` in `.env`.
2. **Configure Provider**: Provide your `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and `OIDC_CONFIG_URL` (Discovery URL).
3. **Set Redirect URL**: Ensure your OIDC provider allows `http://localhost:8001/auth/oauth/LinShare/callback`.
4. **Session Security**: Generate a random `CHAINLIT_AUTH_SECRET` (e.g., `openssl rand -hex 32`).

When OIDC is enabled, users must log in via the identity provider to access the Chat Assistant. Note that this is independent of the LinShare API authentication, which must still be configured via the Settings UI or environment variables.

## 🏃 Usage (Local)

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
docker-compose.yml | Docker Compose file for full stack deployment |
