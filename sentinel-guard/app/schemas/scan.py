import re
from pydantic import BaseModel, Field, field_validator
from app.models.scan import ScanType, ScanStatus, Severity

# Flags and their optional value patterns that are explicitly permitted.
# Anything not matching this set is rejected before reaching the scanner.
_ALLOWED_FLAGS: set[str] = {
    "-sV", "-sC", "-sT", "-sU", "-sn", "-sP",
    "--open", "--closed",
    "-T0", "-T1", "-T2", "-T3", "-T4", "-T5",
    "-O", "-A",
    "--script=safe", "--script=default",
    "--host-timeout",
    "--max-retries",
    "--top-ports",
    "-p",
    "-F",
    "-n",
    "-v", "-vv",
}

_FLAG_RE = re.compile(r"^(-{1,2}[a-zA-Z][\w\-=,]*|\d+(?:-\d+)?)$")


def _validate_nmap_args(value: str) -> str:
    tokens = value.split()
    for token in tokens:
        # Allow port ranges like "80,443" or "1-1024"
        if re.fullmatch(r"\d[\d,\-]*", token):
            continue
        # Allow --script=<name> with safe chars only
        if re.fullmatch(r"--script=[a-zA-Z0-9_,\-]+", token):
            continue
        # Allow --host-timeout / --max-retries values
        if re.fullmatch(r"\d+[smh]?", token):
            continue
        if token not in _ALLOWED_FLAGS:
            raise ValueError(
                f"Nmap flag not permitted: '{token}'. "
                f"Allowed: {sorted(_ALLOWED_FLAGS)}"
            )
    return value


class ScanRequest(BaseModel):
    asset_id: str
    scan_type: ScanType = ScanType.FULL
    nmap_arguments: str = Field(default="-sV -sC --open", max_length=200)

    @field_validator("nmap_arguments")
    @classmethod
    def validate_nmap_arguments(cls, v: str) -> str:
        return _validate_nmap_args(v)


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
