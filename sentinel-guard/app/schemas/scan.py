from pydantic import BaseModel, Field
from app.models.scan import ScanType, ScanStatus, Severity


class ScanRequest(BaseModel):
    asset_id: str
    scan_type: ScanType = ScanType.FULL
    nmap_arguments: str = Field(default="-sV -sC --open", max_length=200)


class FindingOut(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity
    category: str
    reference: str | None
    cvss_score: float | None
    details: dict | None
    remediation: str | None

    model_config = {"from_attributes": True}


class ScanOut(BaseModel):
    id: str
    asset_id: str
    scan_type: ScanType
    status: ScanStatus
    risk_score: float | None
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    findings: list[FindingOut] = []

    model_config = {"from_attributes": True}


class ScanSummary(BaseModel):
    id: str
    asset_id: str
    scan_type: ScanType
    status: ScanStatus
    risk_score: float | None
    created_at: str
    finding_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
