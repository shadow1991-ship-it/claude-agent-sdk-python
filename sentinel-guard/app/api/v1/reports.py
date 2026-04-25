import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.asset import Asset
from app.models.report import Report
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.report import ReportOut, ReportVerification
from app.services.reporter.generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])
_generator = ReportGenerator()


@router.post("/generate/{scan_id}", response_model=ReportOut)
async def generate_report(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scan = await _get_completed_scan(scan_id, user, db)

    existing = await db.execute(select(Report).where(Report.scan_id == scan.id))
    if report := existing.scalar_one_or_none():
        return _serialize(report)

    payload, signature, fingerprint = _generator.generate(scan)

    report = Report(
        scan_id=scan.id,
        generated_by=user.id,
        payload=payload,
        signature=signature,
        fingerprint=fingerprint,
    )
    db.add(report)
    await db.flush()
    return _serialize(report)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)
    return _serialize(report)


@router.get("/{report_id}/verify", response_model=ReportVerification)
async def verify_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)
    is_valid = _generator.verify_signature(report.payload, report.signature)
    return ReportVerification(
        report_id=str(report.id),
        fingerprint=report.fingerprint,
        is_valid=is_valid,
        message="Report integrity verified." if is_valid else "Signature mismatch — report may have been tampered.",
    )


@router.get("", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .join(Asset, Scan.asset_id == Asset.id)
        .where(Asset.organization_id == user.organization_id)
        .order_by(Report.created_at.desc())
    )
    return [_serialize(r) for r in result.scalars().all()]


async def _get_completed_scan(scan_id: str, user: User, db: AsyncSession) -> Scan:
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
    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Scan is not yet completed")
    return scan


async def _get_owned_report(report_id: str, user: User, db: AsyncSession) -> Report:
    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .join(Asset, Scan.asset_id == Asset.id)
        .where(Report.id == uid, Asset.organization_id == user.organization_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _serialize(report: Report) -> ReportOut:
    return ReportOut(
        id=str(report.id),
        scan_id=str(report.scan_id),
        payload=report.payload,
        signature=report.signature,
        fingerprint=report.fingerprint,
        created_at=report.created_at.isoformat(),
    )
