"""
Test UiPath API connection. Run: python test_api.py
"""
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

from backend.clients.uipath_client import UiPathClient


async def main() -> None:
    client_id = os.getenv("UIPATH_CLIENT_ID")
    client_secret = os.getenv("UIPATH_CLIENT_SECRET")
    tenant = os.getenv("UIPATH_TENANT_NAME", "DefaultTenant")
    org = os.getenv("UIPATH_ORG_SLUG", "lackmann")
    folder_id = os.getenv("UIPATH_FOLDER_ID")  # e.g. 5719144 for Lackmann
    if not client_id or not client_secret:
        print("ERROR: Set UIPATH_CLIENT_ID and UIPATH_CLIENT_SECRET in .env")
        sys.exit(1)
    client = UiPathClient(
        client_id=client_id,
        client_secret=client_secret,
        tenant=tenant,
        org_slug=org,
        folder_id=int(folder_id) if folder_id else None,
    )
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=1)
    today = date.today()
    try:
        jobs = await client.get_jobs(yesterday, today)
        print(f"OK: Fetched {len(jobs)} jobs from {yesterday} to {today}")
        if jobs:
            print("Sample:", jobs[0])
    except httpx.HTTPStatusError as e:
        body = e.response.text[:800] if e.response.text else ""
        print("ERROR:", e.response.status_code, "URL:", e.response.url)
        print("Body:", body)
        sys.exit(1)
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
