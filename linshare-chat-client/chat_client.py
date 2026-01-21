# chat_client.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Load environment variables before ANY other imports
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# 2. DEBUG: Check and Force OIDC variables for Chainlit auto-discovery
AUTH_TYPE = os.getenv("AUTH_TYPE", "none").lower()
print(f"🔍 Environment Check (Auth Type: {AUTH_TYPE})")

if AUTH_TYPE == "oidc":
    print("🛠️  Auto-configuring OIDC via Generic OAuth...")
    discovery_url = os.getenv("OIDC_CONFIG_URL") or os.getenv("OIDC_DISCOVERY_URL")
    client_id = os.getenv("OIDC_CLIENT_ID")
    client_secret = os.getenv("OIDC_CLIENT_SECRET")
    
    if discovery_url and client_id and client_secret:
        try:
            import httpx
            # Sync fetch of discovery info
            with httpx.Client() as client:
                resp = client.get(discovery_url)
                resp.raise_for_status()
                disco = resp.json()
                
                # Map OIDC Discovery to Chainlit Generic OAuth variables
                os.environ["OAUTH_GENERIC_CLIENT_ID"] = client_id
                os.environ["OAUTH_GENERIC_CLIENT_SECRET"] = client_secret
                os.environ["OAUTH_GENERIC_AUTH_URL"] = disco.get("authorization_endpoint")
                os.environ["OAUTH_GENERIC_TOKEN_URL"] = disco.get("token_endpoint")
                os.environ["OAUTH_GENERIC_USER_INFO_URL"] = disco.get("userinfo_endpoint")
                os.environ["OAUTH_GENERIC_SCOPES"] = "openid profile email"
                os.environ["OAUTH_GENERIC_NAME"] = "LinShare"
                
                # CRITICAL: Manually patch the existing provider instance in Chainlit
                try:
                    import chainlit.oauth_providers as oauth
                    print(f"DEBUG: Found {len(oauth.providers)} configured providers.")
                    for p in oauth.providers:
                        class_name = p.__class__.__name__
                        print(f"DEBUG: Checking provider: {p.id} ({class_name})")
                        if class_name == "GenericOAuthProvider":
                            p.id = "LinShare"
                            p.client_id = client_id
                            p.client_secret = client_secret
                            p.authorize_url = disco.get("authorization_endpoint")
                            p.token_url = disco.get("token_endpoint")
                            p.user_info_url = disco.get("userinfo_endpoint")
                            p.scopes = "openid profile email"
                            # Important: Chainlit uses authorize_params to build the URL
                            p.authorize_params["scope"] = "openid profile email"
                            print("✅ GenericOAuthProvider instance manually patched (Scope & ID fixed).")
                except Exception as patch_err:
                    print(f"⚠️ Could not patch provider instance: {patch_err}")
                
                print(f"✅ Generic OAuth configured using OIDC discovery.")
        except Exception as e:
            print(f"❌ Failed to parse OIDC discovery: {e}")

# Chainlit will now find the 'generic' provider we just patched.
import chainlit as cl
from mcp import ClientSession
# ... existing imports ...
from mcp.client.sse import sse_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
import json
import httpx
import base64

# --- LinShare API Configuration ---
LINSHARE_USER_URL = os.getenv("LINSHARE_USER_URL") or os.getenv("LINSHARE_BASE_URL", "")
# Derive AUTH_BASE_URL (strip /user/v5 if present)
import re
AUTH_BASE_URL = re.sub(r'/user/v\d+$', '', LINSHARE_USER_URL.rstrip('/'))

# --- User Config Persistence ---
USER_CONFIGS_FILE = Path(__file__).parent / "user_configs.json"

def load_user_config(user_id):
    """Load persistent settings for a specific user."""
    if not USER_CONFIGS_FILE.exists():
        return {}
    try:
        with open(USER_CONFIGS_FILE, "r") as f:
            data = json.load(f)
            return data.get(user_id, {})
    except Exception as e:
        print(f"⚠️ Error loading user config: {e}")
        return {}

def save_user_config(user_id, config_data):
    """Save settings for a specific user."""
    try:
        all_configs = {}
        if USER_CONFIGS_FILE.exists():
            with open(USER_CONFIGS_FILE, "r") as f:
                all_configs = json.load(f)
        
        all_configs[user_id] = config_data
        with open(USER_CONFIGS_FILE, "w") as f:
            json.dump(all_configs, f, indent=4)
        print(f"✅ Configuration saved for user: {user_id}")
    except Exception as e:
        print(f"❌ Error saving user config: {e}")

