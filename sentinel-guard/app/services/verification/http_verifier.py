import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class HTTPVerifier:
    """Verifies domain ownership via a file hosted on the web server."""

    def get_verification_url(self, domain: str, token: str) -> str:
        return f"http://{domain}/{settings.HTTP_VERIFICATION_PATH}/{token}"

    async def verify(self, domain: str, token: str) -> bool:
        url = self.get_verification_url(domain, token)
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and token in resp.text:
                    logger.info("HTTP file verification passed for %s", domain)
                    return True
                logger.warning(
                    "HTTP verification failed for %s — status=%s", domain, resp.status_code
                )
        except httpx.RequestError as exc:
            logger.warning("HTTP request error for %s: %s", domain, exc)
        return False

    def get_instructions(self, domain: str, token: str) -> str:
        path = f"{settings.HTTP_VERIFICATION_PATH}/{token}"
        url = self.get_verification_url(domain, token)
        return (
            f"Create a file at the following path on your web server:\n\n"
            f"  Path   : {path}\n"
            f"  Content: {token}\n\n"
            f"The file must be publicly accessible at:\n  {url}\n\n"
            "Call /assets/verify once the file is in place."
        )
