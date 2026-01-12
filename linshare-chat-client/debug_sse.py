
import httpx
import asyncio

async def probe(url):
    print(f"--- Probing {url} ---")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Body Preview: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    print("\n")

async def main():
    base = "http://127.0.0.1:8100"
    await probe(f"{base}/")
    await probe(f"{base}/sse")
    await probe(f"{base}/sse/")
    await probe(f"{base}/messages") # Check if it's using messages endpoint?

if __name__ == "__main__":
    asyncio.run(main())
