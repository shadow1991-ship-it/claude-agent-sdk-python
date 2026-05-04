from uuid import UUID
from pydantic import BaseModel


class ReportOut(BaseModel):
    id: UUID
    scan_id: UUID
    payload: dict
    signature: str
    fingerprint: str
    created_at: str

    model_config = {"from_attributes": True}


class ReportVerification(BaseModel):
    report_id: str
    fingerprint: str
    is_valid: bool
    message: str
