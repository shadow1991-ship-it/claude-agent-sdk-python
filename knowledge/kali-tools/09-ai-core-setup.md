# إعداد نواة الذكاء الاصطناعي المحلية

> جميع النماذج تعمل محلياً — لا إنترنت، لا API key، لا تكلفة.
> ممنوع --privileged | ممنوع --net=host | السيادة كاملة لك

---

## الخيار 1: Ollama (الأبسط والأسرع)

### تشغيل Ollama (آمن — بدون --privileged، بدون --net=host)
```bash
docker run -d \
  --name sentinel_ai_core \
  -v /sentinel_data/ollama:/root/.ollama \
  -p 11434:11434 \
  --restart always \
  ollama/ollama
```

### تحميل النماذج
```bash
# نموذج عربي قوي (ميزة)
docker exec sentinel_ai_core ollama pull qwen2.5:7b

# نموذج أمني متخصص
docker exec sentinel_ai_core ollama pull llama3.1:8b

# نموذج خفيف سريع
docker exec sentinel_ai_core ollama pull phi3.5:mini

# نموذج كود
docker exec sentinel_ai_core ollama pull deepseek-coder:6.7b

# قائمة النماذج المثبتة
docker exec sentinel_ai_core ollama list
```

### اختبار Ollama
```bash
# سؤال بسيط
curl http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:7b","prompt":"مرحبا","stream":false}'

# قائمة النماذج
curl http://localhost:11434/api/tags

# OpenAI-compatible endpoint (نفس واجهة Docker Model Runner)
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [{"role":"user","content":"مرحبا"}]
  }'
```

---

## الخيار 2: Docker Model Runner (مُدمج مع Docker Desktop)

```bash
# تحقق من التشغيل
docker model ls

# تحميل نماذج
docker model pull ai/deepseek-v4-flash   # الـ dashboard chatbot
docker model pull ai/granite-4.0-nano   # AutoFixer السريع
docker model pull ai/deepseek-v4-pro    # التحليل العميق

# اختبار
curl http://localhost:12434/engines/llama.cpp/v1/models
```

---

## الخيار 3: تشغيل الاثنين معاً

```yaml
# docker-compose.yml للـ AI core
services:
  ollama:
    image: ollama/ollama
    container_name: sentinel_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: always
    # ⛔ لا --privileged | لا --net=host

volumes:
  ollama_data:
```

```bash
docker compose up -d
docker exec sentinel_ollama ollama pull qwen2.5:7b
```

---

## النماذج الموصى بها للأمن السيبراني

| النموذج | الحجم | الاستخدام | الأمر |
|---------|-------|-----------|-------|
| `qwen2.5:7b` | 4.7GB | عربي ممتاز، متعدد المهام | `ollama pull qwen2.5:7b` |
| `llama3.1:8b` | 4.9GB | تحليل أمني، كود | `ollama pull llama3.1:8b` |
| `phi3.5:mini` | 2.2GB | سريع جداً، محادثة | `ollama pull phi3.5:mini` |
| `deepseek-coder:6.7b` | 3.8GB | تحليل كود، ثغرات | `ollama pull deepseek-coder:6.7b` |
| `mistral:7b` | 4.1GB | تعليمات، تحليل | `ollama pull mistral:7b` |

---

## ربط Ollama بـ Sentinel Guard

في ملف `empire/.env`:
```env
# اختر المزود
AI_BACKEND=ollama              # أو: docker_model_runner

# Ollama
OLLAMA_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b

# Docker Model Runner (البديل)
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_MODEL_GENERAL=ai/deepseek-v4-flash
```

في `web_dashboard.py` — يختار المزود تلقائياً:
```python
# يجرب Ollama أولاً، إذا فشل → Docker Model Runner
AI_URL = os.getenv("OLLAMA_URL", os.getenv(
    "DOCKER_MODEL_RUNNER_URL",
    "http://localhost:12434/engines/llama.cpp/v1"
))
AI_MODEL = os.getenv("OLLAMA_MODEL", os.getenv(
    "AI_MODEL_GENERAL",
    "ai/deepseek-v4-flash"
))
```
