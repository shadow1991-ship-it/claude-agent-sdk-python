import hashlib
import json
import os
import logging
from datetime import datetime, timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from app.core.config import settings
from app.models.scan import Scan

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Builds a signed JSON report from a completed scan."""

    def __init__(self) -> None:
        self._private_key = self._load_or_create_private_key()
        self._public_key = self._private_key.public_key()

    def _load_or_create_private_key(self) -> rsa.RSAPrivateKey:
        priv_path = settings.RSA_PRIVATE_KEY_PATH
        pub_path = settings.RSA_PUBLIC_KEY_PATH

        if os.path.exists(priv_path):
            with open(priv_path, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)

        logger.info("Generating new RSA-2048 key pair at %s / %s", priv_path, pub_path)
        os.makedirs(os.path.dirname(priv_path), exist_ok=True)

        key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        with open(priv_path, "wb") as f:
            f.write(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )
        with open(pub_path, "wb") as f:
            f.write(
                key.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )
        return key

    def build_payload(self, scan: Scan) -> dict:
        findings = [
            {
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity.value,
                "category": f.category,
                "description": f.description,
                "reference": f.reference,
                "cvss_score": f.cvss_score,
                "details": f.details,
                "remediation": f.remediation,
            }
            for f in scan.findings
        ]

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in scan.findings:
            severity_counts[f.severity.value] += 1

        return {
            "report_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scan": {
                "id": str(scan.id),
                "type": scan.scan_type.value,
                "asset_id": str(scan.asset_id),
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            },
            "risk_score": scan.risk_score,
            "summary": severity_counts,
            "findings": findings,
            "raw": {
                "shodan": scan.shodan_data,
                "nmap": scan.nmap_data,
                "ssl": scan.ssl_data,
                "headers": scan.headers_data,
            },
        }

    def sign(self, payload: dict) -> tuple[str, str]:
        """Returns (signature_hex, sha256_fingerprint)."""
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")

        fingerprint = hashlib.sha256(serialized).hexdigest()

        signature = self._private_key.sign(
            serialized,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        ).hex()

        return signature, fingerprint

    def verify_signature(self, payload: dict, signature_hex: str) -> bool:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        try:
            self._public_key.verify(
                bytes.fromhex(signature_hex),
                serialized,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    def generate(self, scan: Scan) -> tuple[dict, str, str]:
        """Returns (payload, signature_hex, fingerprint)."""
        payload = self.build_payload(scan)
        signature, fingerprint = self.sign(payload)
        return payload, signature, fingerprint