# --- Authentication Callbacks ---
if AUTH_TYPE == "oidc":
    try:
        @cl.oauth_callback
        def oauth_callback(provider_id, token, raw_user_data, default_user):
            """Capture OIDC tokens after successful login."""
            # Store metadata in user object for on_chat_start
            return default_user
        print("✅ OIDC OAuth Callback registered.")
    except Exception as e:
        print(f"❌ FAILED to register OIDC callback: {e}")

MCP_SERVER_SSE_URL = os.getenv("MCP_SERVER_SSE_URL", "http://127.0.0.1:8100/sse")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Local / On-Premise LLM Configuration
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL") # e.g., http://localhost:1234/v1
if LOCAL_LLM_URL:
    LOCAL_LLM_URL = LOCAL_LLM_URL.rstrip('/')
    
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "not-needed")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "local-model")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").lower()
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "groq").lower()

print(f"📡 Configuration Loaded:")

def get_settings(user_id=None, current_auth_mode=None):
    # Load current settings to use as initial values in the UI
    config = load_user_config(user_id) if user_id else {}
    
    # Defaults
    # Defaults
    # Defaults via Environment or Empty
    mcp_url = config.get("mcp_url") or os.getenv("MCP_SERVER_SSE_URL", "")
    
    # Handle legacy config (string) vs new config (bool)
    stored_mode = config.get("mcp_auth_mode")
    
    if isinstance(stored_mode, bool):
        is_admin_mode = stored_mode
    elif isinstance(stored_mode, str) and "Basic" in stored_mode:
        is_admin_mode = True
    else:
        is_admin_mode = False
        
    # Handle Manual JWT Switch
    is_manual_jwt = config.get("use_manual_jwt", False) # Default to False (use OIDC)

    # Override if passed explicitly (during update) - Not really needed for static UI but good for safety
    if current_auth_mode is not None:
        is_admin_mode = current_auth_mode

    widgets = [
        cl.input_widget.TextInput(
            id="mcp_url",
            label="MCP Server SSE URL",
            initial=mcp_url,
        ),
        cl.input_widget.Switch(
            id="mcp_auth_mode",
            label="Enable Admin Mode (Basic Auth)",
            initial=is_admin_mode
        ),
        cl.input_widget.TextInput(
            id="admin_username",
            label="Admin Username (for Basic Auth)",
            initial=config.get("admin_username") or ""
        ),
        cl.input_widget.TextInput(
            id="admin_password",
            label="Admin Password (for Basic Auth)",
            initial=config.get("admin_password") or ""
        ),
        cl.input_widget.Switch(
            id="use_manual_jwt",
            label="Enable Manual JWT Override",
            initial=is_manual_jwt
        ),
        cl.input_widget.TextInput(
            id="manual_jwt",
            label="Manual JWT Token",
            initial=config.get("manual_jwt") or ""
        )
    ]
    
    # NOTE: All widgets are returned unconditionally to ensure instant usability 
    # without requiring the "Close -> Re-open" workflow.
    
    return widgets

@cl.on_settings_update
async def on_settings_update(settings):
    """Handle changes to the configuration UI."""
    user = cl.user_session.get("user")
    user_id = user.identifier if user else "public_user"
    
    # Save to disk
    save_user_config(user_id, settings)
    
    # Notify and reconnect automatically
    await cl.Message(content="⚙️ Settings saved! Reconnecting...").send()
    await connect_mcp(settings)

