"""Get Folders to find FolderId for Jobs API."""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

async def main():
    # Get token
    token_url = "https://cloud.uipath.com/lackmann/identity_/connect/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("UIPATH_CLIENT_ID"),
        "client_secret": os.getenv("UIPATH_CLIENT_SECRET"),
        "scope": "OR.Jobs OR.Folders",
    }
    async with httpx.AsyncClient(timeout=30.0) as http:
        tr = await http.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        tr.raise_for_status()
        token = tr.json()["access_token"]

    # Get Folders - no folder header needed for /odata/Folders
    org = "lackmann"
    tenant = "DefaultTenant"
    folders_url = f"https://cloud.uipath.com/{org}/{tenant}/orchestrator_/odata/Folders?$top=20"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as http:
        r = await http.get(
            folders_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        print("Folders Status:", r.status_code)
        print("Body:", r.text[:1500] if r.text else "(empty)")
        if r.status_code == 200:
            j = r.json()
            for f in j.get("value", []):
                print("Folder:", f.get("DisplayName"), "| Id:", f.get("Id"), "| Key:", f.get("Key"), "| Path:", f.get("Path"))

if __name__ == "__main__":
    asyncio.run(main())
