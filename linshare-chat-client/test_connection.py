
import asyncio
import httpx

async def test_raw_sse(url):
    print(f"\n--- Probng Raw SSE: {url} ---")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            async with client.stream("GET", url, headers={"Accept": "text/event-stream"}, follow_redirects=True) as response:
                print(f"Status: {response.status_code}")
                print(f"Headers: {response.headers}")
                print(f"History (Redirects): {[r.status_code for r in response.history]}")
                
                if response.status_code == 200 and "text/event-stream" in response.headers.get("content-type", ""):
                    print("✅ SUCCESS! Valid SSE Stream detected.")
                    # Try to read a bit
                    async for chunk in response.aiter_lines():
                        print(f"Received chunk: {chunk!r}")
                        break # Just one is enough
                    return True
                else:
                    print("❌ Invalid Response (Not SSE)")
                    return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

async def main():
    # Test valid endpointcandidates
    await test_raw_sse("http://127.0.0.1:8100/sse")
    
if __name__ == "__main__":
    asyncio.run(main())
