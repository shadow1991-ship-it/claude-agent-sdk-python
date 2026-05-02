# Xiaomi MiMo-V2.5-Pro — المواصفات والاستخدام

> نموذج استدلالي قوي من Xiaomi | MIT License | مجاني كلياً

---

## نظرة عامة

| المعامل | القيمة |
|---------|--------|
| المطوّر | Xiaomi AI (XiaomiMiMo) |
| الاسم الكامل | MiMo-V2.5-Pro |
| المعمارية | Transformer (مبنية على Qwen) |
| حجم النموذج | 7B parameters |
| الترخيص | MIT (مجاني كلياً) |
| التخصص | Mathematics، Reasoning، Code |
| HuggingFace | `XiaomiMiMo/MiMo-V2.5-Pro` |

---

## لماذا MiMo-V2.5-Pro؟

MiMo (Mi Model) هو مشروع Xiaomi لبناء نماذج استدلالية صغيرة لكن قوية جداً. تتميز نسخة V2.5-Pro بـ:

- **Reinforcement Learning من التفاعل** — تدربت على حل مسائل حقيقية بالـ trial-and-error
- **قوة استدلالية غير متناسبة مع حجمها** — تتفوق على نماذج أكبر في الرياضيات
- **متاحة محلياً** — 7B تعمل على GPU عادي (8GB VRAM)
- **MIT License** — لا قيود على الاستخدام التجاري

---

## Special Tokens

```json
{
  "<think>":       151667,
  "</think>":      151668,
  "<|im_start|>":  151644,
  "<|im_end|>":    151645,
  "<|endoftext|>": 151643
}
```

> نفس special tokens لـ DeepSeek V4 — متوافق مع نفس الـ chat format.

---

## مثال استخدام — تحليل أمني

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:12434/engines/llama.cpp/v1",
    api_key="unused",
)

async def mimo_security_analysis(dockerfile_content: str) -> str:
    response = await client.chat.completions.create(
        model="ai/mimo-v2.5-pro",   # إذا متاح في Docker Model Runner
        messages=[
            {
                "role": "system",
                "content": "You are a security expert. Analyze step by step."
            },
            {
                "role": "user",
                "content": f"Analyze this Dockerfile for security issues:\n\n{dockerfile_content}"
            }
        ],
        max_tokens=2048,
        temperature=0.7,
    )
    return response.choices[0].message.content
```

---

## مقارنة MiMo مع النماذج الأخرى

| | MiMo-V2.5-Pro | Granite Nano | DeepSeek V4-Flash | DeepSeek V4-Pro |
|---|---|---|---|---|
| الحجم | 7B | ~4B | 284B (13B active) | 1.6T (49B active) |
| السرعة | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ | ⚡ |
| الاستدلال الرياضي | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| تحليل الكود | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| VRAM المطلوب | 8GB | 4GB | 24GB+ | 80GB+ |
| السيادة المحلية | ✅ | ✅ | ✅ | ✅ |

---

## Thinking Mode في MiMo

MiMo يدعم أيضاً thinking mode بنفس تنسيق DeepSeek:

```python
# تفعيل التفكير العميق
messages = [
    {"role": "user", "content": "فكّر بعمق: ما أفضل طريقة لتأمين API endpoint؟"}
]
# النموذج يُخرج:
# <think>
#   أحتاج للنظر في: Authentication, Rate Limiting, Input Validation...
#   أولاً: JWT vs API Keys — JWT أفضل لأن...
# </think>
# الجواب: استخدم JWT + Rate Limiting + Input Validation...
```

---

## التوافق مع Sentinel Guard

```python
# في ai_scanner.py — إضافة MiMo كخيار
class ModelRouter:
    MODELS = {
        "fast":     "ai/granite-4.0-nano",      # < 2s
        "reason":   "ai/mimo-v2.5-pro",         # 7B — استدلال محلي قوي
        "deep":     "ai/deepseek-v4-pro",       # كبير — تحليل شامل
        "general":  "ai/deepseek-v4-flash",     # chatbot
    }
```

---

## سحب وتشغيل MiMo محلياً

```bash
# عبر Ollama (إذا متاح)
ollama pull xiaomi/mimo-v2.5-pro

# عبر Docker Model Runner (عند إضافته للـ registry)
docker model pull ai/mimo-v2.5-pro

# مباشرة من HuggingFace
pip install transformers accelerate
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained('XiaomiMiMo/MiMo-V2.5-Pro')
"

# أو عبر llama.cpp (GGUF — الأخف)
# حمّل GGUF من HuggingFace ثم:
llama-server -m MiMo-V2.5-Pro.Q4_K_M.gguf --port 11434
```

---

## سلسلة MiMo الكاملة

| النموذج | الحجم | التخصص |
|---------|-------|---------|
| MiMo-7B-Base | 7B | نموذج أساسي |
| MiMo-7B-RL | 7B | RL محسّن |
| MiMo-7B-RL-Zero | 7B | Zero-shot RL |
| **MiMo-V2.5-Pro** | 7B | **أقوى نسخة** |

---

## مصادر

- HuggingFace: `https://huggingface.co/XiaomiMiMo/MiMo-V2.5-Pro`
- GitHub: `https://github.com/XiaomiMiMo/MiMo`
- Technical Report: في صفحة HuggingFace