async def connect_mcp(settings=None, silent=False):
    """Worker to handle MCP connection with specific settings and headers."""
    # 1. Close existing session if any
    old_mcp_session = cl.user_session.get("mcp_session")
    if old_mcp_session:
        try:
             # Just safety cleanup
             cl.user_session.set("mcp_session", None)
             print("🔄 Previous MCP session cleared.")
        except: pass

    old_sse = cl.user_session.get("sse_ctx")
    if old_sse:
        try:
             await old_sse.__aexit__(None, None, None)
             print("🔄 Previous MCP SSE connection closed.")
        except: pass

    # 2. Get settings (from UI or fallback)
    if not settings:
        user = cl.user_session.get("user")
        user_id = user.identifier if user else "public_user"
        settings = load_user_config(user_id)
    
    sse_url = settings.get("mcp_url") or os.getenv("MCP_SERVER_SSE_URL", "")
    
    if not sse_url:
        print("⚠️ No MCP URL configured. Skipping connection.")
        if not silent:
             await cl.Message(content="⚠️ Please configure the MCP Server URL in settings.").send()
        return
    
    # Handle Auth Mode Switches
    auth_mode_val = settings.get("mcp_auth_mode")
    if isinstance(auth_mode_val, bool):
        is_admin = auth_mode_val
    elif isinstance(auth_mode_val, str) and "Basic" in auth_mode_val:
        is_admin = True
    else:
        is_admin = False
        
    use_manual_jwt = settings.get("use_manual_jwt", False)
    
    # 3. Build headers
    headers = {}
    if not is_admin:
        # Priority 1: User Manual JWT (if switch enabled)
        manual_token = settings.get("manual_jwt")
        if use_manual_jwt and manual_token and manual_token.strip():
             headers["Authorization"] = f"Bearer {manual_token.strip()}"
             print(f"🔑 Using Manual JWT for authentication.")
        
        # Priority 2: OIDC Token Exchange (Automated)
        elif AUTH_TYPE == "oidc":
             # Try to get JWT from user session cache
             cached_jwt = cl.user_session.get("linshare_jwt")
             if not cached_jwt:
                  # Perform exchange
                  cached_jwt = await get_linshare_jwt_from_oidc()
                  if cached_jwt:
                       cl.user_session.set("linshare_jwt", cached_jwt)
             
             if cached_jwt:
                 headers["Authorization"] = f"Bearer {cached_jwt}"
                 print(f"🔑 Using OIDC-exchanged LinShare JWT.")
             else:
                 print("⚠️ OIDC exchange failed. Fallback to Env variable.")
                 token = os.getenv("LINSHARE_JWT_TOKEN")
                 if token:
                     headers["Authorization"] = f"Bearer {token}"
                     print(f"🔑 Using User JWT (Bearer) from environment.")
        
        # Priority 3: Environment Variable
        else:
            token = os.getenv("LINSHARE_JWT_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                print(f"🔑 Using User JWT (Bearer) from environment.")
            else:
                print("⚠️ No LinShare JWT provided (Manual or Env). Tools may fail.")
    else:
        # Basic Auth
        user_name = settings.get("admin_username")
        password = settings.get("admin_password")
        if user_name and password:
            auth_str = f"{user_name}:{password}"
            encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
            print(f"🔑 Using Admin Basic Auth for {user_name}")

    print(f"🔄 Connecting to SSE Server at: {sse_url}")
    try:
        # Keep connection open manually
        sse_ctx = sse_client(sse_url, headers=headers)
        streams = await sse_ctx.__aenter__()
        
        session_ctx = ClientSession(streams[0], streams[1])
        session = await session_ctx.__aenter__()
        await session.initialize()
        
        # Store contexts
        cl.user_session.set("session_ctx", session_ctx)
        cl.user_session.set("sse_ctx", sse_ctx)
        cl.user_session.set("mcp_session", session)

        # 4. Fetch available tools from MCP Server
        result = await session.list_tools()
        mcp_tools = result.tools
        cl.user_session.set("tools_map", {t.name: t for t in mcp_tools})
        print(f"✅ Connected! {len(mcp_tools)} tools loaded.")
        
        return mcp_tools

    except Exception as e:
        error_msg = str(e)
        # Handle TaskGroup/ExceptionGroup which can be cryptic
        if "ExceptionGroup" in error_msg or "TaskGroup" in error_msg:
            # Try to extract the first sub-exception message
            try:
                if hasattr(e, 'exceptions') and e.exceptions:
                    sub_e = e.exceptions[0]
                    error_msg = f"{type(sub_e).__name__}: {sub_e}"
            except: pass
            
        print(f"❌ Connection Failed: {error_msg}")
        if not silent:
            await cl.Message(content=f"❌ Connection Failed to {sse_url}: {error_msg}").send()
        return None
print(f"   LLM Provider: {LLM_PROVIDER}")
print(f"   Transcription Provider: {TRANSCRIPTION_PROVIDER}")
print(f"   Auth Type: {AUTH_TYPE}")

if LLM_PROVIDER == "local":
    print(f"   Local URL: {LOCAL_LLM_URL}")
    print(f"   Local Model: {LOCAL_LLM_MODEL}")

def get_llm():
    """Helper to initialize the LLM based on provider settings."""
    if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
        return ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
            max_tokens=2048
        )
    elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            temperature=0
        )
    elif LLM_PROVIDER == "local" and LOCAL_LLM_URL:
        return ChatOpenAI(
            model=LOCAL_LLM_MODEL,
            api_key=LOCAL_LLM_API_KEY,
            base_url=LOCAL_LLM_URL,
            max_tokens=2048
        )
        # Default to Google Gemini
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)

