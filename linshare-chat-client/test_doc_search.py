import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Load settings from the main .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

LINSHARE_USER_URL = os.getenv("LINSHARE_USER_URL")
LINSHARE_JWT_TOKEN = os.getenv("LINSHARE_JWT_TOKEN")

if not LINSHARE_USER_URL or not LINSHARE_JWT_TOKEN:
    print("Error: LINSHARE_USER_URL or LINSHARE_JWT_TOKEN not set in .env")
    exit(1)

headers = {
    'Authorization': f'Bearer {LINSHARE_JWT_TOKEN}',
    'Accept': 'application/json'
}

def test_pattern(pattern):
    url = f"{LINSHARE_USER_URL}/documents"
    params = {'pattern': pattern}
    print(f"Testing {url} with pattern='{pattern}'...")
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        docs = resp.json()
        print(f"Found {len(docs)} documents.")
        if docs:
            for d in docs[:5]:
                print(f"- {d.get('name')}")
    except Exception as e:
        print(f"Failed: {e}")

test_pattern("deployment")
test_pattern("")
