import asyncio
import logging
from app.models.asset import Asset, AssetType
from app.models.scan import ScanType
from app.services.scanner.shodan_scanner import ShodanScanner
from app.services.scanner.nmap_scanner import NmapScanner, DEFAULT_ARGS
from app.services.scanner.ssl_scanner import SSLScanner
from app.services.scanner.headers_scanner import HeadersScanner
from app.services.scanner.dockerfile_scanner import DockerfileScanner
from app.services.scanner.sbom_scanner import SBOMScanner
from app.services.scanner.ai_scanner import AIScanner
from app.core.config import settings

logger = logging.getLogger(__name__)

SEVERITY_WEIGHT = {"critical": 40, "high": 20, "medium": 8, "low": 3, "info": 0}


class ScanOrchestrator:
    """Coordinates all scanners and produces a unified result."""

    def __init__(self) -> None:
        self.shodan = ShodanScanner()
        self.nmap = NmapScanner()
        self.ssl = SSLScanner()
        self.headers = HeadersScanner()
        self.dockerfile = DockerfileScanner()
        self.sbom = SBOMScanner()
        self.ai = AIScanner()

    async def run(
        self,
        asset: Asset,
        scan_type: ScanType = ScanType.FULL,
        nmap_arguments: str = DEFAULT_ARGS,
        dockerfile_url: str | None = None,
        image_ref: str | None = None,
    ) -> dict:
        target = asset.value
        is_domain = asset.asset_type in (AssetType.DOMAIN, AssetType.URL)
        is_repo = asset.asset_type == AssetType.REPOSITORY
        results: dict = {}

        tasks = {}

        if scan_type in (ScanType.FULL, ScanType.SHODAN) and not is_repo:
            tasks["shodan"] = (
                self.shodan.search_domain(target) if is_domain
                else self.shodan.scan_host(target)
            )

        if scan_type in (ScanType.FULL, ScanType.PORTS) and not is_repo:
            tasks["nmap"] = self.nmap.scan(target, nmap_arguments)

        if scan_type in (ScanType.FULL, ScanType.SSL) and is_domain:
            tasks["ssl"] = self.ssl.scan(target)

        if scan_type in (ScanType.FULL, ScanType.HEADERS) and is_domain:
            url = target if target.startswith("http") else f"https://{target}"
            tasks["headers"] = self.headers.scan(url)

        if scan_type in (ScanType.FULL, ScanType.DOCKERFILE) or is_repo:
            df_target = dockerfile_url or target
            tasks["dockerfile"] = self.dockerfile.scan(df_target)

        if scan_type == ScanType.SBOM and image_ref:
            tasks["sbom"] = self.sbom.scan(image_ref)

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for key, value in zip(tasks.keys(), gathered):
            results[key] = {} if isinstance(value, Exception) else value
            if isinstance(value, Exception):
                logger.warning("Scanner '%s' raised: %s", key, value)

        findings = self._collect_findings(results)

        # AI post-processing: adds missed findings and remediation plan
        if settings.AI_ENABLED and findings:
            ai_result = await self.ai.scan(target, findings)
            extra = self.ai.extract_findings(ai_result)
            findings.extend(extra)
            results["ai"] = ai_result

        risk_score = self._calculate_risk(findings)

        return {
            "shodan_data": results.get("shodan"),
            "nmap_data": results.get("nmap"),
            "ssl_data": results.get("ssl"),
            "headers_data": results.get("headers"),
            "dockerfile_data": results.get("dockerfile"),
            "sbom_data": results.get("sbom"),
            "ai_data": results.get("ai"),
            "findings": findings,
            "risk_score": risk_score,
        }

    def _collect_findings(self, results: dict) -> list[dict]:
        findings = []

        if shodan := results.get("shodan"):
            findings.extend(self.shodan.extract_findings(shodan))

        if nmap := results.get("nmap"):
            findings.extend(self.nmap.extract_findings(nmap))

        if ssl := results.get("ssl"):
            findings.extend(self.ssl.extract_findings(ssl))

        if headers := results.get("headers"):
            findings.extend(self.headers.extract_findings(headers))

        if dockerfile := results.get("dockerfile"):
            findings.extend(self.dockerfile.extract_findings(dockerfile))

        if sbom := results.get("sbom"):
            findings.extend(self.sbom.extract_findings(sbom))

        return findings

    def _calculate_risk(self, findings: list[dict]) -> float:
        score = sum(SEVERITY_WEIGHT.get(f.get("severity", "info"), 0) for f in findings)
        return min(round(score, 1), 100.0)
