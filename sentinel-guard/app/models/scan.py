import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Enum as SAEnum, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class ScanType(str, enum.Enum):
    FULL = "full"
    PORTS = "ports"
    SSL = "ssl"
    HEADERS = "headers"
    SHODAN = "shodan"
    DOCKERFILE = "dockerfile"
    SBOM = "sbom"


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    scan_type: Mapped[ScanType] = mapped_column(SAEnum(ScanType), nullable=False)
    status: Mapped[ScanStatus] = mapped_column(SAEnum(ScanStatus), default=ScanStatus.QUEUED)

    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw results from each scanner
    shodan_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    nmap_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ssl_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    headers_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dockerfile_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sbom_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Dockerfile / container image target
    dockerfile_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Aggregated risk score 0-100
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="scans")
    findings: Mapped[list["ScanFinding"]] = relationship(
        "ScanFinding", back_populates="scan", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship("Report", back_populates="scan", uselist=False)


class ScanFinding(Base):
    __tablename__ = "scan_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # CVE or reference
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Specific details (port, service, etc.)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")
