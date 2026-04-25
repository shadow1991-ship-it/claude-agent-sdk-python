"""
Shared Sentinel Guard API client — used by dashboard and bot.
"""

import os
import httpx
from typing import Any

SENTINEL_BASE_URL = os.getenv("SENTINEL_API_URL", "http://localhost:8000/api/v1")
_token_cache: dict[str, str] = {}


class SentinelClient:
    def __init__(self, base_url: str = SENTINEL_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self._access_token: str | None = None

    def _headers(self) -> dict:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    def login(self, email: str, password: str) -> bool:
        try:
            r = httpx.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            if r.status_code == 200:
                self._access_token = r.json()["access_token"]
                return True
        except Exception:
            pass
        return False

    def get_assets(self) -> list[dict]:
        return self._get("/assets")

    def get_scans(self, asset_id: str | None = None) -> list[dict]:
        url = "/scans"
        if asset_id:
            url += f"?asset_id={asset_id}"
        return self._get(url)

    def get_scan(self, scan_id: str) -> dict:
        return self._get(f"/scans/{scan_id}")

    def request_scan(self, asset_id: str, scan_type: str = "full") -> dict:
        return self._post("/scans", {"asset_id": asset_id, "scan_type": scan_type})

    def get_reports(self) -> list[dict]:
        return self._get("/reports")

    def generate_report(self, scan_id: str) -> dict:
        return self._post(f"/reports/generate/{scan_id}", {})

    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url.replace('/api/v1', '')}/health", timeout=5)
            return r.json()
        except Exception:
            return {"status": "offline"}

    def stats(self) -> dict:
        """Aggregate stats: asset count, scan counts by status, total findings."""
        assets = self.get_assets()
        scans = self.get_scans()

        verified = sum(1 for a in assets if a.get("verification_status") == "verified")
        completed = [s for s in scans if s.get("status") == "completed"]
        failed = [s for s in scans if s.get("status") == "failed"]
        queued = [s for s in scans if s.get("status") in ("queued", "running")]

        avg_risk = 0.0
        risk_scores = [s["risk_score"] for s in completed if s.get("risk_score") is not None]
        if risk_scores:
            avg_risk = round(sum(risk_scores) / len(risk_scores), 1)

        return {
            "assets_total": len(assets),
            "assets_verified": verified,
            "scans_completed": len(completed),
            "scans_failed": len(failed),
            "scans_queued": len(queued),
            "avg_risk_score": avg_risk,
            "api_status": self.health().get("status", "unknown"),
        }

    def latest_findings(self, limit: int = 10) -> list[dict]:
        scans = self.get_scans()
        completed = sorted(
            [s for s in scans if s.get("status") == "completed"],
            key=lambda s: s.get("created_at", ""),
            reverse=True,
        )
        findings = []
        for scan in completed[:5]:
            detail = self.get_scan(scan["id"])
            for f in detail.get("findings", []):
                f["asset_id"] = scan.get("asset_id")
                f["scan_id"] = scan["id"]
                findings.append(f)
            if len(findings) >= limit:
                break
        return findings[:limit]

    def _get(self, path: str) -> list | dict:
        try:
            r = httpx.get(f"{self.base_url}{path}", headers=self._headers(), timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return []

    def _post(self, path: str, body: dict) -> dict:
        try:
            r = httpx.post(
                f"{self.base_url}{path}",
                json=body,
                headers=self._headers(),
                timeout=15,
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}


def get_client() -> SentinelClient:
    """Returns an authenticated client using env credentials."""
    client = SentinelClient()
    email = os.getenv("SENTINEL_EMAIL", "")
    password = os.getenv("SENTINEL_PASSWORD", "")
    if email and password:
        client.login(email, password)
    return client
