"""
AutoFixer — NeatCoder-inspired: security finding → AI generates exact code fix.
Uses Granite Nano (fast) for code generation via Docker Model Runner.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a security engineer. Given a security finding and asset context, "
    "generate the exact code fix. Return ONLY a JSON object with keys: "
    "fix_code (string), fix_language (string: dockerfile|nginx|python|yaml|bash|json), "
    "fix_description (string, one sentence). No prose, only JSON."
)

ASSET_TYPE_HINTS = {
    "dockerfile": "The asset is a Dockerfile.",
    "repository": "The asset is a code repository.",
    "domain": "The asset is a web server or domain.",
    "url": "The asset is a web application URL.",
    "ip": "The asset is a server IP address.",
}


class AutoFixer:
    """Generates concrete code fixes for security findings using local AI."""

    async def generate_fix(self, finding: dict, asset_context: dict) -> dict:
        from app.services.scanner.ai_scanner import ModelRouter
        router = ModelRouter()

        asset_hint = ASSET_TYPE_HINTS.get(
            asset_context.get("asset_type", ""), "The asset type is unknown."
        )
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Context: {asset_hint}\n"
            f"Finding title: {finding.get('title', '')}\n"
            f"Finding description: {finding.get('description', '')}\n"
            f"Suggested remediation: {finding.get('remediation', '')}\n"
        )

        raw = await router.fast(prompt)
        try:
            import json
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
                return {
                    "finding_id": finding.get("id", ""),
                    "fix_code": result.get("fix_code", ""),
                    "fix_language": result.get("fix_language", "text"),
                    "fix_description": result.get("fix_description", ""),
                }
        except Exception as exc:
            logger.warning("AutoFixer JSON parse failed: %s", exc)

        return {
            "finding_id": finding.get("id", ""),
            "fix_code": raw,
            "fix_language": "text",
            "fix_description": "AI-generated fix suggestion.",
        }
