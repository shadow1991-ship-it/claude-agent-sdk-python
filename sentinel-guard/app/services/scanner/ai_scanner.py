"""
Multi-model AI scanner using Docker Model Runner (all free, all local).
Routes tasks to the right model based on complexity:
  - Fast  (Granite Nano):      AutoFixer, pattern check, code review
  - Deep  (DeepSeek V4 Pro):   Dockerfile analysis, CVE reasoning, SBOM review
  - Chat  (DeepSeek V4 Flash): Dashboard chatbot, SSE Q&A, scan summary
"""
import json
import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes AI tasks to the appropriate local model via Docker Model Runner."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.DOCKER_MODEL_RUNNER_URL,
            api_key="unused",
        )

    async def fast(self, prompt: str) -> str:
        """Granite Nano — pattern check, code fix, < 2s."""
        return await self._call(settings.AI_MODEL_FAST, prompt, timeout=10)

    async def deep(self, prompt: str) -> str:
        """DeepSeek V4 Pro — Dockerfile analysis, security reasoning, < 30s."""
        return await self._call(settings.AI_MODEL_DEEP, prompt, timeout=60)

    async def chat(self, messages: list[dict]) -> str:
        """DeepSeek V4 Flash — chatbot, dashboard Q&A, < 15s."""
        return await self._call(settings.AI_MODEL_GENERAL, messages=messages, timeout=30)

    async def _call(
        self,
        model: str,
        prompt: str = "",
        messages: list[dict] | None = None,
        timeout: int = 30,
    ) -> str:
        if not settings.AI_ENABLED:
            return ""
        try:
            msgs = messages or [{"role": "user", "content": prompt}]
            response = await self._client.chat.completions.create(
                model=model,
                messages=msgs,
                timeout=timeout,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("Docker Model Runner call failed (%s): %s", model, exc)
            return ""


class AIScanner:
    """Post-processing AI scanner: aggregates findings from all scanners and adds insights."""

    SYSTEM_PROMPT = (
        "You are a senior security analyst. Given a JSON summary of security scan findings, "
        "identify any missed vulnerabilities, prioritize remediation order, and suggest a "
        "remediation plan. Return ONLY a JSON object with keys: "
        "'additional_findings' (array), 'priority_order' (array of finding titles), "
        "'remediation_plan' (string). No prose outside JSON."
    )

    def __init__(self) -> None:
        self._router = ModelRouter()

    async def scan(self, target: str, existing_findings: list[dict]) -> dict:
        if not settings.AI_ENABLED or not existing_findings:
            return {"additional_findings": [], "priority_order": [], "remediation_plan": ""}

        summary = json.dumps({
            "target": target,
            "finding_count": len(existing_findings),
            "findings": existing_findings[:20],  # cap to avoid token overflow
        }, ensure_ascii=False)

        raw = await self._router.deep(
            f"{self.SYSTEM_PROMPT}\n\nScan summary:\n{summary}"
        )
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("AI scanner JSON parse failed: %s", exc)

        return {"additional_findings": [], "priority_order": [], "remediation_plan": raw}

    def extract_findings(self, data: dict) -> list[dict]:
        results = []
        for f in data.get("additional_findings", []):
            results.append({
                "title": f.get("title", "AI Finding"),
                "description": f.get("description", ""),
                "severity": f.get("severity", "medium"),
                "category": f.get("category", "ai-analysis"),
                "reference": None,
                "cvss_score": None,
                "details": {"source": "ai-scanner"},
                "remediation": f.get("remediation", ""),
            })
        return results
