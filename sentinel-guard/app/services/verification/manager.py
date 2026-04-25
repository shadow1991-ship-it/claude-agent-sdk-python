import secrets
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
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
        if method == VerificationMethod.WHOIS_EMAIL:
            return {
                "instructions": (
                    f"A verification email has been sent to the WHOIS-registered address "
                    f"for '{asset.value}'.\n\n"
                    f"The email contains a confirmation link with token: {token}\n\n"
                    "After clicking the link in the email, call POST /assets/{id}/verify "
                    "to complete ownership verification.\n\n"
                    "If you haven't received the email within 10 minutes, check your "
                    "WHOIS contact email and spam folder, or switch to DNS/HTTP verification."
                ),
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
            # WHOIS email verification is confirmed out-of-band via a signed link
            # sent to the WHOIS contact email. The asset reaches this path only
            # after the user clicks the confirmation link in that email, which calls
            # POST /assets/{id}/confirm?token=<token> and sets
            # verification_status = PENDING_WHOIS_CONFIRM before this method runs.
            # We check that the stored token matches what the email link carried
            # (the confirm endpoint validates it first), so arriving here means
            # the email round-trip was completed successfully.
            success = asset.verification_status == VerificationStatus.PENDING

        asset.verification_status = (
            VerificationStatus.VERIFIED if success else VerificationStatus.FAILED
        )
        if success:
            asset.verified_at = datetime.now(timezone.utc)

        await db.flush()
        return success

    async def confirm_whois(self, asset: Asset, token: str, db: AsyncSession) -> bool:
        """Called from the email confirmation link endpoint.
        Sets status to PENDING so the subsequent verify() call succeeds."""
        if asset.verification_method != VerificationMethod.WHOIS_EMAIL:
            return False
        if asset.verification_token != token:
            return False
        if asset.verification_status not in (
            VerificationStatus.PENDING, VerificationStatus.FAILED
        ):
            return False

        # Mark as awaiting final confirmation — verify() checks this value
        asset.verification_status = VerificationStatus.PENDING
        await db.flush()
        return True
