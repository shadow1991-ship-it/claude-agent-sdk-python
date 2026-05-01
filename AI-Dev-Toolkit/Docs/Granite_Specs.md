# IBM Granite 4.0 Nano — المواصفات والاستخدام

> نموذج مجاني محلي عبر Docker Model Runner | SHA256: `34ae9a653d558205...`

---

## نظرة عامة

| المعامل | القيمة |
|---------|--------|
| المطوّر | IBM Research |
| الاسم الكامل | ibm-granite/granite-4.0-nano-instruct |
| الحجم | Nano (مُحسَّن للأجهزة المتواضعة) |
| الترخيص | Apache 2.0 (مجاني كلياً) |
| الاستخدام الأمثل | Code generation، AutoFixer، Pattern check |
| متوسط الاستجابة | < 2 ثانية |

---

## سحب النموذج

```bash
docker model pull ai/granite-4.0-nano
# SHA256: 34ae9a653d558205...

# التحقق
curl http://localhost:12434/engines/llama.cpp/v1/models | jq '.data[].id'
```

---

## قدرات Granite 4.0

| القدرة | التفاصيل |
|--------|---------|
| Code Review | يُحلّل كود Python/Go/JS ويقترح تحسينات |
| Security Patterns | يكتشف أنماط الثغرات في الكود |
| Fix Generation | يُولّد كود الإصلاح المباشر |
| Dockerfile Analysis | يفحص Dockerfiles لأفضل الممارسات |
| Config Validation | يتحقق من صحة ملفات التكوين |

---

## مثال استخدام — AutoFixer

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:12434/engines/llama.cpp/v1",
    api_key="unused",
)

async def generate_fix(finding: dict) -> str:
    prompt = f"""Security finding: {finding['title']}
Description: {finding['description']}
Asset type: {finding.get('category', 'unknown')}

Generate the exact fix code. Return ONLY the code block."""

    response = await client.chat.completions.create(
        model="ai/granite-4.0-nano",
        messages=[
            {"role": "system", "content": "You are a security engineer. Generate precise code fixes."},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=512,
        timeout=10,
    )
    return response.choices[0].message.content
```

---

## أمثلة عملية

### 1. إصلاح Dockerfile Finding

```
Finding: "Missing HEALTHCHECK instruction"

Granite output:
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 2. إصلاح HTTP Header

```
Finding: "Missing X-Content-Type-Options header"

Granite output (nginx):
add_header X-Content-Type-Options "nosniff" always;
```

### 3. Pattern Detection

```python
# يكتشف: eval(), exec(), pickle.loads(), os.system()
# يُقترح: استخدام subprocess مع قائمة بيضاء، ast.literal_eval
```

---

## الفرق بين Granite Nano وباقي النماذج

| النموذج | السرعة | الدقة | الاستخدام |
|---------|--------|-------|-----------|
| Granite Nano | ⚡⚡⚡ | ⭐⭐ | Code fix، pattern check |
| DeepSeek V4 Flash | ⚡⚡ | ⭐⭐⭐ | Chatbot، Q&A |
| Kimi K2.6 / DeepSeek V4 Pro | ⚡ | ⭐⭐⭐⭐⭐ | تحليل أمني عميق |

---

## مصادر

- IBM Granite on Hugging Face: `https://huggingface.co/ibm-granite`
- IBM Granite GitHub: `https://github.com/ibm-granite`
- Docker Hub: `https://hub.docker.com/r/ibmcom/granite`
