"""
Dockerfile security scanner — two layers:
  1. Rule-based: fast regex pattern matching (TRACK-inspired, all 8 bugs fixed)
  2. AI layer: DeepSeek V4 Pro via Docker Model Runner for deep contextual analysis
"""
import re
import json
import logging
import httpx
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

_FROM_RE = re.compile(r"^FROM\s+(.+?)(?:\s+AS\s+\S+)?\s*$", re.IGNORECASE)
_ENV_SECRET_RE = re.compile(r"(PASSWORD|SECRET|KEY|TOKEN|PASS)\s*[=:]", re.IGNORECASE)
_CURL_PIPE_RE = re.compile(r"curl\s+\S+.*\|\s*(ba)?sh", re.IGNORECASE)
_APT_CLEAN_RE = re.compile(r"apt(?:-get)?\s+install", re.IGNORECASE)
_APT_PURGE_RE = re.compile(r"apt(?:-get)?\s+clean|rm\s+-rf\s+/var/lib/apt", re.IGNORECASE)
_ADD_RE = re.compile(r"^ADD\s+", re.IGNORECASE)
_DIGEST_RE = re.compile(r"@sha256:[a-f0-9]{64}")


class DockerfileParser:
    """Parses Dockerfile content into structured instruction list."""

    def parse(self, content: str) -> list[dict]:
        instructions = []
        for line_num, raw in enumerate(content.splitlines(), start=1):  # BUG-01 fixed: enumerate not ++
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            cmd = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""
            instructions.append({"line": line_num, "cmd": cmd, "args": args})
        return instructions

    def extract_rule_findings(self, instructions: list[dict]) -> list[dict]:
        findings = []
        has_apt_install = False

        for instr in instructions:
            cmd, args, line = instr["cmd"], instr["args"], instr["line"]

            if cmd == "FROM":
                image = args.strip()
                # BUG-05 fixed: strip AS alias before parsing
                image = re.sub(r"\s+AS\s+\S+\s*$", "", image, flags=re.IGNORECASE).strip()
                if not _DIGEST_RE.search(image):
                    # BUG-04 fixed: default tag "latest" when no tag
                    tag = image.split(":")[-1] if ":" in image else "latest"
                    findings.append({
                        "title": "Image not digest-pinned",
                        "description": f"FROM {image} uses tag '{tag}' instead of @sha256 digest — vulnerable to image substitution attacks.",
                        "severity": "high",
                        "category": "supply-chain",
                        "line_number": line,
                        "remediation": f"Pin the image: FROM {image.split(':')[0]}@sha256:<digest>",
                    })

            elif cmd == "ENV" and _ENV_SECRET_RE.search(args):
                findings.append({
                    "title": "Hardcoded secret in ENV",
                    "description": f"Line {line}: ENV instruction contains a potential secret: {args[:80]}",
                    "severity": "critical",
                    "category": "secrets",
                    "line_number": line,
                    "remediation": "Use Docker secrets or build-time ARG with --secret mount instead of ENV for sensitive values.",
                })

            elif cmd == "RUN":
                if _CURL_PIPE_RE.search(args):
                    findings.append({
                        "title": "Remote code execution via curl|bash",
                        "description": f"Line {line}: Piping curl output directly to shell allows arbitrary remote code execution.",
                        "severity": "high",
                        "category": "rce",
                        "line_number": line,
                        "remediation": "Download script first, verify its checksum, then execute.",
                    })
                if _APT_CLEAN_RE.search(args):
                    has_apt_install = True

            elif cmd == "ADD" and not args.startswith("http"):
                findings.append({
                    "title": "Prefer COPY over ADD",
                    "description": f"Line {line}: ADD has implicit tar extraction and URL fetch behaviors that can be surprising.",
                    "severity": "info",
                    "category": "best-practice",
                    "line_number": line,
                    "remediation": "Use COPY for local files unless you specifically need ADD's extra features.",
                })

        # Check apt cache purge after all instructions
        all_run_args = " ".join(i["args"] for i in instructions if i["cmd"] == "RUN")
        if has_apt_install and not _APT_PURGE_RE.search(all_run_args):
            findings.append({
                "title": "APT cache not purged",
                "description": "apt-get install found but no apt-get clean or rm /var/lib/apt/lists — increases image size.",
                "severity": "low",
                "category": "image-size",
                "line_number": 0,
                "remediation": "Add '&& apt-get clean && rm -rf /var/lib/apt/lists/*' to your RUN instruction.",
            })

        return findings


