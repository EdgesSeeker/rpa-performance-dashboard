"""
UiPath Cloud Orchestrator API client: OAuth 2.0 + Jobs endpoint.
"""
import logging
from datetime import date, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# UiPath Automation Cloud: token via identity server (not account.uipath.com)
def _token_url(org_slug: str) -> str:
    return f"https://cloud.uipath.com/{org_slug}/identity_/connect/token"


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.rstrip("Z").replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


class UiPathClient:
    """Client for UiPath Automation Cloud Orchestrator API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        tenant: str,
        org_slug: str,
        folder_id: int | str | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant = tenant
        self.org_slug = org_slug
        self.folder_id = str(folder_id) if folder_id else None
        self._token: str | None = None
        self._token_expires: datetime | None = None
        self._base_url = f"https://cloud.uipath.com/{org_slug}/{tenant}/orchestrator_/"

    def _is_token_valid(self) -> bool:
        if not self._token or not self._token_expires:
            return False
        # Consider expired 5 min before actual expiry
        from datetime import timedelta
        return datetime.utcnow() < (self._token_expires - timedelta(minutes=5))

    async def get_access_token(self) -> str:
        """Get OAuth token; refresh if expired."""
        if self._is_token_valid():
            return self._token or ""

        url = _token_url(self.org_slug)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
            r = await http.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "OR.Jobs OR.Robots OR.Machines",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            r.raise_for_status()
            data = r.json()
            self._token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            self._token_expires = datetime.utcnow()
            self._token_expires = self._token_expires.replace(
                microsecond=0
            )  # type: ignore
            from datetime import timedelta
            self._token_expires = self._token_expires + timedelta(seconds=expires_in)
            logger.info("UiPath token refreshed")
            return self._token or ""

    async def get_jobs(
        self,
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        """
        Fetch jobs from Orchestrator for the given date range.
        Returns list of dicts with keys: job_key, robot_name, machine_name, process_name, start_time, end_time, state.
        """
        token = await self.get_access_token()
        # OData filter: StartTime >= date_from and StartTime <= date_to
        from_str = date_from.isoformat() + "T00:00:00Z"
        to_str = date_to.isoformat() + "T23:59:59Z"
        url = (
            f"{self._base_url}odata/Jobs"
            f"?$filter=StartTime ge {from_str} and StartTime le {to_str}"
            "&$orderby=StartTime asc"
            "&$expand=Robot"
        )
        all_rows: list[dict[str, Any]] = []
        skip = 0
        top = 100

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if self.folder_id:
            headers["X-UIPATH-OrganizationUnitId"] = self.folder_id
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as http:
            while True:
                page_url = f"{url}&$top={top}&$skip={skip}"
                try:
                    r = await http.get(page_url, headers=headers)
                    if r.status_code == 401:
                        self._token = None
                        self._token_expires = None
                        token = await self.get_access_token()
                        headers["Authorization"] = f"Bearer {token}"
                        r = await http.get(page_url, headers=headers)
                    r.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error("UiPath API error: %s %s", e.response.status_code, e.response.text)
                    raise

                data = r.json()
                value = data.get("value") or []
                if not value:
                    break
                for item in value:
                    robot = item.get("Robot") or {}
                    # HostMachineName = Host Name in Orchestrator (RPA-DONALD-001, RPA-MICKY-002)
                    machine_name = (
                        item.get("HostMachineName")
                        or robot.get("MachineName")
                        or ""
                    )
                    robot_name = robot.get("Name") or item.get("RuntimeType") or "Unknown"
                    start_dt = _parse_iso(item.get("StartTime"))
                    end_dt = _parse_iso(item.get("EndTime")) if item.get("EndTime") else None
                    all_rows.append({
                        "job_key": str(item.get("Key", "")),
                        "robot_name": robot_name,
                        "machine_name": str(machine_name).strip(),
                        "process_name": item.get("ReleaseName") or "",
                        "start_time": start_dt,
                        "end_time": end_dt,
                        "state": item.get("State") or "",
                    })
                skip += len(value)
                if len(value) < top:
                    break

        logger.info("Fetched %d jobs from UiPath", len(all_rows))
        return all_rows
