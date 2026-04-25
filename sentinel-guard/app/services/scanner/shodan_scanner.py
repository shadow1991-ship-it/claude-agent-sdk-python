import asyncio
import logging
import shodan
from app.core.config import settings

logger = logging.getLogger(__name__)


class ShodanScanner:
    """Passive reconnaissance using the Shodan API."""

    def __init__(self) -> None:
        self._api = shodan.Shodan(settings.SHODAN_API_KEY) if settings.SHODAN_API_KEY else None

    async def scan_host(self, target: str) -> dict:
        if not self._api:
            logger.warning("Shodan API key not configured — skipping passive scan")
            return {"error": "Shodan not configured"}

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._api.host, target)
            return self._normalize(result)
        except shodan.APIError as exc:
            logger.warning("Shodan error for %s: %s", target, exc)
            return {"error": str(exc)}

    async def search_domain(self, domain: str) -> dict:
        if not self._api:
            return {"error": "Shodan not configured"}

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, lambda: self._api.search(f"hostname:{domain}")
            )
            return {
                "total": result.get("total", 0),
                "hosts": [self._normalize(h) for h in result.get("matches", [])[:20]],
            }
        except shodan.APIError as exc:
            logger.warning("Shodan domain search error for %s: %s", domain, exc)
            return {"error": str(exc)}

    def _normalize(self, host: dict) -> dict:
        return {
            "ip": host.get("ip_str"),
            "org": host.get("org"),
            "isp": host.get("isp"),
            "country": host.get("country_name"),
            "city": host.get("city"),
            "os": host.get("os"),
            "hostnames": host.get("hostnames", []),
            "domains": host.get("domains", []),
            "ports": host.get("ports", []),
            "vulns": list(host.get("vulns", {}).keys()),
            "services": [
                {
                    "port": svc.get("port"),
                    "transport": svc.get("transport"),
                    "product": svc.get("product"),
                    "version": svc.get("version"),
                    "banner": svc.get("data", "")[:500],
                    "cpe": svc.get("cpe", []),
                }
                for svc in host.get("data", [])
            ],
            "last_update": host.get("last_update"),
        }

    def extract_findings(self, shodan_data: dict) -> list[dict]:
        findings = []

        for vuln in shodan_data.get("vulns", []):
            findings.append({
                "title": f"Known Vulnerability: {vuln}",
                "description": f"Shodan detected {vuln} associated with this host.",
                "severity": "high",
                "category": "vulnerability",
                "reference": vuln,
            })

        open_ports = shodan_data.get("ports", [])
        risky = {21: "FTP", 23: "Telnet", 3389: "RDP", 445: "SMB", 1433: "MSSQL", 3306: "MySQL"}
        for port, service in risky.items():
            if port in open_ports:
                findings.append({
                    "title": f"Exposed {service} Port ({port})",
                    "description": (
                        f"Port {port} ({service}) is publicly accessible. "
                        "This service should not be exposed to the internet without strict controls."
                    ),
                    "severity": "medium" if service not in ("Telnet", "FTP") else "high",
                    "category": "exposure",
                    "details": {"port": port, "service": service},
                    "remediation": f"Restrict access to port {port} via firewall rules or VPN.",
                })

        return findings
