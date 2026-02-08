import asyncio
import os
import json
import sys
import traceback
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

# Load environment variables from .env (root and client folder)
load_dotenv()
load_dotenv("linshare-chat-client/.env")

# Project root for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").lower()
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "not-needed")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3")

# LinShare Credentials for Auth Separation
USER_JWT = os.getenv("LINSHARE_JWT_TOKEN")
ADMIN_USER = os.getenv("LINSHARE_USERNAME")
ADMIN_PASS = os.getenv("LINSHARE_PASSWORD")

TEST_CASES = [
    {
        "name": "User Identity Check",
        "prompt": "Who am I logged in as on LinShare?",
        "expected_tools": ["user_get_current_user_info"],
        "mode": "user"
    },
    {
        "name": "User List Documents",
        "prompt": "Show me the files in my personal space.",
        "expected_tools": ["list_my_documents"],
        "mode": "user"
    },
    {
        "name": "Admin Audit Logs",
        "prompt": "Search audit logs for user admin@linshare.org for today.",
        "expected_tools": ["search_user_audit_logs"],
        "mode": "admin"
    }
]

def get_model():
    """Initializes the LLM based on environment configuration."""
    if LLM_PROVIDER == "local" and LOCAL_LLM_URL:
        print(f"🤖 Using Local LLM ({LOCAL_LLM_MODEL}) at {LOCAL_LLM_URL}")
        return ChatOpenAI(
            model=LOCAL_LLM_MODEL,
            api_key=LOCAL_LLM_API_KEY,
            base_url=LOCAL_LLM_URL,
            max_tokens=2048
        )
    else:
        print(f"🤖 Using Google Gemini (gemini-1.5-flash)")
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)

def get_server_env(mode: str) -> Dict[str, str]:
    """Provides a clean environment for the server instance based on auth mode."""
    env = os.environ.copy()
    # Remove both to be safe, then add back only needed one
    env.pop("LINSHARE_JWT_TOKEN", None)
    env.pop("LINSHARE_USERNAME", None)
    env.pop("LINSHARE_PASSWORD", None)
    
    if mode == "user":
        if not USER_JWT:
            raise ValueError("LINSHARE_JWT_TOKEN missing for user mode test.")
        env["LINSHARE_JWT_TOKEN"] = USER_JWT
        env["LINSHARE_MCP_MODE"] = "user"
    elif mode == "admin":
        if not (ADMIN_USER and ADMIN_PASS):
            raise ValueError("LINSHARE_USERNAME/PASSWORD missing for admin mode test.")
        env["LINSHARE_USERNAME"] = ADMIN_USER
        env["LINSHARE_PASSWORD"] = ADMIN_PASS
        env["LINSHARE_MCP_MODE"] = "admin"
    
    return env

async def run_test_case(model: Any, test_case: Dict[str, Any]):
    print(f"\n🧪 Running Test: {test_case['name']} (Mode: {test_case['mode'].upper()})")
    print(f"💬 Prompt: {test_case['prompt']}")
    
    # 1. Start a mode-specific MCP server instance
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "linshare_mcp.main"],
        env=get_server_env(test_case['mode'])
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 2. Get tools and bind to model
                tools_resp = await session.list_tools()
                lc_tools = [{"name": t.name, "description": t.description, "parameters": t.inputSchema} for t in tools_resp.tools]
                model_with_tools = model.bind_tools(lc_tools)
                
                # 3. Ask the model
                system_prompt = f"You are a LinShare Assistant. You are currently in {test_case['mode']} mode. Only used tools that start with {test_case['mode']}_ or common tools."
                messages = [SystemMessage(content=system_prompt), HumanMessage(content=test_case['prompt'])]
                
                response = await model_with_tools.ainvoke(messages)
                
                # 4. Check tool selection
                called_tools = [tc["name"] for tc in response.tool_calls] if hasattr(response, "tool_calls") else []
                print(f"🤖 Intent: AI selected tools: {called_tools}")
                
                selection_ok = all(expected in called_tools for expected in test_case['expected_tools'])
                if not selection_ok:
                    print(f"❌ Selection Fail: Missing {test_case['expected_tools']}")
                    return False

                # 5. EXECUTION: Actually call the tools on the server
                print("⚙️ Executing tools E2E...")
                for tool_call in response.tool_calls:
                    result = await session.call_tool(tool_call["name"], tool_call["args"])
                    # Check for errors in result content
                    result_text = result.content[0].text if result.content else ""
                    if "error" in result_text.lower() and "401" in result_text:
                        print(f"❌ Execution Fail: 401 Unauthorized during tool call")
                        return False
                    print(f"✅ Tool {tool_call['name']} executed successfully")

                print("✅ Pass (Intent + Execution)")
                return True

    except Exception as e:
        print(f"💥 Error: {e}")
        traceback.print_exc()
        return False

async def main():
    print("🚀 Starting LinShare MCP Automated Test Runner (E2E + Multi-Auth)...")
    model = get_model()
    
    results = []
    for tc in TEST_CASES:
        res = await run_test_case(model, tc)
        results.append(res)
    
    print("\n" + "="*40)
    print(f"📊 FINAL REPORT: {sum(results)}/{len(results)} Passed")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
