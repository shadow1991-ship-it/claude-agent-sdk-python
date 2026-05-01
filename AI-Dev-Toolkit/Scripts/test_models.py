#!/usr/bin/env python3
"""
Test all local models via Docker Model Runner.
Free — no API key, no cloud, all runs locally.

Usage:
    python test_models.py
    python test_models.py --url http://localhost:12434/engines/llama.cpp/v1
"""
import asyncio
import argparse
import time
import sys

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Install: pip install openai")
    sys.exit(1)

MODELS = {
    "granite-4.0-nano": "ai/granite-4.0-nano",      # sha256:34ae9a653d558205...
    "kimi-k2":          "ai/kimi-k2",               # MoE, 61 layers, deep analysis
    "deepseek-v4-flash": "ai/deepseek-v4-flash",    # 1M context, fast chatbot
    "deepseek-v3":      "ai/deepseek-v3-0324",      # fallback
}

TEST_PROMPTS = {
    "granite-4.0-nano":  "Reply with exactly: GRANITE_OK",
    "kimi-k2":           "Reply with exactly: KIMI_OK",
    "deepseek-v4-flash": "Reply with exactly: DEEPSEEK_OK",
    "deepseek-v3":       "Reply with exactly: DS3_OK",
}


async def test_model(client: AsyncOpenAI, name: str, model_id: str) -> dict:
    prompt = TEST_PROMPTS.get(name, "Reply with: OK")
    start = time.time()
    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            timeout=30,
        )
        latency = round(time.time() - start, 2)
        content = response.choices[0].message.content.strip()
        return {"name": name, "status": "ok", "latency": latency, "reply": content}
    except Exception as exc:
        latency = round(time.time() - start, 2)
        return {"name": name, "status": "error", "latency": latency, "error": str(exc)}


async def list_available_models(client: AsyncOpenAI) -> list[str]:
    try:
        models = await client.models.list()
        return [m.id for m in models.data]
    except Exception:
        return []


async def main(base_url: str, skip_unavailable: bool) -> None:
    client = AsyncOpenAI(base_url=base_url, api_key="unused")

    print(f"Docker Model Runner → {base_url}\n")

    available = await list_available_models(client)
    if available:
        print(f"نماذج متاحة: {', '.join(available)}\n")
    else:
        print("تحذير: تعذّر جلب قائمة النماذج — سيُحاول اختبار كل نموذج مباشرة\n")

    results = []
    tasks = []
    for name, model_id in MODELS.items():
        if skip_unavailable and available and model_id not in available:
            print(f"⏭  {name:20} | غير محمَّل — تخطي")
            continue
        tasks.append(test_model(client, name, model_id))

    if tasks:
        results = await asyncio.gather(*tasks)

    print("\n" + "─" * 60)
    print(f"{'النموذج':<22} {'الحالة':<8} {'الزمن':<8} {'الرد'}")
    print("─" * 60)
    for r in results:
        if r["status"] == "ok":
            print(f"✅ {r['name']:<20} {'ok':<8} {r['latency']:>4}s   {r['reply']}")
        else:
            print(f"❌ {r['name']:<20} {'error':<8} {r['latency']:>4}s   {r['error'][:40]}")
    print("─" * 60)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"\nنجح: {ok_count}/{len(results)} نماذج")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Docker Model Runner models")
    parser.add_argument(
        "--url",
        default="http://localhost:12434/engines/llama.cpp/v1",
        help="Docker Model Runner base URL",
    )
    parser.add_argument(
        "--skip-unavailable",
        action="store_true",
        help="تخطي النماذج غير المحمَّلة",
    )
    args = parser.parse_args()
    asyncio.run(main(args.url, args.skip_unavailable))
