import httpx
import logging

logger = logging.getLogger(__name__)

REQUIRED_HEADERS = {
    "strict-transport-security": {
        "severity": "high",
        "description": "HSTS header missing. Browsers are not forced to use HTTPS.",
        "remediation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
    },
    "content-security-policy": {
        "severity": "high",
        "description": "CSP header missing. XSS attacks may succeed.",
        "remediation": "Implement a Content-Security-Policy header tailored to your application.",
    },
    "x-content-type-options": {
        "severity": "medium",
        "description": "X-Content-Type-Options missing. MIME-type sniffing is enabled.",
        "remediation": "Add: X-Content-Type-Options: nosniff",
    },
    "x-frame-options": {
        "severity": "medium",
        "description": "X-Frame-Options missing. Clickjacking attacks are possible.",
        "remediation": "Add: X-Frame-Options: DENY  (or use CSP frame-ancestors)",
    },
    "referrer-policy": {
        "severity": "low",
        "description": "Referrer-Policy not set. Sensitive URLs may leak via Referer header.",
        "remediation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
    },
    "permissions-policy": {
        "severity": "low",
        "description": "Permissions-Policy header missing.",
        "remediation": "Restrict browser features with Permissions-Policy.",
    },
}

LEAK_HEADERS = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]


class HeadersScanner:
    """Checks HTTP security headers for best-practice compliance."""

    async def scan(self, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.head(url)
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return {"status_code": resp.status_code, "headers": headers}
        except httpx.RequestError as exc:
            logger.warning("Headers scan failed for %s: %s", url, exc)
            return {"error": str(exc)}

    def extract_findings(self, headers_data: dict) -> list[dict]:
        findings = []
        headers = headers_data.get("headers", {})

        for header, meta in REQUIRED_HEADERS.items():
            if header not in headers:
                findings.append({
                    "title": f"Missing Security Header: {header}",
                    "description": meta["description"],
                    "severity": meta["severity"],
                    "category": "http_headers",
                    "remediation": meta["remediation"],
                })

        for leak_header in LEAK_HEADERS:
            if leak_header in headers:
                findings.append({
                    "title": f"Information Disclosure via '{leak_header}' Header",
                    "description": (
                        f"The response exposes '{leak_header}: {headers[leak_header]}'. "
                        "Server version/technology disclosure helps attackers target known vulnerabilities."
                    ),
                    "severity": "low",
                    "category": "information_disclosure",
                    "details": {leak_header: headers[leak_header]},
                    "remediation": f"Remove or redact the '{leak_header}' response header.",
                })

        return findings
