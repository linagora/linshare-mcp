
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

URL = os.getenv("LOCAL_LLM_URL")
KEY = os.getenv("LOCAL_LLM_API_KEY", "not-needed")
MODEL = os.getenv("LOCAL_LLM_MODEL", "local-model")

def test_url(base_url):
    print(f"\n--- Testing Base URL: {base_url} ---")
    
    # 1. Probe models
    try:
        models_url = f"{base_url}/models"
        print(f"📡 Probing {models_url}")
        resp = requests.get(models_url, headers={"Authorization": f"Bearer {KEY}"}, timeout=5)
        print(f"🔢 Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ Models endpoint is reachable.")
            try:
                data = resp.json()
                models = [m.get('id') for m in data.get('data', [])]
                print(f"🤖 Available Models: {models}")
            except:
                print(f"📄 Note: models returned 200 but not standard JSON (could be a splash page).")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 2. Probe Chat Completion
    chat_url = f"{base_url}/chat/completions"
    print(f"📡 Testing POST {chat_url}")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
    }
    try:
        resp = requests.post(
            chat_url,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        print(f"🔢 Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"✅ SUCCESS! model responded.")
            return True
        else:
            print(f"❌ FAILED: {resp.status_code} - {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    if not URL:
        print("❌ ERROR: LOCAL_LLM_URL not set.")
        return

    # Try original
    clean_url = URL.rstrip('/')
    success = test_url(clean_url)
    
    if not success:
        # Try /api (Common for Open WebUI / Linagora AI)
        if not clean_url.endswith('/api'):
            alt_url = clean_url.replace('/v1', '') # Strip /v1 if present
            alt_url = alt_url.rstrip('/') + '/api'
            print(f"\n💡 Trying Open WebUI style URL: {alt_url}")
            test_url(alt_url)

if __name__ == "__main__":
    main()
