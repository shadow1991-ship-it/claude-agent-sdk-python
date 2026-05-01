"""
Sentinel Guard — AWS Lambda Handler
يستدعي Sentinel Guard API لتشغيل فحص Dockerfile ويُرجع النتيجة.

Free Tier: 1M requests/month + 400,000 GB-seconds/month

Test locally:
    docker build -t sentinel-lambda .
    docker run -p 9000:8080 sentinel-lambda
    curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
         -d '{"scan_type": "dockerfile", "target": "https://raw.github.com/.../Dockerfile"}'
"""
import os
import json
import httpx

SENTINEL_URL   = os.environ.get("SENTINEL_URL",   "http://localhost:8000/api/v1")
SENTINEL_TOKEN = os.environ.get("SENTINEL_TOKEN",  "")
SCAN_TIMEOUT   = int(os.environ.get("SCAN_TIMEOUT", "120"))


def _headers() -> dict:
    return {"Authorization": f"Bearer {SENTINEL_TOKEN}", "Content-Type": "application/json"}


def _create_scan(scan_type: str, asset_id: str, dockerfile_url: str | None) -> dict:
    payload: dict = {"asset_id": asset_id, "scan_type": scan_type}
    if dockerfile_url:
        payload["dockerfile_url"] = dockerfile_url
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{SENTINEL_URL}/scans", headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


def _wait_for_scan(scan_id: str, timeout: int) -> dict:
    import time
    deadline = time.time() + timeout
    with httpx.Client(timeout=15) as client:
        while time.time() < deadline:
            r = client.get(f"{SENTINEL_URL}/scans/{scan_id}", headers=_headers())
            r.raise_for_status()
            data = r.json()
            if data.get("status") in ("completed", "failed"):
                return data
            time.sleep(5)
    return {"status": "timeout", "scan_id": scan_id}


def handler(event: dict, context=None) -> dict:
    """
    Lambda entry point.

    event fields:
        scan_type     : "dockerfile" | "nmap" | "ssl" | "headers" | "full"
        target        : IP / URL / hostname
        asset_id      : UUID of existing asset (optional — will auto-create if missing)
        dockerfile_url: URL to Dockerfile (required for scan_type=dockerfile)
    """
    scan_type      = event.get("scan_type", "dockerfile")
    target         = event.get("target", "")
    asset_id       = event.get("asset_id")
    dockerfile_url = event.get("dockerfile_url")

    try:
        # 1. إنشاء asset إذا لم يُعطَ
        if not asset_id:
            asset_type = "repository" if scan_type == "dockerfile" else "domain"
            with httpx.Client(timeout=15) as client:
                r = client.post(
                    f"{SENTINEL_URL}/assets",
                    headers=_headers(),
                    json={"value": target, "asset_type": asset_type},
                )
                r.raise_for_status()
                asset_id = r.json()["id"]

        # 2. إطلاق الفحص
        scan = _create_scan(scan_type, asset_id, dockerfile_url or target)
        scan_id = scan["id"]

        # 3. انتظار الاكتمال
        result = _wait_for_scan(scan_id, SCAN_TIMEOUT)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "scan_id":  scan_id,
                "status":   result.get("status"),
                "findings": result.get("findings_count", 0),
                "result":   result,
            }),
        }

    except httpx.HTTPStatusError as exc:
        return {
            "statusCode": exc.response.status_code,
            "body": json.dumps({"error": str(exc), "detail": exc.response.text[:500]}),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