@cl.on_audio_start
async def on_audio_start():
    cl.user_session.set("audio_buffer", bytearray())
    cl.user_session.set("audio_mime_type", "audio/webm") # Default usually
    print("🎤 Audio recording started")
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk):
    # chunk is likely cl.AudioChunk, containing 'data', 'mimeType', etc.
    # In recent versions it might be a dataclass or Pydantic model.
    # We access .data assuming it's bytes.
    buffer = cl.user_session.get("audio_buffer")
    if buffer is not None:
        # Check if chunk has .data or is bytes
        if hasattr(chunk, "data"):
             buffer.extend(chunk.data)
             if hasattr(chunk, "mimeType"):
                 cl.user_session.set("audio_mime_type", chunk.mimeType)
        elif isinstance(chunk, bytes):
             buffer.extend(chunk)
        else:
             print(f"⚠️ Unknown chunk type: {type(chunk)}")

@cl.on_audio_end
async def on_audio_end(*args, **kwargs):
    print(f"🎤 Audio recording ended. Args: {args}, Kwargs: {kwargs}")
    
    buffer = cl.user_session.get("audio_buffer")
    if not buffer:
        await cl.Message(content="⚠️ Audio ended but no data buffered.").send()
        return
        
    try:
        if not GROQ_API_KEY:
            await cl.Message(content="⚠️ Groq API Key missing. Cannot transcribe.").send()
            return

        # DEBUG: See what's in the session (looking for staged files)
        # In Chainlit 2.x, user_session is a wrapper. We can try to access the underlying dict if possible.
        try:
             print(f"🕵️ on_audio_end - Session Keys: {list(cl.user_session.data.keys())}")
        except:
             print(f"🕵️ on_audio_end - Could not list session keys directly")
        
        if "elements" in kwargs:
             print(f"🕵️ on_audio_end - Elements found in kwargs: {len(kwargs['elements'])}")

        # Simple transcription using Groq
        try:
            from groq import Groq
        except ImportError:
            await cl.Message(content="❌ 'groq' library not installed. Please pip install groq.").send()
            return
            
        # Detection of magic numbers for better extension mapping
        mime_type = cl.user_session.get("audio_mime_type", "audio/webm")
        import io
        import uuid
        
        # EBML/WebM: 1A 45 DF A3
        # RIFF/WAV: 52 49 46 46
        # MPEG: FF FB or ID3 (49 44 33)
        magic = buffer[:4].hex().upper()
        print(f"🎤 Debug: Buffer Magic Number: {magic}")
        
        ext = ".webm"
        is_raw_pcm = not (magic.startswith("1A45DFA3") or magic.startswith("52494646") or magic.startswith("494433") or magic.startswith("FFFB"))
        
        if is_raw_pcm:
            print("📦 Wrapping raw PCM in WAV header...")
            import wave
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2) # 16-bit PCM
                wf.setframerate(24000) # Match config.toml
                wf.writeframes(buffer)
            buffer = wav_buffer.getvalue()
            ext = ".wav"
        else:
            if magic.startswith("52494646"): ext = ".wav"
            elif magic.startswith("494433") or magic.startswith("FFFB"): ext = ".mp3"
            elif "mp4" in mime_type: ext = ".mp4"
            elif "wav" in mime_type: ext = ".wav"
            elif "mpeg" in mime_type: ext = ".mp3"
        
        fname = f"audio_{uuid.uuid4()}{ext}"
        
        # DEBUG: Save to disk to verify validity
        with open("debug_audio_dump" + ext, "wb") as f_debug:
            f_debug.write(buffer)
        print(f"🎤 Debug: Saved {len(buffer)} bytes to debug_audio_dump{ext} (Mime: {mime_type}, Was Raw: {is_raw_pcm})")

        # Create bytes IO with name attribute
        audio_file = io.BytesIO(buffer)
        audio_file.name = fname
        
        await cl.Message(content=f"🎧 Transcribing audio ({len(buffer)} bytes, ext: {ext})...").send()
        
        # 2. Call Transcription Provider
        if TRANSCRIPTION_PROVIDER == "groq" and GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            transcription = client.audio.transcriptions.create(
                file=(fname, audio_file.read()),
                model="whisper-large-v3",
                response_format="json"
            )
            text = transcription.text
        else:
            await cl.Message(content=f"⚠️ Transcription provider '{TRANSCRIPTION_PROVIDER}' not fully implemented or key missing.").send()
            return
        print(f"🗣️ Transcribed: {text}")
        
        # 3. Send the Transcription Signal to the frontend
        # Our public/script.js MutationObserver will catch this and fill the input field.
        # author="System" and hiding the message via JS keeps it clean.
        msg = cl.Message(
            content=f'<span class="transcription-signal" id="trans-{uuid.uuid4().hex[:8]}">{text}</span>',
            author="System"
        )
        await msg.send()
        
        # Store for removal after the user clicks "Send"
        cl.user_session.set("last_transcription_msg", msg)
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        await cl.Message(content=f"❌ Transcription failed: {e}").send()
    finally:
        cl.user_session.set("audio_buffer", None)

