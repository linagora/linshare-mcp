import subprocess
import json
import time
import sys
import select

def send_msg(proc, msg):
    print(f"Sending: {json.dumps(msg)}", file=sys.stderr)
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()

def read_msg(proc, timeout=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if select.select([proc.stdout], [], [], 0.1)[0]:
            line = proc.stdout.readline()
            if line:
                print(f"Received: {line.strip()}", file=sys.stderr)
                return json.loads(line)
        
        # Also check stderr
        if select.select([proc.stderr], [], [], 0.1)[0]:
            err_line = proc.stderr.readline()
            if err_line:
                print(f"STDERR: {err_line.strip()}", file=sys.stderr)
    return None

env = {
    "PYTHONPATH": "/home/walidboudiche/mcp-servers",
    "LINSHARE_USER_URL": "https://user.linshare-6-3-on-commit.integration-linshare.org/linshare/webservice/rest/user/v5",
    "LINSHARE_JWT_TOKEN": "eyJhbGciOiJSUzUxMiJ9.eyJkb21haW4iOiIzNzcyNjRlNi1hYWUwLTRlOTQtOTMwNy1iMjlhZTQzMWVhYjQiLCJ1dWlkIjoiM2YxY2MwODktZTQ3OS00ZDk2LTk4ZjAtZDM5OWEwMmI2NzM2Iiwic3ViIjoiYWJiZXkuY3VycnlAbGluc2hhcmUub3JnIiwiaWF0IjoxNzY2MDExMzE0LCJpc3MiOiJMaW5TaGFyZSJ9.mOKOD_PHceh-d17tJE93odIxQzaah33TsY_Qjxn4LlX8DzCvm3QAlCR13lLSL8R6UUjisJa6OUUJ6fpC6laNYty2P9V_28J84KfpDEL2LVWAB1RKwHmRmQr-mfkrkyGc8R8PTtwFNgm2tVOwU1n0kJ13ELkqRjMuoOT7Uz1fDZz0Hp9mKa1zaXqYHTzgIniXXhzi7RIICd3ACI1N9xRhsjQ-Xgue_P8ZoN3Uhplc59SWl343vlsDPg-OCVXWPeDr3GErejuSJZoH3fjDurmQYwEAMWb04D0QeBJs2hvO_vAX0jIC4lkpLx6mTZj6JkjUY5QX_oDSfK_EoxbknxEgKw",
    "LINSHARE_UPLOAD_DIR": "/home/walidboudiche/Téléchargements/LinShareUploads",
    "LINSHARE_DOWNLOAD_DIR": "/home/walidboudiche/TéléchargementsLinShareDownloads"
}

proc = subprocess.Popen(
    ["/home/walidboudiche/mcp-servers/.venv/bin/python", "-m", "linshare_mcp.main"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
    text=True,
    bufsize=1
)

# Initialize
send_msg(proc, {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
})

init_resp = read_msg(proc)
if not init_resp:
    print("Failed to get initialize response", file=sys.stderr)
    sys.exit(1)

# List tools
send_msg(proc, {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
})

tools_resp = read_msg(proc, timeout=10)
if not tools_resp:
    print("Failed to get tools response", file=sys.stderr)
else:
    print("SUCCESS: Got tools response", file=sys.stderr)
    print(json.dumps(tools_resp))

proc.terminate()
