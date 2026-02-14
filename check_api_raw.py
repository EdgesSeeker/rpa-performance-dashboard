"""Fetch raw Jobs API response to verify Robot/MachineName structure."""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

async def main():
    token_url = "https://cloud.uipath.com/lackmann/identity_/connect/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("UIPATH_CLIENT_ID"),
        "client_secret": os.getenv("UIPATH_CLIENT_SECRET"),
        "scope": "OR.Jobs OR.Robots OR.Machines",
    }
    async with httpx.AsyncClient(timeout=30.0) as http:
        tr = await http.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        tr.raise_for_status()
        token = tr.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-UIPATH-OrganizationUnitId": os.getenv("UIPATH_FOLDER_ID", "5719144"),
    }
    # First fetch Machines to build Id -> Name map (Host names like RPA-DONALD-001)
    machines_url = "https://cloud.uipath.com/lackmann/DefaultTenant/orchestrator_/odata/Machines?$top=50"
    async with httpx.AsyncClient(timeout=30.0) as http:
        mr = await http.get(machines_url, headers=headers)
        mr.raise_for_status()
        machines_data = mr.json()
    machine_map = {}
    for m in machines_data.get("value", []):
        mid = m.get("Id")
        name = m.get("Name")
        if mid is not None and name:
            machine_map[mid] = name
    print("Machines (relevant):", {k: v for k, v in machine_map.items() if "RPA-" in v})

    # Robots API: Robot Id -> MachineId mapping
    robots_url = "https://cloud.uipath.com/lackmann/DefaultTenant/orchestrator_/odata/Robots?$top=100"
    async with httpx.AsyncClient(timeout=30.0) as http:
        rr = await http.get(robots_url, headers=headers)
        rr.raise_for_status()
        robots_data = rr.json()
    robot_to_machine: dict[int, int] = {}
    for r in robots_data.get("value", []):
        rid, mid = r.get("Id"), r.get("MachineId")
        if rid is not None and mid is not None:
            robot_to_machine[rid] = mid
    # Filter to robots that map to RPA machines
    rpa_robot_info = []
    for r in robots_data.get("value", []):
        mid = r.get("MachineId")
        mname = machine_map.get(mid, "") if mid else ""
        if "RPA-DONALD" in mname or "RPA-MICKEY" in mname or "RPA-MICKY" in mname:
            rpa_robot_info.append({"Id": r.get("Id"), "Name": r.get("Name"), "MachineId": mid, "MachineName": mname})
    print("RPA Robots (Donald/Mickey):", rpa_robot_info)

    url = "https://cloud.uipath.com/lackmann/DefaultTenant/orchestrator_/odata/Jobs?$top=30&$expand=Robot&$orderby=StartTime desc"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as http:
        r = await http.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
    for i, item in enumerate(data.get("value", [])[:5]):
        robot = item.get("Robot") or {}
        print(f"\n--- Job {i+1} ---")
        print("Robot keys:", list(robot.keys()))
        machine_id = robot.get("MachineId")
        machine_name = robot.get("MachineName") or (machine_map.get(machine_id) if machine_id else None)
        print("Robot.Id:", robot.get("Id"))
        print("Robot.Name:", robot.get("Name"))
        print("Robot.ExternalName:", robot.get("ExternalName"))
        print("Robot.MachineId:", machine_id)
        print("Robot.MachineName:", robot.get("MachineName"))
        print("Machine lookup (Id->Name):", machine_name)
        print("ReleaseName:", item.get("ReleaseName"))
        print("StartTime:", item.get("StartTime"))

if __name__ == "__main__":
    asyncio.run(main())
