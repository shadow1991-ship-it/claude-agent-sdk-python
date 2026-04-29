"""
SBOM (Software Bill of Materials) scanner — inspired by Anchore Syft.
Generates SBOM for container images and checks packages against known CVEs via AI.
"""
import json
import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)


class SBOMScanner:
    """
    Generates SBOM for container images using Syft CLI (if available)
    and uses AI (DeepSeek V4 Pro) to identify CVEs in discovered packages.
    """

    async def scan(self, image_reference: str) -> dict:
        sbom = await self._generate_sbom(image_reference)
        if not sbom:
            return {"image": image_reference, "packages": [], "error": "Syft not available or image unreachable"}

        cve_findings = await self._check_cves_via_ai(sbom)
        return {
            "image": image_reference,
            "packages": sbom.get("artifacts", []),
            "package_count": len(sbom.get("artifacts", [])),
            "cve_findings": cve_findings,
        }

    def extract_findings(self, data: dict) -> list[dict]:
        findings = []
        for cve in data.get("cve_findings", []):
            findings.append({
                "title": f"Vulnerable package: {cve.get('package', 'unknown')}",
                "description": (
                    f"{cve.get('package')} {cve.get('current_version', '?')} "
                    f"has {cve.get('cve_id', 'CVE unknown')}: {cve.get('description', '')}"
                ),
                "severity": cve.get("severity", "high"),
                "category": "sbom-vulnerability",
                "reference": cve.get("cve_id"),
                "cvss_score": cve.get("cvss_score"),
                "details": {
                    "package": cve.get("package"),
                    "current_version": cve.get("current_version"),
                    "fixed_version": cve.get("fixed_version"),
                    "source": "sbom",
                },
                "remediation": f"Upgrade {cve.get('package')} to {cve.get('fixed_version', 'latest')}",
            })
        return findings

    async def _generate_sbom(self, image_reference: str) -> dict | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "syft", image_reference, "-o", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            if proc.returncode == 0:
                return json.loads(stdout)
        except FileNotFoundError:
            logger.info("Syft CLI not found — SBOM scan skipped")
        except Exception as exc:
            logger.warning("SBOM generation failed: %s", exc)
        return None

    async def _check_cves_via_ai(self, sbom: dict) -> list[dict]:
        if not settings.AI_ENABLED:
            return []

        packages = sbom.get("artifacts", [])[:30]  # limit for token budget
        package_summary = [
            {"name": p.get("name"), "version": p.get("version"), "type": p.get("type")}
            for p in packages
        ]

        from app.services.scanner.ai_scanner import ModelRouter
        router = ModelRouter()

        prompt = (
            "You are a CVE expert. Given this list of packages from a container SBOM, "
            "identify which ones have known CVEs. Return ONLY a JSON array of objects with: "
            "package, current_version, fixed_version, cve_id, severity, cvss_score, description. "
            f"Only report real CVEs.\n\nPackages:\n{json.dumps(package_summary, ensure_ascii=False)}"
        )
        raw = await router.deep(prompt)
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception:
            pass
        return []
