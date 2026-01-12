
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
load_dotenv(dotenv_path=env_path)

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
6. 📝 RESPONSE: If you call a tool, the entire response MUST be the JSON block. Do not add conversational text around it.

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
    # Choose LLM Provider
    if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
        model_name = "deepseek-chat"
        model = ChatOpenAI(
            model=model_name,
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
            max_tokens=2048
        )
    elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
        model_name = "llama-3.3-70b-versatile"
        model = ChatGroq(
            model=model_name,
            api_key=GROQ_API_KEY,
            temperature=0
        )
    elif LLM_PROVIDER == "local" and LOCAL_LLM_URL:
        model_name = LOCAL_LLM_MODEL
        model = ChatOpenAI(
            model=model_name,
            api_key=LOCAL_LLM_API_KEY,
            base_url=LOCAL_LLM_URL,
            max_tokens=2048
        )
    else:
        # Default to Google Gemini
        model_name = "gemini-2.5-flash-lite" 
        model = ChatGoogleGenerativeAI(model=model_name, google_api_key=GOOGLE_API_KEY)
    
    message_history = cl.user_session.get("message_history")
    message_history.append(HumanMessage(content=message.content))
    
    MAX_ITERATIONS = 5
    iterations = 0
    final_content = ""

    import asyncio
    while iterations < MAX_ITERATIONS:
        iterations += 1
        try:
            # ✂️ Context Window Management: Keep System Message + Last 6 messages
            # (To avoid Groq 413 Payload Too Large)
            active_messages = [message_history[0]] # System message
            if len(message_history) > 7:
                active_messages.extend(message_history[-6:])
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
            message_history.append(response)

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
                    message_history.append(HumanMessage(content=f"Tool '{tool_name}' result:\n{tool_output}\n\nPlease summarize this for the user."))
                continue

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
                        message_history.append(HumanMessage(content=f"Tool '{tool_name}' result:\n{tool_output}\n\nPlease summarize this for the user."))
                        continue
                except Exception as e:
                    print(f"⚠️ JSON Parse Error: {e}")

            # 3. If no tools were called, this is the final answer
            print(f"✅ Turn {iterations} yielded no tools. Breaking.")
            final_content = content
            break

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
         final_content = "I've processed your request but don't have a verbal summary to show. Is there anything else?"
         
    await cl.Message(content=final_content, author="LinShare Assistant").send()

@cl.on_chat_end
async def on_chat_end():
    # Attempting to manually exit context managers usually fails in Chainlit due to loop mismatch.
    # It is safer to just let the session garbage collect or close naturally.
    pass
