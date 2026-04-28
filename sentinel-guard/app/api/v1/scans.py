import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.main import limiter
from app.models.asset import Asset, VerificationStatus
from app.models.scan import Scan, ScanStatus, ScanFinding
from app.models.user import User
from app.schemas.scan import ScanRequest, ScanOut, ScanSummary, FixOut

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.post("", response_model=ScanSummary, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.RATE_SCAN)
async def request_scan(
    request: Request,
    payload: ScanRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = await _get_verified_asset(payload.asset_id, user, db)

    scan = Scan(
        asset_id=asset.id,
        requested_by=user.id,
        scan_type=payload.scan_type,
        status=ScanStatus.QUEUED,
    )
    db.add(scan)
    await db.flush()

    # Dispatch async task
    from app.workers.scan_tasks import run_scan
    task = run_scan.delay(str(scan.id), payload.nmap_arguments)
    scan.celery_task_id = task.id
    await db.flush()

    return ScanSummary(
        id=str(scan.id),
        asset_id=str(scan.asset_id),
        scan_type=scan.scan_type,
        status=scan.status,
        risk_score=None,
        created_at=scan.created_at.isoformat(),
    )


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scan = await _get_scan(scan_id, user, db)
    return _serialize(scan)


@router.get("", response_model=list[ScanSummary])
async def list_scans(
    asset_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Scan)
        .join(Asset, Scan.asset_id == Asset.id)
        .where(Asset.organization_id == user.organization_id)
        .options(selectinload(Scan.findings))
        .order_by(Scan.created_at.desc())
    )
    if asset_id:
        query = query.where(Scan.asset_id == uuid.UUID(asset_id))

    result = await db.execute(query)
    scans = result.scalars().all()
    return [
        ScanSummary(
            id=str(s.id),
            asset_id=str(s.asset_id),
            scan_type=s.scan_type,
            status=s.status,
            risk_score=s.risk_score,
            created_at=s.created_at.isoformat(),
            finding_counts=_count_severities(s),
        )
        for s in scans
    ]


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scan = await _get_scan(scan_id, user, db)
    if scan.status not in (ScanStatus.QUEUED, ScanStatus.RUNNING):
        raise HTTPException(status_code=400, detail="Scan is not cancellable")

    if scan.celery_task_id:
        AsyncResult(scan.celery_task_id).revoke(terminate=True, signal="SIGTERM")

    scan.status = ScanStatus.CANCELLED
    await db.flush()


async def _get_verified_asset(asset_id: str, user: User, db: AsyncSession) -> Asset:
    try:
        uid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    result = await db.execute(
        select(Asset).where(
            Asset.id == uid,
            Asset.organization_id == user.organization_id,
            Asset.is_active == True,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=403,
            detail="Asset ownership not verified. Verify the asset before scanning.",
        )
    return asset


async def _get_scan(scan_id: str, user: User, db: AsyncSession) -> Scan:
    try:
        uid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    result = await db.execute(
        select(Scan)
        .join(Asset, Scan.asset_id == Asset.id)
        .where(Scan.id == uid, Asset.organization_id == user.organization_id)
        .options(selectinload(Scan.findings))
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _serialize(scan: Scan) -> ScanOut:
    from app.schemas.scan import FindingOut
    return ScanOut(
        id=str(scan.id),
        asset_id=str(scan.asset_id),
        scan_type=scan.scan_type,
        status=scan.status,
        risk_score=scan.risk_score,
        error_message=scan.error_message,
        started_at=scan.started_at.isoformat() if scan.started_at else None,
        completed_at=scan.completed_at.isoformat() if scan.completed_at else None,
        created_at=scan.created_at.isoformat(),
        findings=[
            FindingOut(
                id=str(f.id),
                title=f.title,
                description=f.description,
                severity=f.severity,
                category=f.category,
                reference=f.reference,
                cvss_score=f.cvss_score,
                details=f.details,
                remediation=f.remediation,
            )
            for f in scan.findings
        ],
    )


def _count_severities(scan: Scan) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in scan.findings:
        counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
    return counts


@router.get("/{scan_id}/sarif")
async def export_sarif(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export scan findings in SARIF 2.1.0 format — compatible with GitHub Code Scanning, VS Code, Azure DevOps."""
    scan = await _get_scan(scan_id, user, db)

    def _build_rule(f: ScanFinding) -> dict:
        return {
            "id": str(f.id),
            "name": f.title.replace(" ", ""),
            "shortDescription": {"text": f.title},
            "fullDescription": {"text": f.description},
            "defaultConfiguration": {"level": _sarif_level(f.severity.value)},
            "help": {"text": f.remediation or "No remediation available.", "markdown": f.remediation or ""},
        }

    def _sarif_level(severity: str) -> str:
        return {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "none"}.get(severity, "none")

    def _finding_to_sarif(f: ScanFinding) -> dict:
        result = {
            "ruleId": str(f.id),
            "level": _sarif_level(f.severity.value),
            "message": {"text": f.description},
            "locations": [],
        }
        if f.details and f.details.get("line_number"):
            result["locations"].append({
                "physicalLocation": {
                    "artifactLocation": {"uri": "Dockerfile"},
                    "region": {"startLine": f.details["line_number"]},
                }
            })
        return result

    sarif = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Sentinel Guard",
                    "version": settings.APP_VERSION,
                    "rules": [_build_rule(f) for f in scan.findings],
                }
            },
            "results": [_finding_to_sarif(f) for f in scan.findings],
        }],
    }
    return JSONResponse(content=sarif, media_type="application/json")


@router.post("/{scan_id}/findings/{finding_id}/fix", response_model=FixOut)
async def generate_fix(
    scan_id: str,
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate an AI code fix for a specific finding using Granite Nano (local, free)."""
    scan = await _get_scan(scan_id, user, db)

    finding_obj = next((f for f in scan.findings if str(f.id) == finding_id), None)
    if not finding_obj:
        raise HTTPException(status_code=404, detail="Finding not found")

    asset_result = await db.execute(select(Asset).where(Asset.id == scan.asset_id))
    asset = asset_result.scalar_one_or_none()

    from app.services.scanner.auto_fixer import AutoFixer
    fixer = AutoFixer()
    fix = await fixer.generate_fix(
        finding={
            "id": str(finding_obj.id),
            "title": finding_obj.title,
            "description": finding_obj.description,
            "severity": finding_obj.severity.value,
            "remediation": finding_obj.remediation or "",
        },
        asset_context={
            "asset_type": asset.asset_type.value if asset else "unknown",
            "value": asset.value if asset else "",
        },
    )
    return FixOut(**fix)
