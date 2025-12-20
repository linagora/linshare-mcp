import subprocess
import json
import time
import sys
import os

def send_request(process, method, params=None, request_id=1):
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {}
    }
    msg = json.dumps(request) + "\n"
    process.stdin.write(msg)
    process.stdin.flush()

def read_response(process, timeout=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        line = process.stdout.readline()
        if line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
        time.sleep(0.1)
    return None

def main():
    cmd = [
        "/home/walidboudiche/mcp-servers/.venv/bin/python3",
        "-m", "linshare_mcp.main"
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "/home/walidboudiche/mcp-servers"
    # Set a dummy token to avoid auth_manager blocking if it still does
    env["LINSHARE_JWT_TOKEN"] = "dummy"
    env["LINSHARE_USER_URL"] = "http://localhost"
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1
    )
    
    try:
        # 1. Initialize
        send_request(process, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }, request_id=0)
        read_response(process)
        
        # 2. Initialized notification
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()
        
        # 3. List tools
        send_request(process, "tools/list", request_id=1)
        resp = read_response(process)
        
        if resp and "result" in resp and "tools" in resp["result"]:
            tools = resp["result"]["tools"]
            print(f"Total tools returned: {len(tools)}")
            print(f"Tool names: {[t['name'] for t in tools]}")
        else:
            print(f"Unexpected response: {resp}")
            
    finally:
        process.terminate()

if __name__ == "__main__":
    main()
