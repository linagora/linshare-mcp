import subprocess
import json
import time
import sys

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
    print(f"Sent: {method}")

def read_response(process, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        line = process.stdout.readline()
        if line:
            try:
                resp = json.loads(line)
                print(f"Received: {json.dumps(resp, indent=2)}")
                return resp
            except json.JSONDecodeError:
                print(f"Non-JSON output: {line.strip()}")
        
        # Check stderr
        while True:
            err_line = process.stderr.readline()
            if not err_line:
                break
            print(f"Stderr: {err_line.strip()}")
            
        time.sleep(0.1)
    print("Timeout waiting for response")
    return None

def main():
    cmd = [
        "/home/walidboudiche/mcp-servers/.venv/bin/python",
        "-m", "linshare_mcp.main"
    ]
    env = {
        "PYTHONPATH": "/home/walidboudiche/mcp-servers",
        "LINSHARE_USER_URL": "https://user.linshare-6-3-on-commit.integration-linshare.org/linshare/webservice/rest/user/v5",
        "LINSHARE_JWT_TOKEN": "eyJhbGciOiJSUzUxMiJ9.eyJkb21haW4iOiIzNzcyNjRlNi1hYWUwLTRlOTQtOTMwNy1iMjlhZTQzMWVhYjQiLCJ1dWlkIjoiM2YxY2MwODktZTQ3OS00ZDk2LTk4ZjAtZDM5OWEwMmI2NzM2Iiwic3ViIjoiYWJiZXkuY3VycnlAbGluc2hhcmUub3JnIiwiaWF0IjoxNzY2MDExMzE0LCJpc3MiOiJMaW5TaGFyZSJ9.mOKOD_PHceh-d17tJE93odIxQzaah33TsY_Qjxn4LlX8DzCvm3QAlCR13lLSL8R6UUjisJa6OUUJ6fpC6laNYty2P9V_28J84KfpDEL2LVWAB1RKwHmRmQr-mfkrkyGc8R8PTtwFNgm2tVOwU1n0kJ13ELkqRjMuoOT7Uz1fDZz0Hp9mKa1zaXqYHTzgIniXXhzi7RIICd3ACI1N9xRhsjQ-Xgue_P8ZoN3Uhplc59SWl343vlsDPg-OCVXWPeDr3GErejuSJZoH3fjDurmQYwEAMWb04D0QeBJs2hvO_vAX0jIC4lkpLx6mTZj6JkjUY5QX_oDSfK_EoxbknxEgKw"
    }
    
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
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        print("Sent: notifications/initialized")
        
        # 3. List tools, prompts, and resources in parallel
        send_request(process, "tools/list", request_id=1)
        send_request(process, "prompts/list", request_id=2)
        send_request(process, "resources/list", request_id=3)
        
        read_response(process, timeout=10) # tools
        read_response(process, timeout=10) # prompts
        read_response(process, timeout=10) # resources
        
    finally:
        process.terminate()

if __name__ == "__main__":
    main()
