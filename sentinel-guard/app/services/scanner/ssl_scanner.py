import asyncio
import ssl
import socket
import logging
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class SSLScanner:
    """Checks TLS/SSL certificate validity, expiry, and cipher strength."""

    async def scan(self, hostname: str, port: int = 443) -> dict:
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._check, hostname, port),
                timeout=30,
            )
            return result
        except asyncio.TimeoutError:
            return {"error": "SSL check timed out"}
        except Exception as exc:
            logger.warning("SSL scan failed for %s:%s — %s", hostname, port, exc)
            return {"error": str(exc)}

    def _check(self, hostname: str, port: int) -> dict:
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=15) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cipher = ssock.cipher()
                    protocol = ssock.version()
        except ssl.SSLCertVerificationError as exc:
            return {"valid": False, "error": str(exc)}

        cert = x509.load_der_x509_certificate(cert_der, default_backend())
        now = datetime.now(timezone.utc)

        not_after = cert.not_valid_after_utc
        days_left = (not_after - now).days

        return {
            "valid": True,
            "subject": cert.subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "not_before": cert.not_valid_before_utc.isoformat(),
            "not_after": not_after.isoformat(),
            "days_until_expiry": days_left,
            "serial_number": str(cert.serial_number),
            "protocol": protocol,
            "cipher": cipher[0] if cipher else None,
            "cipher_bits": cipher[2] if cipher else None,
            "san": self._get_san(cert),
        }

    def _get_san(self, cert: x509.Certificate) -> list[str]:
        try:
            ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            return [str(name.value) for name in ext.value]
        except x509.ExtensionNotFound:
            return []

    def extract_findings(self, ssl_data: dict) -> list[dict]:
        findings = []

        if ssl_data.get("error"):
            findings.append({
                "title": "SSL Certificate Error",
                "description": ssl_data["error"],
                "severity": "critical",
                "category": "ssl",
                "remediation": "Ensure a valid, trusted SSL certificate is installed.",
            })
            return findings

        days = ssl_data.get("days_until_expiry", 999)
        if days <= 0:
            findings.append({
                "title": "SSL Certificate Expired",
                "description": f"The certificate expired {abs(days)} days ago.",
                "severity": "critical",
                "category": "ssl",
                "remediation": "Renew the SSL certificate immediately.",
            })
        elif days <= 14:
            findings.append({
                "title": f"SSL Certificate Expiring Soon ({days} days)",
                "description": "Certificate will expire within 14 days.",
                "severity": "high",
                "category": "ssl",
                "remediation": "Renew the certificate before it expires.",
            })
        elif days <= 30:
            findings.append({
                "title": f"SSL Certificate Expiring in {days} Days",
                "description": "Certificate will expire within 30 days.",
                "severity": "medium",
                "category": "ssl",
                "remediation": "Plan certificate renewal.",
            })

        protocol = ssl_data.get("protocol", "")
        if protocol in ("TLSv1", "TLSv1.1", "SSLv3", "SSLv2"):
            findings.append({
                "title": f"Deprecated TLS Protocol: {protocol}",
                "description": f"{protocol} is deprecated and has known vulnerabilities.",
                "severity": "high",
                "category": "ssl",
                "remediation": "Disable TLS 1.0/1.1 and enforce TLS 1.2+.",
            })

        weak_ciphers = ("RC4", "DES", "3DES", "NULL", "EXPORT", "anon")
        cipher = ssl_data.get("cipher", "") or ""
        if any(w in cipher.upper() for w in weak_ciphers):
            findings.append({
                "title": f"Weak Cipher Suite: {cipher}",
                "description": "A weak or deprecated cipher is in use.",
                "severity": "high",
                "category": "ssl",
                "remediation": "Configure the server to use strong cipher suites (AES-GCM, CHACHA20).",
            })

        return findings
