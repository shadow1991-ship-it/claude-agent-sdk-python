# DeepSeek-V4-Pro & Flash — المواصفات الكاملة

> MIT License | مجاني كلياً | يعمل عبر Docker Model Runner

---

## نظرة عامة

| | **V4-Pro** | **V4-Flash** |
|---|---|---|
| المعمارية | MoE | MoE |
| إجمالي البارامترات | 1.6T | 284B |
| البارامترات النشطة | 49B | 13B |
| طول السياق | **1M token** | **1M token** |
| الدقة | FP4 + FP8 Mixed | FP4 + FP8 Mixed |
| الترخيص | MIT | MIT |
| الاستخدام الأمثل | تحليل أمني عميق، كود | chatbot، Q&A سريع |

---

## أبرز الابتكارات المعمارية

### 1. Hybrid Attention (CSA + HCA)
- **CSA** (Compressed Sparse Attention) — انتباه متفرق للسياق البعيد
- **HCA** (Heavily Compressed Attention) — انتباه مضغوط للكفاءة
- في سياق 1M token: يحتاج فقط **27% من FLOPs** و**10% من KV cache** مقارنة بـ V3.2

### 2. Manifold-Constrained Hyper-Connections (mHC)
- يُقوّي الـ residual connections التقليدية
- يُحسّن استقرار انتشار الإشارة عبر الطبقات
- يحافظ على تعبيرية النموذج

### 3. Muon Optimizer (تدريب)
- تقارب أسرع من Adam
- استقرار أكبر في التدريب على 32T+ token

---

## أوضاع التفكير — Thinking Modes

| الوضع | السرعة | الدقة | الاستخدام |
|-------|--------|-------|-----------|
| **Non-think** | ⚡⚡⚡ | ⭐⭐ | مهام روتينية، أسئلة بسيطة |
| **Think High** | ⚡⚡ | ⭐⭐⭐⭐ | مسائل معقدة، تحليل أمني |
| **Think Max** | ⚡ | ⭐⭐⭐⭐⭐ | أصعب المسائل، استنتاج متعدد الخطوات |

### تنسيق الرد

```
Non-think:  </think>  النتيجة المباشرة
Think High: <think> ... تفكير منطقي ... </think>  الجواب النهائي
Think Max:  <think> ... تفكير عميق جداً ... </think>  الجواب النهائي
```

---

## Special Tokens

```json
{
  "<|im_start|>": 151644,
  "<|im_end|>":   151645,
  "<think>":      151667,
  "</think>":     151668,
  "<|fim_prefix|>": 151659,
  "<|fim_middle|>": 151660,
  "<|fim_suffix|>": 151661,
  "<|file_sep|>":   151664,
  "<|repo_name|>":  151663,
  "<|endoftext|>":  151643
}
```

> **ملاحظة:** عند استخدام OpenAI-compatible API (Docker Model Runner)، لا داعي للتعامل مع هذه الـ tokens يدوياً.

---

## تنسيق الرسائل (Chat Template)

```python
# بدون Jinja template — استخدام encoding_dsv4 الرسمي أو OpenAI API
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:12434/engines/llama.cpp/v1",
    api_key="unused",
)

# Non-think mode (سريع)
response = await client.chat.completions.create(
    model="ai/deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "أنت مساعد أمني خبير."},
        {"role": "user",   "content": "ما هي أخطر ثغرات Docker؟"},
    ],
    max_tokens=1024,
)

# Think High mode (تحليل معمق)
response = await client.chat.completions.create(
    model="ai/deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "أنت مساعد أمني. فكّر بعمق قبل الإجابة."},
        {"role": "user",   "content": "<think>هل هذا الـ Dockerfile آمن؟ ...</think>"},
    ],
    max_tokens=4096,
    temperature=1.0,
    top_p=1.0,
)
```

---

## نتائج الأداء البارزة (V4-Pro-Max)

| المعيار | DS V4-Pro Max |
|---------|--------------|
| LiveCodeBench | **93.5%** (الأول عالمياً) |
| Codeforces Rating | **3206** (الأول عالمياً) |
| MMLU-Pro | 87.5% |
| GPQA Diamond | 90.1% |
| SWE-bench Verified | 80.6% |
| Long Context (MRCR 1M) | 83.5% |

---

## الاستخدام في Sentinel Guard

```python
# توجيه المهام الأمثل
AI_MODELS = {
    "chatbot":  "ai/deepseek-v4-flash",   # dashboard chat — سريع
    "analysis": "ai/deepseek-v4-pro",     # Dockerfile + CVE — دقيق
    "codegen":  "ai/granite-4.0-nano",    # AutoFixer — أسرع للكود
    "fallback": "ai/deepseek-v3-0324",    # إذا V4 غير متاح
}

# إعدادات الـ sampling الموصى بها
SAMPLING = {"temperature": 1.0, "top_p": 1.0}

# Think Max: سياق لا يقل عن 384K token
THINK_MAX_CONTEXT = 384_000
```

---

## سحب النماذج

```bash
# الأخف (dashboard chatbot)
docker model pull ai/deepseek-v4-flash

# الأقوى (تحليل أمني عميق)
docker model pull ai/deepseek-v4-pro

# التحقق
curl http://localhost:12434/engines/llama.cpp/v1/models | jq '.data[].id'
```

---

## مصادر

- HuggingFace: `https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro`
- Technical Report: `https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf`
- GitHub: `https://github.com/deepseek-ai`
