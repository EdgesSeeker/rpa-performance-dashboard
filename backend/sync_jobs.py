"""
Sync jobs from UiPath Orchestrator into the local SQLite DB.
Run: python -m backend.sync_jobs [days]
Default: last 90 days. For Streamlit Cloud use fewer days (e.g. 30) to avoid timeout.
"""
import asyncio
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from backend.clients.uipath_client import UiPathClient
from backend.database import SessionLocal, Job, init_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _make_client() -> UiPathClient:
    client_id = os.getenv("UIPATH_CLIENT_ID")
    client_secret = os.getenv("UIPATH_CLIENT_SECRET")
    tenant = os.getenv("UIPATH_TENANT_NAME", "DefaultTenant")
    org = os.getenv("UIPATH_ORG_SLUG", "lackmann")
    folder_id = os.getenv("UIPATH_FOLDER_ID")
    if not client_id or not client_secret:
        raise ValueError(
            "UIPATH_CLIENT_ID und UIPATH_CLIENT_SECRET fehlen. "
            "Lokal: in .env eintragen. Streamlit Cloud: App → Settings → Secrets (siehe README)."
        )
    return UiPathClient(
        client_id=client_id,
        client_secret=client_secret,
        tenant=tenant,
        org_slug=org,
        folder_id=int(folder_id) if folder_id else None,
    )


async def sync_jobs(days: int = 90) -> int:
    """
    Fetch jobs from UiPath for the last `days` days and upsert into jobs table.
    Returns number of jobs upserted.
    """
    init_tables()
    client = _make_client()
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    raw_jobs = await client.get_jobs(start_date, end_date)

    db = SessionLocal()
    try:
        count = 0
        for row in raw_jobs:
            job_key = str(row.get("job_key") or "")
            if not job_key:
                continue
            existing = db.query(Job).filter(Job.job_key == job_key).first()
            start_time = row.get("start_time")
            end_time = row.get("end_time")
            if not start_time:
                continue
            if existing:
                existing.robot_name = row.get("robot_name")
                existing.machine_name = row.get("machine_name")
                existing.process_name = row.get("process_name")
                existing.start_time = start_time
                existing.end_time = end_time
                existing.state = row.get("state")
            else:
                db.add(Job(
                    job_key=job_key,
                    robot_name=row.get("robot_name"),
                    machine_name=row.get("machine_name"),
                    process_name=row.get("process_name"),
                    start_time=start_time,
                    end_time=end_time,
                    state=row.get("state"),
                ))
            count += 1
        db.commit()
        logger.info("Synced %d jobs (%s to %s)", count, start_date, end_date)
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_sync(days: int = 90) -> int:
    """Synchronous entry point for use from Streamlit. Returns number of jobs synced."""
    return asyncio.run(sync_jobs(days=days))


if __name__ == "__main__":
    days = 90
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    n = run_sync(days=days)
    print(f"Synced {n} jobs.")
