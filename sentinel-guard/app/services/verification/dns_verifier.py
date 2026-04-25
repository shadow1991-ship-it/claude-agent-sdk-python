import asyncio
import dns.asyncresolver
import dns.exception
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class DNSVerifier:
    """Verifies domain ownership via a DNS TXT record."""

    def build_record_value(self, token: str) -> str:
        return f"{settings.DNS_VERIFICATION_PREFIX}={token}"

    async def verify(self, domain: str, token: str) -> bool:
        expected = self.build_record_value(token)
        try:
            resolver = dns.asyncresolver.Resolver()
            resolver.lifetime = 10.0
            answers = await resolver.resolve(domain, "TXT")
            for rdata in answers:
                for txt_string in rdata.strings:
                    if txt_string.decode("utf-8", errors="ignore") == expected:
                        logger.info("DNS TXT verification passed for %s", domain)
                        return True
        except dns.exception.DNSException as exc:
            logger.warning("DNS lookup failed for %s: %s", domain, exc)
        return False

    def get_instructions(self, domain: str, token: str) -> str:
        record = self.build_record_value(token)
        return (
            f"Add the following DNS TXT record to your domain '{domain}':\n\n"
            f"  Type : TXT\n"
            f"  Host : @ (or {domain})\n"
            f"  Value: {record}\n\n"
            "DNS propagation may take up to 24 hours. "
            "Call /assets/verify once the record is live."
        )
