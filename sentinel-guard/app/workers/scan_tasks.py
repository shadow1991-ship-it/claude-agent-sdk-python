import asyncio
import logging
import uuid
from datetime import datetime, timezone
from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.scan import Scan, ScanStatus, ScanFinding, Severity
from app.models.asset import Asset
from app.services.scanner.orchestrator import ScanOrchestrator

logger = logging.getLogger(__name__)

_orchestrator = ScanOrchestrator()

SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}


class ScanTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Scan task %s failed: %s", task_id, exc)


@celery_app.task(bind=True, base=ScanTask, name="run_scan")
def run_scan(self, scan_id: str, nmap_arguments: str, dockerfile_url: str | None = None, image_ref: str | None = None) -> dict:
    return asyncio.run(_execute_scan(scan_id, nmap_arguments, dockerfile_url, image_ref))


async def _execute_scan(scan_id: str, nmap_arguments: str, dockerfile_url: str | None = None, image_ref: str | None = None) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Scan)
            .where(Scan.id == uuid.UUID(scan_id))
            .options(selectinload(Scan.asset))
        )
        scan = result.scalar_one_or_none()

        if not scan:
            logger.error("Scan %s not found", scan_id)
            return {"error": "Scan not found"}

        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            results = await _orchestrator.run(
                scan.asset, scan.scan_type, nmap_arguments,
                dockerfile_url=dockerfile_url,
                image_ref=image_ref,
            )

            scan.shodan_data = results.get("shodan_data")
            scan.nmap_data = results.get("nmap_data")
            scan.ssl_data = results.get("ssl_data")
            scan.headers_data = results.get("headers_data")
            scan.dockerfile_data = results.get("dockerfile_data")
            scan.sbom_data = results.get("sbom_data")
            scan.ai_data = results.get("ai_data")
            scan.risk_score = results.get("risk_score", 0.0)

            for raw_finding in results.get("findings", []):
                finding = ScanFinding(
                    scan_id=scan.id,
                    title=raw_finding["title"],
                    description=raw_finding["description"],
                    severity=SEVERITY_MAP.get(raw_finding.get("severity", "info"), Severity.INFO),
                    category=raw_finding.get("category", "general"),
                    reference=raw_finding.get("reference"),
                    cvss_score=raw_finding.get("cvss_score"),
                    details=raw_finding.get("details"),
                    remediation=raw_finding.get("remediation"),
                )
                db.add(finding)

            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info("Scan %s completed — risk score: %.1f", scan_id, scan.risk_score)
            return {"status": "completed", "risk_score": scan.risk_score}

        except Exception as exc:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(exc)
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("Scan %s failed: %s", scan_id, exc)
            raise
