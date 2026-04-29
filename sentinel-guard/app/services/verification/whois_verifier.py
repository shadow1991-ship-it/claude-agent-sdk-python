import asyncio
import ipwhois
import logging

logger = logging.getLogger(__name__)


class WHOISVerifier:
    """Verifies IP ownership by checking WHOIS registration email."""

    async def get_abuse_emails(self, ip: str) -> list[str]:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._lookup, ip)
            return result
        except Exception as exc:
            logger.warning("WHOIS lookup failed for %s: %s", ip, exc)
            return []

    def _lookup(self, ip: str) -> list[str]:
        obj = ipwhois.IPWhois(ip)
        result = obj.lookup_rdap(depth=1)
        emails: list[str] = []
        for entity in result.get("entities", []):
            for contact in entity.get("contact", {}).get("email", []):
                emails.append(contact.get("value", "").lower())
        return list(set(emails))

    def get_instructions(self, ip: str, token: str, registered_email: str) -> str:
        return (
            f"To verify ownership of IP {ip}:\n\n"
            f"  1. We will send a verification email to: {registered_email}\n"
            f"     (extracted from WHOIS records)\n"
            f"  2. The email contains token: {token}\n"
            f"  3. Reply to or click the link in that email to confirm ownership.\n\n"
            "If the WHOIS email is outdated, use DNS TXT or HTTP verification instead."
        )
