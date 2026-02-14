"""Test only token acquisition."""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

async def main():
    url = "https://cloud.uipath.com/lackmann/identity_/connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("UIPATH_CLIENT_ID"),
        "client_secret": os.getenv("UIPATH_CLIENT_SECRET"),
        "scope": "OR.Jobs",
    }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
        r = await http.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        print("Status:", r.status_code)
        print("Final URL:", r.url)
        print("Headers:", dict(r.headers))
        print("Body (first 500 chars):", r.text[:500] if r.text else "(empty)")
        if r.status_code == 200:
            try:
                j = r.json()
                print("Token OK, expires_in:", j.get("expires_in"))
            except Exception as e:
                print("JSON parse failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
