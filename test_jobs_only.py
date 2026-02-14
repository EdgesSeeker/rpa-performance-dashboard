"""Test Jobs API call only."""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

async def main():
    # Get token first
    token_url = "https://cloud.uipath.com/lackmann/identity_/connect/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("UIPATH_CLIENT_ID"),
        "client_secret": os.getenv("UIPATH_CLIENT_SECRET"),
        "scope": "OR.Jobs",
    }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
        tr = await http.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        tr.raise_for_status()
        token = tr.json()["access_token"]
        print("Token OK")

    # Call Jobs API - try DefaultTenant vs defaultenet
    org = os.getenv("UIPATH_ORG_SLUG", "lackmann")
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as http:
        for tenant in ["DefaultTenant", "defaultenet"]:
            jobs_url = f"https://cloud.uipath.com/{org}/{tenant}/orchestrator_/odata/Jobs?$top=5"
            print(f"\nTrying tenant: {tenant}")
            r = await http.get(
                jobs_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            print("Jobs Status:", r.status_code)
            if r.status_code == 302:
                print("Redirect Location:", r.headers.get("Location", ""))
            print("Body (first 400 chars):", r.text[:400] if r.text else "(empty)")
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                j = r.json()
                value = j.get("value", [])
                print("SUCCESS! Jobs count:", len(value))
                break

if __name__ == "__main__":
    asyncio.run(main())
