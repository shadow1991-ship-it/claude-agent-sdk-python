import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.asset import Asset, VerificationStatus
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.scan import ScanRequest, ScanOut, ScanSummary

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.post("", response_model=ScanSummary, status_code=status.HTTP_202_ACCEPTED)
async def request_scan(
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
