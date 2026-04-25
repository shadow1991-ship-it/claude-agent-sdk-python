import asyncio
import logging
import nmap3
from app.core.config import settings

logger = logging.getLogger(__name__)

# Safe default arguments — no SYN flood, no OS fingerprint without explicit opt-in
DEFAULT_ARGS = "-sV -sC --open -T4 --host-timeout 120s"


class NmapScanner:
    """Active port and service scanning using Nmap."""

    async def scan(self, target: str, arguments: str = DEFAULT_ARGS) -> dict:
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._run, target, arguments),
                timeout=settings.SCAN_TIMEOUT_SECONDS,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("Nmap scan timed out for %s", target)
            return {"error": "Scan timed out"}
        except Exception as exc:
            logger.error("Nmap error for %s: %s", target, exc)
            return {"error": str(exc)}

    def _run(self, target: str, arguments: str) -> dict:
        nm = nmap3.Nmap()
        raw = nm.scan_command(target, arg=arguments)
        return self._normalize(raw)

    def _normalize(self, raw: dict) -> dict:
        hosts = []
        for ip, data in raw.items():
            if not isinstance(data, dict):
                continue
            ports = []
            for port_info in data.get("ports", []):
                ports.append({
                    "port": port_info.get("portid"),
                    "protocol": port_info.get("protocol"),
                    "state": port_info.get("state"),
                    "service": port_info.get("service", {}).get("name"),
                    "product": port_info.get("service", {}).get("product"),
                    "version": port_info.get("service", {}).get("version"),
                    "scripts": port_info.get("scripts", []),
                })
            hosts.append({
                "ip": ip,
                "hostname": data.get("hostname", [{}])[0].get("name") if data.get("hostname") else None,
                "state": data.get("state", {}).get("state"),
                "ports": ports,
            })
        return {"hosts": hosts}

    def extract_findings(self, nmap_data: dict) -> list[dict]:
        findings = []
        for host in nmap_data.get("hosts", []):
            for port in host.get("ports", []):
                state = port.get("state", "")
                p = int(port.get("port", 0))
                service = port.get("service", "unknown")

                if state != "open":
                    continue

                # Unencrypted protocols
                plain_protocols = {21: "FTP", 23: "Telnet", 80: "HTTP", 25: "SMTP"}
                if p in plain_protocols:
                    findings.append({
                        "title": f"Unencrypted Protocol on Port {p} ({plain_protocols[p]})",
                        "description": (
                            f"{plain_protocols[p]} transmits data in plaintext. "
                            "Credentials and data are susceptible to interception."
                        ),
                        "severity": "high" if p == 23 else "medium",
                        "category": "cleartext_protocol",
                        "details": {"port": p, "service": service},
                        "remediation": (
                            "Replace with encrypted alternatives (SFTP, SSH, HTTPS, SMTPS)."
                        ),
                    })

                # Default database ports
                db_ports = {3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis"}
                if p in db_ports:
                    findings.append({
                        "title": f"Database Port {p} ({db_ports[p]}) Exposed",
                        "description": (
                            f"{db_ports[p]} is publicly reachable. "
                            "Database services should never be exposed directly to the internet."
                        ),
                        "severity": "critical",
                        "category": "exposure",
                        "details": {"port": p, "service": db_ports[p]},
                        "remediation": (
                            "Restrict port access to application servers only via firewall. "
                            "Use a VPN or private network for database access."
                        ),
                    })

                # Script findings (NSE scripts like vuln, auth)
                for script in port.get("scripts", []):
                    output = script.get("output", "")
                    if "VULNERABLE" in output.upper():
                        findings.append({
                            "title": f"NSE Script Finding on Port {p}: {script.get('id')}",
                            "description": output[:1000],
                            "severity": "high",
                            "category": "nse_vuln",
                            "details": {"port": p, "script_id": script.get("id")},
                        })

        return findings
