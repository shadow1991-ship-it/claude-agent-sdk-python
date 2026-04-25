from pydantic import BaseModel, Field, field_validator
import ipaddress
import re
from app.models.asset import AssetType, VerificationMethod, VerificationStatus


_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


class AssetCreate(BaseModel):
    value: str = Field(min_length=1, max_length=500)
    asset_type: AssetType
    description: str | None = Field(default=None, max_length=1000)
    verification_method: VerificationMethod

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        v = v.strip().lower()
        return v


class AssetOut(BaseModel):
    id: str
    value: str
    asset_type: AssetType
    description: str | None
    verification_method: VerificationMethod
    verification_status: VerificationStatus
    verification_token: str | None
    verified_at: str | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class VerificationChallenge(BaseModel):
    asset_id: str
    method: VerificationMethod
    instructions: str
    token: str
    dns_record: str | None = None
    http_path: str | None = None


class VerifyAssetRequest(BaseModel):
    asset_id: str