async def get_linshare_jwt_from_oidc():
    """
    Exchange OIDC access token (from Chainlit session) for a LinShare JWT.
    This ensures we only send a LinShare JWT to the MCP server, and not the raw OIDC token.
    """
    user = cl.user_session.get("user")
    if not user:
        print("⚠️ No user in session. Cannot perform OIDC exchange.")
        return None
    
    # Chainlit's Generic OAuth provider stores tokens in metadata
    # metadata is usually a dict if the user successfully logged in
    metadata = getattr(user, "metadata", {})
    if not metadata:
        print("⚠️ User found but metadata is empty. Cannot extract OIDC token.")
        return None

    oidc_token = metadata.get("access_token")
    if not oidc_token:
        # Check in 'extra_data' which is where some providers store it
        oidc_token = metadata.get("extra_data", {}).get("access_token")
        
    if not oidc_token:
        print("⚠️ OIDC login detected but no 'access_token' found in user metadata.")
        return None

    if not AUTH_BASE_URL:
        print("⚠️ AUTH_BASE_URL is empty. Check LINSHARE_USER_URL in .env.")
        return None

    auth_base = AUTH_BASE_URL.rstrip('/')
    headers = {
        'Authorization': f'Bearer {oidc_token}',
        'accept': 'application/json'
    }
    
    print(f"🔄 Exchanging OIDC token for LinShare JWT at {auth_base}...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Establish session (Cookie generation on LinShare side)
            auth_url = f"{auth_base}/authentication/authorized"
            resp = await client.get(auth_url, headers=headers, timeout=10)
            resp.raise_for_status()
            
            # 2. Get/Create JWT for the Chat Assistant
            jwt_url = f"{auth_base}/jwt"
            # Get list of existing tokens
            list_resp = await client.get(jwt_url, headers=headers, timeout=10)
            tokens = list_resp.json() if list_resp.status_code == 200 else []
            
            # Look for our specific token
            token_desc = "Chat-Assistant-Token"
            existing = next((t for t in tokens if t.get('description') == token_desc), None)
            
            if not existing:
                print(f"🆕 Creating new LinShare JWT: {token_desc}")
                create_resp = await client.post(
                    jwt_url,
                    headers=headers,
                    json={"description": token_desc, "expiryDate": None}, # Permanent
                    timeout=10
                )
                create_resp.raise_for_status()
                existing = create_resp.json()
            else:
                print(f"♻️ Reusing existing LinShare JWT: {token_desc}")
                
            return existing.get('token')
            
        except Exception as e:
            print(f"❌ OIDC to JWT Exchange failed: {e}")
            return None

@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    user_id = user.identifier if user else "public_user"
    
    # 1. Initialize UI Settings
    settings = load_user_config(user_id)
    # Update initial values in widgets based on stored config
    await cl.ChatSettings(get_settings(user_id)).send()
    
    # 2. Connect to MCP Server (using stored or default settings)
    # Be silent on boot if no config exists to avoid scaring users with auth errors
    is_initial_run = not bool(settings)
    mcp_tools = await connect_mcp(settings, silent=is_initial_run)
    if not mcp_tools:
        # Fallback empty list to avoid crashes
        mcp_tools = []

    # 3. Build tool descriptions for the system prompt
    tool_descriptions = "\n".join([f"- {t.name}: {t.description} (Args: {t.inputSchema})" for t in mcp_tools])
    
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # --- NEW: User Context Injection ---
    user_context = ""
    # Default un-connected message
    welcome_msg = "👋 Welcome to LinShare Assistant. Please open settings ⚙️ to configure the MCP connection."
    
    # Only show "Connected" if we actually have tools or an active session
    session = cl.user_session.get("mcp_session")
    
    # Check for Admin Mode
    auth_mode_val = settings.get("mcp_auth_mode")
    is_admin_mode = False
    if isinstance(auth_mode_val, bool):
        is_admin_mode = auth_mode_val
    elif isinstance(auth_mode_val, str) and "Basic" in auth_mode_val:
        is_admin_mode = True

    if session and mcp_tools:
        if is_admin_mode:
            # Admin Context
            welcome_msg = f"🛡️ **Connected as Administrator!** | I have access to {len(mcp_tools)} Admin tools. I can audit users, manage workgroups, and more."
            user_context = (
                "\n\n### AUTHENTICATION STATUS: ADMINISTRATOR 🛡️\n"
                "You are currently logged in as a SYSTEM ADMINISTRATOR.\n"
                "You have ELEVATED PRIVILEGES to manage users, workgroups, and view audit logs.\n"
                "Do NOT refuse requests to list activities or manage resources on behalf of other users.\n"
                "Use the tools without any 'admin_' prefix for these tasks (e.g., 'list_user_documents')."
            )
            print(f"✅ Admin Mode Detected. Context injected.")
        else:
            # Regular User Context
            welcome_msg = f"✅ Connected! I have access to {len(mcp_tools)} LinShare tools. Ask me anything!"
            try:
                user_info_raw = await session.call_tool("user_get_current_user_info", {})
                user_info_text = user_info_raw.content[0].text if user_info_raw.content else ""
                print(f"🔍 User info response: {user_info_text[:200]}")
                if "Current User Session" in user_info_text:
                    user_context = f"\n\nCURRENT USER INFO:\n{user_info_text}"
                    # Extract first name if possible
                    import re
                    match = re.search(r"User: (\w+)", user_info_text)
                    if match:
                        welcome_msg = f"🛡️ **LinShare Assistant** | Hello {match.group(1)}! I'm ready to help you manage your files securely."
                        print(f"✅ Personalized welcome message created for: {match.group(1)}")
                else:
                    print(f"⚠️ User info doesn't contain 'Current User Session'. Response: {user_info_text}")
            except Exception as e:
                print(f"❌ Error fetching user info: {e}")

    system_prompt = f"""You are the LinShare Assistant. You have access to these tools:
{tool_descriptions}

Current Date: {now}{user_context}

To use a tool, reply in JSON format:
{{
  "thought": "I need to...",
  "tool": "tool_name",
  "arguments": {{ ... }}
}}

### CRITICAL GUIDELINES:
1. 🤖 AUTONOMY: Do NOT ask the user for information you can find yourself. 
   - Need user details? Use tools like 'user_get_current_user_info'.
   - Looking for a specific file? Use 'user_search_my_documents' or 'list_user_documents'. 
   - Need to check activities? Use 'user_search_audit' or 'search_user_audit_logs'.
2. 🔒 AUTHENTICATION: You are AUTOMATICALLY logged in if a token is present in the headers. 
   - NEVER ask for passwords/UUIDs unless a tool returns a persistent '401 Unauthorized' or 'Not logged in' error.
   - If you encounter an authentication error despite being connected, call 'user_check_config' to diagnose the session status before asking the user for help.
3. 📅 TIME: Use the 'Current Date' above to calculate relative dates. 
   - CRITICAL: All date arguments for tools (like 'begin_date') MUST use the format: YYYY-MM-DDT00:00:00Z.
4. 📎 ATTACHED FILES: If a user attaches a file, the chat client automatically uploads it. 
   - Check the history for a 'BACKGROUND ACTION' notification.
   - Use the provided 'UUID' from that notification directly for sharing or moving.
   - Do NOT call 'list_upload_files' unless the user specifically mentions picking a file from the server's local disk.
5. 🛠️ TOOL TYPES: 
   - Tools starting with 'user_' are for PERSONAL SPACE (User v5 API). Use these for your own files, login, and personal settings.
   - Tools NOT starting with 'user_' (and not 'list_upload_files') are for ADMINISTRATIVE/DELEGATION tasks. Use these when you need to act on behalf of other users, manage workgroups, or view global audit logs.
6. 🛠️ PROACTIVE ACTION: Do NOT narrate your plan or explain what you are about to do. If you have enough information to call a tool (like listing documents or searching for a user), CALL IT IMMEDIATELY. Your goal is to reach the final objective in as few conversational turns as possible.
7. 📝 RESPONSE: If you need to use a tool, the entire response MUST be the JSON block only.
8. 🗣️ FINAL ANSWER: If you have all the information required to answer the user (e.g. after a tool has returned data), do NOT output JSON. Instead, provide a helpful and friendly response in plain Markdown.
9. 💎 DATA PRESENTATION:
   - Use clean Markdown tables for simple lists (max 3 columns).
   - NEVER show full UUIDs in tables; use only the first 8 chars (e.g., `3d568a13...`) to keep tables narrow and readable.
   - Use Bulleted Lists for detailed item descriptions.
   - For file lists, always include the file size and creation date if available.

Context: User is managing their files on LinShare.
"""
    cl.user_session.set("system_prompt", system_prompt)
    cl.user_session.set("message_history", [SystemMessage(content=system_prompt)])

    await cl.Message(content=welcome_msg, author="LinShare Assistant").send()

@cl.on_message
async def on_message(message: cl.Message):
    # Remove the transcription signal message after user sends their real message
    last_trans_msg = cl.user_session.get("last_transcription_msg")
    if last_trans_msg:
        try:
            await last_trans_msg.remove()
        except:
            pass
        cl.user_session.set("last_transcription_msg", None)

    cl.user_session.set("last_call_key", None)
    session = cl.user_session.get("mcp_session")
    if not session:
        await cl.Message(content="⚠️ No active connection.").send()
        return

    # 🔄 Initialize session data for this turn
    system_prompt = cl.user_session.get("system_prompt")
    message_history = cl.user_session.get("message_history")
    
    # 🕒 Refresh Current Date in prompt (UTC) and update History
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    import re
    system_prompt = re.sub(r"Current Date: [^\n]+", f"Current Date: {now_str}", system_prompt)
    cl.user_session.set("system_prompt", system_prompt)
    
    if message_history and len(message_history) > 0:
        message_history[0].content = system_prompt

    # Handle File Uploads (Drag & Drop)
    if message.elements:
        for element in message.elements:
            if element.type == "file":
                await cl.Message(content=f"📤 Processing file: {element.name}...").send()
                # Manual chunked upload logic
                try:
                    with open(element.path, "rb") as f:
                        file_data = f.read()
                    
                    CHUNK_SIZE = 1024 * 1024 # 1MB
                    total_chunks = (len(file_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
                    msg_id = message.id
                    
                    last_res = ""
                    for i in range(total_chunks):
                        chunk = file_data[i*CHUNK_SIZE : (i+1)*CHUNK_SIZE]
                        b64_data = base64.b64encode(chunk).decode('utf-8')
                        
                        res = await session.call_tool(
                            "user_remote_upload_by_chunks",
                            arguments={
                                "filename": element.name,
                                "chunk_index": i,
                                "total_chunks": total_chunks,
                                "data_b64": b64_data,
                                "session_id": msg_id
                            }
                        )
                        if i == total_chunks - 1:
                            last_res = res.content[0].text if res.content else ""

                    await cl.Message(content=f"✅ Successfully uploaded {element.name}!").send()
                    
                    # 💡 Notify AI about the upload so it can act on it
                    if "uploaded successfully" in last_res.lower():
                        # Strip debug logs for AI history
                        clean_info = last_res.split("--- DETAILED HTTP DEBUG LOG ---")[0].strip()
                        message_history.append(AIMessage(content=f"[SYSTEM NOTIFICATION: The user attached a file which was just uploaded to LinShare]\n{clean_info}\n(I will use this UUID for the user's request)"))
                except Exception as e:
                     await cl.Message(content=f"❌ Upload failed: {e}").send()
        # Do NOT return here, allow the AI to process the message text (e.g. "share this file")
    # Choose LLM Provider via helper
    model = get_llm()
    model_name = getattr(model, "model", getattr(model, "model_name", "unknown"))
    
    message_history = cl.user_session.get("message_history")
    message_history.append(HumanMessage(content=message.content))
    
    MAX_ITERATIONS = 10
    iterations = 0
    final_content = ""

    import asyncio
    while iterations < MAX_ITERATIONS:
        iterations += 1
        try:
            active_messages = [message_history[0]] # System message
            if len(message_history) > 21:
                active_messages.extend(message_history[-20:])
            else:
                active_messages.extend(message_history[1:])

            # Retry logic for 429 Resource Exhausted
            response = None
            for retry in range(3):
                try:
                    print(f"📡 {model_name} turn {iterations} (Active Messages: {len(active_messages)})...")
                    response = await model.ainvoke(active_messages)
                    break
                except Exception as e:
                    if "429" in str(e) and retry < 2:
                        wait_time = (retry + 1) * 5
                        print(f"⏳ Rate limited (429). Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise e

            content = response.content
            print(f"🔹 {model_name} response content: {content!r}")
            print(f"🔹 {model_name} tool calls: {response.tool_calls}")

            # 🛠️ Fix: If model returns empty content after tool calls, it's likely confused or context is full.
            # We add a hint to force a summary instead of breaking with empty content.
            if not content and not response.tool_calls and iterations > 1:
                print(f"⚠️ Empty response at turn {iterations}. Forcing a summary prompt.")
                message_history.append(HumanMessage(content="[SYSTEM HINT: You provided an empty response. Please summarize the previous tool results for the user now.]"))
                continue

            message_history.append(response)

            # Loop Detection: Check if we've seen this exact response before in this turn
            call_key = f"{content}_{response.tool_calls}"
            if cl.user_session.get("last_call_key") == call_key:
                print(f"🛑 REPETITIVE CALL DETECTED. Breaking loop.")
                final_content = "⚠️ It seems I'm stuck in a loop trying to perform the same action. Here is what I know so far: " + str(message_history[-2].content if len(message_history) > 1 else "")
                break
            cl.user_session.set("last_call_key", call_key)

            has_tools = False

            # 1. Check for Native Tool Calls
            if response.tool_calls:
                print(f"🔸 Native Tool Calls detected")
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    args = tc["args"]
                    print(f"🛠️ Tool Call Request: {tool_name}({args})")
                    await cl.Message(content=f'<span class="tool-call-indicator">🤖 calling `{tool_name}`...</span>').send()
                    res = await session.call_tool(tool_name, arguments=args)
                    tool_output = res.content[0].text
                    
                    # ✂️ Truncate long tool outputs to avoid token overflow
                    if len(tool_output) > 10000:
                        print(f"✂️ Truncating tool output from {len(tool_output)} to 10000 chars")
                        tool_output = tool_output[:10000] + "... [TRUNCATED for brevity]"

                    print(f"📦 Tool Result ({len(tool_output)} chars): {tool_output[:100]}...")
                    message_history.append(HumanMessage(content=f"Tool '{tool_name}' returned: {tool_output}\n\nUser request was: '{message.content}'. Please provide the final response to the user now."))
                    has_tools = True
                if has_tools: continue

            # 2. Check for JSON-in-text fallback
            if content and "{" in content and "}" in content:
                print(f"🔸 JSON detection in turn {iterations}")
                try:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    data = json.loads(content[start:end])
                    
                    # Handle message field in JSON
                    if "message" in data and "tool" not in data:
                        final_content = data["message"]
                        break
                        
                    if "tool" in data:
                        tool_name = data["tool"]
                        args = data.get("arguments", {})
                        print(f"🛠️ JSON Tool Call Request: {tool_name}({args})")
                        await cl.Message(content=f'<span class="tool-call-indicator">🤖 calling `{tool_name}`...</span>').send()
                        res = await session.call_tool(tool_name, arguments=args)
                        tool_output = res.content[0].text
                        
                        # ✂️ Truncate long tool outputs to avoid token overflow
                        if len(tool_output) > 10000:
                            print(f"✂️ Truncating tool output from {len(tool_output)} to 10000 chars")
                            tool_output = tool_output[:10000] + "... [TRUNCATED for brevity]"

                        print(f"📦 Tool Result ({len(tool_output)} chars): {tool_output[:100]}...")
                        message_history.append(HumanMessage(content=f"Tool '{tool_name}' returned: {tool_output}\n\nUser request was: '{message.content}'. Please provide the final response to the user now."))
                        has_tools = True
                    if has_tools: continue
                except Exception as e:
                    print(f"⚠️ JSON Parse Error: {e}")

            # 3. If no tools were called and we have content, this is the final answer
            if content and content.strip():
                print(f"✅ Turn {iterations} yielded content. Breaking.")
                final_content = content
                break
            
            # If we reach here with no content and no tools, we continue to retry (or hit MAX_ITERATIONS)
            print(f"🔄 Turn {iterations} yielded no content and no tools. Continuing...")
            continue

        except Exception as e:
            print(f"❌ Error in turn {iterations}: {e}")
            if "429" in str(e):
                final_content = "⚠️ Gemini/Groq API Rate Limit Exceeded (429). Please wait a few seconds and try again."
            elif "413" in str(e):
                final_content = "⚠️ Request payload is too large for this model (413). Try a shorter query or clearing the chat."
            else:
                final_content = f"⚠️ Sorry, I encountered an error: {e}"
            break

    # Final cleanup & Display
    if not final_content or final_content.strip() == "":
         if iterations >= MAX_ITERATIONS:
             final_content = "⚠️ I've performed the requested actions (including tool calls) but reached the maximum conversation turns before I could provide a final verbal summary. Please let me know if you need more details about the results."
         else:
             final_content = "I've processed your request but don't have a verbal summary to show. Is there anything else?"
         
    await cl.Message(content=final_content, author="LinShare Assistant").send()

@cl.on_chat_end
async def on_chat_end():
    # Attempting to manually exit context managers usually fails in Chainlit due to loop mismatch.
    # It is safer to just let the session garbage collect or close naturally.
    pass
