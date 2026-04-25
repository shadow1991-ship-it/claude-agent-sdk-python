import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AssetType(str, enum.Enum):
    DOMAIN = "domain"
    IP = "ip"
    IP_RANGE = "ip_range"
    URL = "url"


class VerificationMethod(str, enum.Enum):
    DNS_TXT = "dns_txt"
    HTTP_FILE = "http_file"
    WHOIS_EMAIL = "whois_email"
    MANUAL = "manual"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification
    verification_method: Mapped[VerificationMethod] = mapped_column(
        SAEnum(VerificationMethod), nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False
    )
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="assets")
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="asset", cascade="all, delete-orphan")
