
# chat_client.py
import chainlit as cl
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
import httpx
import os
from pathlib import Path
import base64
import json
from dotenv import load_dotenv

# Load API Keys relative to script
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

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
print(f"   LLM Provider: {LLM_PROVIDER}")
print(f"   Transcription Provider: {TRANSCRIPTION_PROVIDER}")
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
    else:
        # Default to Google Gemini (Ensure 1.5-flash is used, 2.5 does not exist)
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

@cl.on_chat_start
async def on_chat_start():
    print(f"🔄 Connecting to SSE Server at: {MCP_SERVER_SSE_URL}")
    try:
        # Keep connection open manually
        sse_ctx = sse_client(MCP_SERVER_SSE_URL)
        streams = await sse_ctx.__aenter__()
        
        session_ctx = ClientSession(streams[0], streams[1])
        session = await session_ctx.__aenter__()
        await session.initialize()
        
        # Store contexts
        cl.user_session.set("session_ctx", session_ctx)
        cl.user_session.set("sse_ctx", sse_ctx)
        cl.user_session.set("mcp_session", session)

        # 1. Fetch available tools from MCP Server
        result = await session.list_tools()
        mcp_tools = result.tools
        
        # 2. Convert MCP tools to LangChain compatible tools
        langchain_tools = []
        for t in mcp_tools:
            # We create a dynamic wrapper for each tool
            async def dynamic_tool_func(*args, **kwargs):
                # This function is bound to the specific tool name
                tool_name = kwargs.pop('__tool_name')
                print(f"🛠️ Agent calling tool: {tool_name} with {kwargs}")
                res = await session.call_tool(tool_name, arguments=kwargs)
                return res.content[0].text

            # Create the structured tool definition
            # We need to construct the schema from t.inputSchema
            # For simplicity in this demo, we rely on the LLM to infer args or use a generic binding
            # A more robust implementation would convert JSON schema to Pydantic
            pass 
            
        # SIMPLE APPROACH:
        # We will use the 'bind_tools' capability of the model if we can convert the schema.
        # But converting dynamic JSON schema to LangChain tools on the fly is tricky.
        # INSTEAD: We will just give the LLM the raw tool definitions in the system prompt
        # and ask it to output JSON for tool calls.
        tool_descriptions = "\n".join([f"- {t.name}: {t.description} (Args: {t.inputSchema})" for t in mcp_tools])
        
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # --- NEW: User Context Injection ---
        welcome_msg = f"✅ Connected! I have access to {len(mcp_tools)} LinShare tools. Ask me anything!"
        user_context = ""
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
   - Need user details? Call 'user_get_current_user_info'.
   - Looking for a specific file? Call 'user_search_my_documents' with a name pattern. 
   - Need to check activities? Call 'user_search_audit'.
2. 🔒 AUTHENTICATION: You are AUTOMATICALLY logged in if a token is present. Do not ask for passwords/UUIDs unless a tool returns an AUTH ERROR.
3. 📅 TIME: Use the 'Current Date' above to calculate relative dates. 
   - CRITICAL: All date arguments for tools (like 'begin_date') MUST use the format: YYYY-MM-DDT00:00:00Z.
4. 📎 ATTACHED FILES: If a user attaches a file, the chat client automatically uploads it. 
   - Check the history for a 'BACKGROUND ACTION' notification.
   - Use the provided 'UUID' from that notification directly for sharing or moving.
   - Do NOT call 'list_upload_files' unless the user specifically mentions picking a file from the server's local disk.
5. 🛠️ PROACTIVE ACTION: Do NOT narrate your plan or explain what you are about to do. If you have enough information to call a tool (like listing documents or searching for a user), CALL IT IMMEDIATELY. Your goal is to reach the final objective in as few conversational turns as possible.
6. 📝 RESPONSE: If you need to use a tool, the entire response MUST be the JSON block only.
7. 🗣️ FINAL ANSWER: If you have all the information required to answer the user (e.g. after a tool has returned data), do NOT output JSON. Instead, provide a helpful and friendly response in plain Markdown.

Context: User is managing their files on LinShare.
"""
        cl.user_session.set("system_prompt", system_prompt)
        cl.user_session.set("tools_map", {t.name: t for t in mcp_tools})
        cl.user_session.set("message_history", [SystemMessage(content=system_prompt)])

        await cl.Message(content=welcome_msg, author="LinShare Assistant").send()

    except Exception as e:
        await cl.Message(content=f"❌ Connection Failed: {e}").send()

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
                    await cl.Message(content=f"🤖 calling `{tool_name}`...").send()
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
                        await cl.Message(content=f"🤖 calling `{tool_name}`...").send()
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
