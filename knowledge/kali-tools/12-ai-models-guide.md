# دليل نماذج الذكاء الاصطناعي المحلية — AI Models Guide

> جميع النماذج مجانية، تعمل محلياً، لا API key، سيادة كاملة

---

## نماذج مدعومة في Sentinel Guard

### جدول المقارنة السريع

| النموذج | الحجم | السرعة | السياق | الاستخدام الأمثل |
|---------|-------|--------|--------|-----------------|
| `ai/granite-4.0-nano` | ~4B | < 2ث | 128K | AutoFixer، code generation |
| `ai/mimo-v2.5-pro` | 7B | < 5ث | 32K | استدلال رياضي، تحليل منطقي |
| `ai/deepseek-v4-flash` | 284B (13B active) | < 10ث | **1M** | Dashboard chatbot، Q&A |
| `ai/deepseek-v4-pro` | 1.6T (49B active) | < 30ث | **1M** | تحليل أمني عميق، CVE |
| `ai/kimi-k2` | ~1T MoE | < 30ث | 128K | Dockerfile analysis |
| `ai/deepseek-v3-0324` | 671B (37B active) | < 15ث | 64K | Fallback عام |

---

## DeepSeek-V4-Pro وV4-Flash

### المعمارية

```
MoE Architecture (Mixture of Experts):
  V4-Pro:   1.6T total → 49B active per token
  V4-Flash: 284B total → 13B active per token

Hybrid Attention:
  CSA (Compressed Sparse Attention) — long range context
  HCA (Heavily Compressed Attention) — efficiency

Context: 1,000,000 tokens (1M) — كامل codebase في prompt واحد
```

### أوضاع التفكير — Thinking Modes

```python
# Non-think — استجابة فورية
messages = [{"role": "user", "content": "سؤال بسيط"}]
# الرد: مباشر بدون تفكير

# Think High — تفكير واعٍ
# النموذج يُخرج:
# <think>
#   [تحليل متعدد الخطوات]
# </think>
# [الجواب النهائي]

# Think Max — أقصى استدلال
# يحتاج: temperature=1.0, top_p=1.0, context >= 384K
# system_prompt += "\nThink as deeply as possible."
```

### Special Tokens (مهمة للـ parsing)

```python
THINK_OPEN  = "<think>"    # token id: 151667
THINK_CLOSE = "</think>"   # token id: 151668
IM_START    = "<|im_start|>"  # id: 151644
IM_END      = "<|im_end|>"    # id: 151645

# Python — كيفية استخراج الـ thinking block من الرد
def parse_thinking(response: str) -> tuple[str, str]:
    """يُرجع (thinking_block, final_answer)."""
    import re
    think = re.search(r"<think>(.*?)</think>", response, re.DOTALL)
    thinking = think.group(1).strip() if think else ""
    answer = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    return thinking, answer
```

---

## Xiaomi MiMo-V2.5-Pro

### لماذا هو مثير للاهتمام؟

```
7B فقط لكن يتفوق على نماذج 70B في:
  ✅ Mathematical reasoning (AMC، AIME)
  ✅ Logical deduction (multi-step)
  ✅ Code debugging
  ✅ Security vulnerability analysis

السر: تدريب بـ Reinforcement Learning على مسائل حقيقية
```

### أداء MiMo vs نماذج أكبر

```
AIME 2025:    MiMo-7B ≈ o1-mini (OpenAI)
LiveCodeBench: MiMo-7B > DeepSeek-Coder-33B
MATH:          MiMo-7B > Qwen2.5-72B-Instruct
```

### متى تستخدم MiMo؟

```
✅ تحليل Dockerfile منطقي — يتبع سلسلة RUN متعددة
✅ CVE reasoning — يربط vulnerability بـ exploitation path
✅ Security logic — يستنتج attack chains
✅ Code analysis — يتبع data flow
❌ كميات نصية ضخمة — context محدود (32K)
❌ اللغة العربية — ضعيف نسبياً، استخدم DeepSeek
```

---

## IBM Granite 4.0 Nano

### لماذا هو مثالي للـ AutoFixer؟

```
التخصص: code generation سريع جداً

مثال: تعطيه finding →  يُعيد الإصلاح خلال < 2 ثانية

Finding: "Missing HEALTHCHECK in Dockerfile"
Granite output (2 ثانية):
  HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```

### أنماط الاستخدام

```python
# AutoFixer — الحالة الأكثر شيوعاً
async def auto_fix(finding_title: str, asset_type: str) -> str:
    prompt = f"""Fix this security finding:
Title: {finding_title}
Asset: {asset_type}
Return ONLY the fix code, no explanation."""

    r = await client.chat.completions.create(
        model="ai/granite-4.0-nano",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        timeout=8,
    )
    return r.choices[0].message.content
```

---

## نمط توجيه المهام في Sentinel Guard

```python
class ModelRouter:
    """يختار النموذج المناسب حسب المهمة والوقت المتاح."""

    async def route(self, task: str, payload: str, budget_ms: int = 30000) -> str:
        if budget_ms < 3000:
            return await self.fast(payload)      # Granite Nano
        elif task in ("dockerfile", "cve", "sbom"):
            return await self.deep(payload)      # DeepSeek V4-Pro
        elif task == "reason":
            return await self.reason(payload)    # MiMo V2.5-Pro
        else:
            return await self.chat(payload)      # DeepSeek V4-Flash
```

---

## سحب جميع النماذج

```bash
# الأساسية (يُنصح بها للبداية)
docker model pull ai/deepseek-v4-flash    # dashboard chatbot — 1M context
docker model pull ai/granite-4.0-nano     # AutoFixer — سريع جداً

# المتقدمة
docker model pull ai/deepseek-v4-pro      # تحليل أمني عميق — يحتاج GPU
docker model pull ai/kimi-k2              # MoE عميق

# التحقق من الكل
curl -s http://localhost:12434/engines/llama.cpp/v1/models | \
  python3 -c "import json,sys; [print('✅', m['id']) for m in json.load(sys.stdin)['data']]"
```

---

## معلومات تقنية مفيدة

### FP4 + FP8 Mixed Precision (DeepSeek V4)

```
MoE expert parameters  → FP4  (أخف — سرعة أكبر)
باقي البارامترات        → FP8  (دقة أعلى)

الفائدة:
  - حجم ملف أصغر بـ 50% من FP16
  - نفس الدقة تقريباً
  - مناسب لـ Docker Model Runner
```

### YaRN Rope Scaling (لتمديد السياق)

```python
# DeepSeek V4 يستخدم YaRN factor=16 لتمديد السياق من 4K → 1M
# لا حاجة لإعداد إضافي — Docker Model Runner يتولى ذلك
# الاستخدام المثالي: ابعث كامل الـ codebase في prompt واحد

long_context_prompt = f"""
Analyze this entire Docker Compose file + all Dockerfiles for security issues:

{docker_compose_content}

{"\n\n---\n\n".join(all_dockerfiles)}
"""
# يعمل مع DeepSeek V4 — سياق حتى 1M token
```

---

## قواعد الاستخدام

```
✅ تشغيل النماذج محلياً على جهازك
✅ تحليل أصولك الخاصة (repos، Dockerfiles، configs)
✅ CTF: استخدام AI لحل تحديات الأمن
✅ AutoFix لثغرات في مشاريعك
❌ لا تُرسل كود/بيانات حساسة لنماذج cloud
❌ لا تستخدم النماذج لتحليل أنظمة غير مملوكة
```