class DockerfileAIAnalyzer:
    """Deep AI analysis of Dockerfile using DeepSeek V4 Pro via Docker Model Runner."""

    SYSTEM_PROMPT = (
        "You are a Docker security expert. Analyze the provided Dockerfile and return "
        "ONLY a valid JSON array of security findings. Each finding must have these fields: "
        "title (str), description (str), severity (critical|high|medium|low|info), "
        "category (str), line_number (int or 0), remediation (str). "
        "Return [] if no additional findings beyond obvious ones. No prose, only JSON."
    )

    async def analyze(self, content: str) -> list[dict]:
        if not settings.AI_ENABLED:
            return []
        try:
            client = AsyncOpenAI(
                base_url=settings.DOCKER_MODEL_RUNNER_URL,
                api_key="unused",
            )
            response = await client.chat.completions.create(
                model=settings.AI_MODEL_DEEP,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this Dockerfile:\n\n{content}"},
                ],
                timeout=settings.AI_TIMEOUT,
                max_tokens=2048,
            )
            raw = response.choices[0].message.content.strip()
            # Extract JSON array from response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("AI Dockerfile analysis failed (graceful degradation): %s", exc)
        return []


class DockerfileScanner:
    """Combines rule-based + AI analysis for Dockerfile security scanning."""

    def __init__(self) -> None:
        self._parser = DockerfileParser()
        self._ai = DockerfileAIAnalyzer()

    async def scan(self, target: str) -> dict:
        content = await self._fetch_content(target)
        if not content:
            return {"error": f"Could not fetch Dockerfile from: {target}", "findings": []}

        instructions = self._parser.parse(content)
        rule_findings = self._parser.extract_rule_findings(instructions)
        ai_findings = await self._ai.analyze(content)

        # Deduplicate by title+line
        seen = {(f["title"], f.get("line_number", 0)) for f in rule_findings}
        unique_ai = [
            f for f in ai_findings
            if (f.get("title", ""), f.get("line_number", 0)) not in seen
        ]

        return {
            "target": target,
            "rule_findings": rule_findings,
            "ai_findings": unique_ai,
            "total_findings": len(rule_findings) + len(unique_ai),
            "content_lines": len(content.splitlines()),
        }

    def extract_findings(self, data: dict) -> list[dict]:
        results = []
        for f in data.get("rule_findings", []) + data.get("ai_findings", []):
            results.append({
                "title": f.get("title", "Unknown"),
                "description": f.get("description", ""),
                "severity": f.get("severity", "info"),
                "category": f.get("category", "dockerfile"),
                "reference": None,
                "cvss_score": None,
                "details": {"line_number": f.get("line_number", 0), "source": "dockerfile"},
                "remediation": f.get("remediation", ""),
            })
        return results

    async def _fetch_content(self, target: str) -> str:
        if target.startswith("http://") or target.startswith("https://"):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:  # BUG-07 fixed: timeout
                    resp = await client.get(target, follow_redirects=True)
                    resp.raise_for_status()
                    return resp.text
            except Exception as exc:
                logger.error("Failed to fetch Dockerfile from URL: %s", exc)
                return ""
        else:
            try:
                from pathlib import Path
                return Path(target).read_text(encoding="utf-8")
            except Exception as exc:
                logger.error("Failed to read Dockerfile from path: %s", exc)
                return ""
