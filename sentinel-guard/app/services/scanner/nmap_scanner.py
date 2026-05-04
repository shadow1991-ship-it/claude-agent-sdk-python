import asyncio
import json
import logging
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from app.core.config import settings

logger = logging.getLogger(__name__)

# Safe default arguments — no SYN flood, no OS fingerprint without explicit opt-in
DEFAULT_ARGS = "-sV -sC --open -T4 --host-timeout 120s"


class NmapScanner:
    """Active port and service scanning using nmap CLI (no nmap3 dependency)."""

    async def scan(self, target: str, arguments: str = DEFAULT_ARGS) -> dict:
        if not shutil.which("nmap"):
            logger.warning("nmap binary not found — skipping port scan")
            return {"error": "nmap not installed", "hosts": []}
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._run, target, arguments),
                timeout=settings.SCAN_TIMEOUT_SECONDS,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("Nmap scan timed out for %s", target)
            return {"error": "Scan timed out", "hosts": []}
        except Exception as exc:
            logger.error("Nmap error for %s: %s", target, exc)
            return {"error": str(exc), "hosts": []}

    def _run(self, target: str, arguments: str) -> dict:
        cmd = ["nmap", "-oX", "-"] + arguments.split() + [target]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 and not proc.stdout.strip():
            return {"error": proc.stderr[:500], "hosts": []}
        return self._parse_xml(proc.stdout)

    def _parse_xml(self, xml_output: str) -> dict:
        hosts = []
        try:
            root = ET.fromstring(xml_output)
        except ET.ParseError:
            return {"hosts": []}
        for host_el in root.findall("host"):
            addr_el = host_el.find("address")
            ip = addr_el.get("addr", "") if addr_el is not None else ""
            state_el = host_el.find("status")
            state = state_el.get("state", "") if state_el is not None else ""
            hostname = ""
            for hn in host_el.findall("hostnames/hostname"):
                hostname = hn.get("name", "")
                break
            ports = []
            for port_el in host_el.findall("ports/port"):
                state_p = port_el.find("state")
                svc_el  = port_el.find("service")
                scripts = []
                for s in port_el.findall("script"):
                    scripts.append({"id": s.get("id"), "output": s.get("output", "")})
                ports.append({
                    "port":     port_el.get("portid"),
                    "protocol": port_el.get("protocol"),
                    "state":    state_p.get("state", "") if state_p is not None else "",
                    "service":  svc_el.get("name", "") if svc_el is not None else "",
                    "product":  svc_el.get("product", "") if svc_el is not None else "",
                    "version":  svc_el.get("version", "") if svc_el is not None else "",
                    "scripts":  scripts,
                })
            hosts.append({"ip": ip, "hostname": hostname, "state": state, "ports": ports})
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
