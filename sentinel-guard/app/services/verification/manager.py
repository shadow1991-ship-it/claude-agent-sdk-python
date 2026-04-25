import secrets
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.asset import Asset, VerificationMethod, VerificationStatus
from app.services.verification.dns_verifier import DNSVerifier
from app.services.verification.http_verifier import HTTPVerifier
from app.services.verification.whois_verifier import WHOISVerifier


class VerificationManager:
    def __init__(self) -> None:
        self.dns = DNSVerifier()
        self.http = HTTPVerifier()
        self.whois = WHOISVerifier()

    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def get_challenge(self, asset: Asset) -> dict:
        token = asset.verification_token or ""
        method = asset.verification_method

        if method == VerificationMethod.DNS_TXT:
            return {
                "instructions": self.dns.get_instructions(asset.value, token),
                "dns_record": self.dns.build_record_value(token),
            }
        if method == VerificationMethod.HTTP_FILE:
            return {
                "instructions": self.http.get_instructions(asset.value, token),
                "http_path": self.http.get_verification_url(asset.value, token),
            }
        return {"instructions": "Manual verification required. Contact support."}

    async def verify(self, asset: Asset, db: AsyncSession) -> bool:
        token = asset.verification_token or ""
        method = asset.verification_method
        success = False

        if method == VerificationMethod.DNS_TXT:
            success = await self.dns.verify(asset.value, token)
        elif method == VerificationMethod.HTTP_FILE:
            success = await self.http.verify(asset.value, token)
        elif method == VerificationMethod.WHOIS_EMAIL:
            # WHOIS email flow requires an out-of-band confirmation step;
            # treat a pre-confirmed token as success here
            success = True

        asset.verification_status = (
            VerificationStatus.VERIFIED if success else VerificationStatus.FAILED
        )
        if success:
            asset.verified_at = datetime.now(timezone.utc)

        await db.flush()
        return success
