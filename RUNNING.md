# RUNNING — دليل التشغيل التفصيلي الكامل

> هذا الدليل يأخذك من الصفر إلى نظام يعمل بالكامل خطوة بخطوة.  
> وقت التثبيت الإجمالي: **15-30 دقيقة** (حسب سرعة الإنترنت لتحميل النماذج).

---

## فهرس

1. [متطلبات الجهاز](#1--متطلبات-الجهاز)
2. [تثبيت المتطلبات](#2--تثبيت-المتطلبات)
3. [تفعيل Docker Model Runner](#3--تفعيل-docker-model-runner)
4. [تحميل نماذج AI](#4--تحميل-نماذج-ai)
5. [إعداد sentinel-guard Backend](#5--إعداد-sentinel-guard-backend)
6. [تشغيل الـ Backend](#6--تشغيل-الـ-backend)
7. [التحقق من صحة الـ Backend](#7--التحقق-من-صحة-الـ-backend)
8. [إعداد Web Dashboard](#8--إعداد-web-dashboard)
9. [تشغيل Dashboard](#9--تشغيل-dashboard)
10. [أول استخدام — API Flow كامل](#10--أول-استخدام--api-flow-كامل)
11. [اختبار النماذج AI](#11--اختبار-نماذج-ai)
12. [إعداد AI-Dev-Toolkit](#12--إعداد-ai-dev-toolkit)
13. [مشاكل شائعة وحلولها](#13--مشاكل-شائعة-وحلولها)
14. [نشر الإنتاج](#14--نشر-الإنتاج)
15. [مرجع سريع](#15--مرجع-سريع)

---

## 1 — متطلبات الجهاز

### الحد الأدنى (للتطوير)

| المورد | الحد الأدنى | الموصى به |
|--------|-----------|-----------|
| CPU | 4 أنوية | 8+ أنوية |
| RAM | 16 GB | 32 GB |
| مساحة القرص | 30 GB فارغة | 80 GB+ |
| GPU VRAM | غير مطلوب (CPU inference) | 8 GB+ |
| نظام التشغيل | macOS 13+ / Windows 11 / Ubuntu 22.04+ | — |

### متطلبات النماذج AI (تراكمية)

| النموذج | الحجم على القرص | VRAM للتشغيل |
|---------|----------------|-------------|
| `ai/granite-4.0-nano` | ~2.5 GB | 4 GB GPU أو CPU |
| `ai/deepseek-v4-flash` | ~8 GB | 8 GB GPU أو CPU (بطيء) |
| `ai/deepseek-v4-pro` | ~15 GB | 24 GB GPU أو CPU (بطيء جداً) |
| `ai/mimo-v2.5-pro` | ~4 GB | 6 GB GPU أو CPU |

> **نصيحة:** ابدأ بـ `granite-4.0-nano` + `deepseek-v4-flash` فقط (10 GB إجمالاً). كافيان لتشغيل النظام كاملاً.

---

## 2 — تثبيت المتطلبات

### 2.1 Docker Desktop

**macOS:**
```bash
# عبر Homebrew
brew install --cask docker

# أو حمّل مباشرة من:
# https://www.docker.com/products/docker-desktop/
```

**Windows:**
```powershell
# عبر winget
winget install Docker.DockerDesktop

# أو من الموقع الرسمي
```

**Linux (Ubuntu/Debian):**
```bash
# تثبيت Docker Engine
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker

# تثبيت Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# تحقق
docker --version        # Docker version 27.x.x
docker compose version  # Docker Compose version v2.x.x
```

> **ملاحظة Linux:** Docker Model Runner يتطلب Docker Desktop. على Linux يمكن استخدام Ollama كبديل (اقرأ القسم 3).

### 2.2 Python 3.11+

**macOS:**
```bash
brew install python@3.11
python3 --version  # Python 3.11.x
```

**Windows:**
```powershell
# من Microsoft Store أو:
winget install Python.Python.3.11
```

**Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```

### 2.3 تحميل المشروع

```bash
git clone https://github.com/shadow1991-ship-it/claude-agent-sdk-python.git
cd claude-agent-sdk-python

# تحقق من الهيكل
ls -la
# يجب أن ترى: sentinel-guard/  empire/  web_dashboard.py  AI-Dev-Toolkit/  knowledge/
```

---

## 3 — تفعيل Docker Model Runner

### على macOS / Windows (Docker Desktop)

1. افتح Docker Desktop
2. انتقل إلى: **Settings → Features in Development**
3. فعّل: **✅ Docker Model Runner** أو **Enable Docker Model Runner**
4. اضغط **Apply & Restart**
5. انتظر إعادة تشغيل Docker Desktop

**تحقق من التفعيل:**
```bash
docker model ls
# يجب أن يُعطيك قائمة (حتى لو فارغة) بدون خطأ
```

إذا ظهر `docker: 'model' is not a docker command`:
- تأكد من تحديث Docker Desktop إلى الإصدار 4.40+
- أعد تشغيل Docker Desktop

### على Linux — بديل Ollama

```bash
# تثبيت Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# تشغيله كخدمة
sudo systemctl enable ollama
sudo systemctl start ollama

# اضبط المتغير للتوافق
# في sentinel-guard/.env:
DOCKER_MODEL_RUNNER_URL=http://localhost:11434/v1

# في empire/.env:
DOCKER_MODEL_RUNNER_URL=http://localhost:11434/v1
OLLAMA_URL=http://localhost:11434/v1
```

---

## 4 — تحميل نماذج AI

### الحد الأدنى المطلوب (نموذج واحد كافٍ للبدء)

```bash
# الأسرع والأخف — AutoFixer + كود generation
docker model pull ai/granite-4.0-nano
# الحجم: ~2.5 GB | الوقت: 2-5 دقائق
```

### الموصى به (للـ dashboard والتحليل)

```bash
# Dashboard chatbot + سياق 1 مليون token
docker model pull ai/deepseek-v4-flash
# الحجم: ~8 GB | الوقت: 5-15 دقيقة

# AutoFixer (إذا لم يُحمَّل granite)
docker model pull ai/granite-4.0-nano
# الحجم: ~2.5 GB | الوقت: 2-5 دقائق
```

### الكامل (لجميع الميزات)

```bash
docker model pull ai/granite-4.0-nano     # AutoFixer
docker model pull ai/deepseek-v4-flash    # chatbot / 1M context
docker model pull ai/deepseek-v4-pro      # تحليل أمني عميق
docker model pull ai/mimo-v2.5-pro        # استدلال منطقي (Xiaomi 7B)
docker model pull ai/deepseek-v3-0324     # fallback
```

**تتبع التحميل:**
```bash
# في terminal آخر — مراقبة التقدم
watch -n5 'docker model ls'
```

**بعد الانتهاء:**
```bash
docker model ls
# NAME                      SIZE
# ai/granite-4.0-nano       2.5 GB
# ai/deepseek-v4-flash      8.1 GB
# ...

# اختبار سريع
curl -s http://localhost:12434/engines/llama.cpp/v1/models | python3 -m json.tool
```

---

## 5 — إعداد sentinel-guard Backend

### 5.1 نسخ ملف البيئة

```bash
cd sentinel-guard
cp .env.example .env
```

### 5.2 توليد SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# مثال الناتج: xK9m2P...  (80+ حرف)
```

افتح `.env` وضع الناتج:
```env
SECRET_KEY=xK9m2P...الناتج_الكامل_هنا
```

### 5.3 ضبط متغيرات AI

```env
# المتغيرات الأساسية المطلوبة في sentinel-guard/.env
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_ENABLED=true
AI_TIMEOUT=60

# النماذج (حسب ما حمّلته في الخطوة 4)
AI_MODEL_FAST=ai/granite-4.0-nano
AI_MODEL_GENERAL=ai/deepseek-v4-flash
AI_MODEL_DEEP=ai/deepseek-v4-pro
AI_MODEL_REASON=ai/mimo-v2.5-pro
AI_MODEL_FALLBACK=ai/deepseek-v3-0324
```

> إذا لم تُحمّل نموذجاً معيناً، اتركه فارغاً وسيُعطّل تلقائياً عند الخطأ.

### 5.4 Shodan (اختياري)

```bash
# احصل على مفتاح مجاني من:
# https://account.shodan.io → Get API Key

# أضفه في .env:
SHODAN_API_KEY=your_actual_key_here

# للتحقق:
python3 -c "import shodan; api=shodan.Shodan('YOUR_KEY'); print(api.info())"
```

---

## 6 — تشغيل الـ Backend

### 6.1 بناء وتشغيل الـ containers

```bash
# داخل sentinel-guard/
docker compose up --build -d

# مراقبة الـ logs أثناء البناء
docker compose logs -f
```

**الوقت المتوقع للـ build الأول:** 3-8 دقائق (تحميل Python image + تثبيت packages)

### 6.2 تهيئة قاعدة البيانات

```bash
# انتظر حتى تصبح db healthy أولاً
docker compose ps
# db يجب أن يكون: Up (healthy)

# ثم شغّل migrations
docker compose exec api alembic upgrade head
```

الناتج المتوقع:
```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> a1b2c3d4e5f6, initial schema
```

> تُنفَّذ **مرة واحدة فقط** عند أول تشغيل، أو بعد أي تعديل على الـ models.

---

## 7 — التحقق من صحة الـ Backend

### 7.1 فحص حالة الـ containers

```bash
docker compose ps
```

المتوقع:
```
NAME                       STATUS           PORTS
sentinel-guard-api-1       Up               0.0.0.0:8000->8000/tcp
sentinel-guard-worker-1    Up
sentinel-guard-db-1        Up (healthy)
sentinel-guard-redis-1     Up (healthy)
```

إذا كان container بحالة `Exit`:
```bash
docker compose logs api --tail=50
docker compose logs worker --tail=50
```

### 7.2 فحص الـ API

```bash
# Health check
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}

# Swagger UI
open http://localhost:8000/docs  # macOS
# أو افتح في المتصفح: http://localhost:8000/docs
```

### 7.3 فحص الـ AI

```bash
# من داخل container — اختبار Docker Model Runner
curl http://localhost:12434/engines/llama.cpp/v1/models

# الناتج المتوقع:
# {"object":"list","data":[{"id":"ai/granite-4.0-nano",...}]}
```

---

## 8 — إعداد Web Dashboard

### 8.1 نسخ ملف البيئة

```bash
cd empire
cp .env.example .env
```

### 8.2 ضبط المتغيرات

افتح `empire/.env`:

```env
# API
SENTINEL_API_URL=http://localhost:8000/api/v1

# Dashboard — ولّد DASHBOARD_SECRET
# python3 -c "import secrets; print(secrets.token_urlsafe(48))"
DASHBOARD_SECRET=YOUR_GENERATED_SECRET_HERE
DASHBOARD_PASSWORD=كلمة_سرك_القوية_هنا
DASHBOARD_PORT=5000

# AI — نفس النماذج المُحمَّلة
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_MODEL_GENERAL=ai/deepseek-v4-flash
AI_MODEL_DEEP=ai/deepseek-v4-pro
AI_MODEL_FAST=ai/granite-4.0-nano
AI_MODEL_REASON=ai/mimo-v2.5-pro
AI_ENABLED=true
```

### 8.3 تثبيت Python dependencies

```bash
cd ..  # ارجع لجذر المشروع

# إنشاء virtual environment (موصى به)
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# أو على Windows: .venv\Scripts\activate

# تثبيت المكتبات
pip install flask openai
# اختياري إذا أردت Gemini:
# pip install google-genai
```

---

## 9 — تشغيل Dashboard

```bash
# من جذر المشروع
source .venv/bin/activate  # إذا استخدمت venv

# تحميل متغيرات empire/.env
set -a && source empire/.env && set +a

python web_dashboard.py
```

الناتج المتوقع:
```
[SENTINEL] ● Dashboard    : http://localhost:5000
[SENTINEL] ● AI Backend   : Local · deepseek-v4-flash @ localhost:12434
[SENTINEL] ● Knowledge    : 487 lines
[SENTINEL] ● Sovereignty  : --privileged BLOCKED | --net=host BLOCKED
```

افتح: **http://localhost:5000**

كلمة السر: ما وضعته في `DASHBOARD_PASSWORD`.

### مميزات الـ Dashboard

| القسم | الوصف |
|-------|-------|
| نظرة عامة | Stats + Threat gauge + Findings |
| الرادار | Nmap Hacker's Radar — عرض الأصول |
| Dockerfile | فحص Dockerfile من URL مباشرة |
| API | روابط Swagger + نقاط API |
| AI Terminal | chatbot بـ 5 نماذج + 3 أوضاع تفكير |

**اختيار النموذج في Terminal:**
```
⚡ V4-Flash (1M)   → للـ chatbot العام
🧠 V4-Pro (Deep)   → للتحليل الأمني
🔧 Granite (Fix)   → لتوليد كود الإصلاح
🔬 MiMo (Reason)  → للاستدلال المنطقي
💾 V3 (Fallback)  → إذا V4 غير متاح
```

**أوضاع التفكير (Thinking Modes):**
```
OFF  → استجابة فورية
HIGH → <think>تحليل منطقي</think> الجواب
MAX  → تفكير عميق جداً + عرض مرئي قابل للطي
```

---

## 10 — أول استخدام — API Flow كامل

```bash
# ── حدّد الـ base URL ─────────────────────────────────────────────
BASE=http://localhost:8000/api/v1

# ── الخطوة 1: إنشاء حساب ─────────────────────────────────────────
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@myorg.com",
    "password": "StrongPass123!",
    "organization_name": "My Security Org"
  }' | python3 -m json.tool

# ── الخطوة 2: تسجيل الدخول ──────────────────────────────────────
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@myorg.com","password":"StrongPass123!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Token: ${TOKEN:0:20}..."

# ── الخطوة 3: إضافة أصل ─────────────────────────────────────────
ASSET_ID=$(curl -s -X POST $BASE/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "example.com",
    "asset_type": "domain",
    "verification_method": "dns_txt"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "✅ Asset ID: $ASSET_ID"

# ── الخطوة 4: الحصول على تعليمات التحقق ────────────────────────
curl -s $BASE/assets/$ASSET_ID/challenge \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# الناتج يشمل:
# "dns_record": "sentinel-verification=abc123..."
# → أضف هذا كـ TXT record في DNS الخاص بك

# ── الخطوة 5: التحقق من الملكية ─────────────────────────────────
# (بعد انتظار انتشار DNS — 5-60 دقيقة)
curl -s -X POST $BASE/assets/$ASSET_ID/verify \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# ── الخطوة 6: طلب فحص ───────────────────────────────────────────
SCAN_ID=$(curl -s -X POST $BASE/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"asset_id\":\"$ASSET_ID\",\"scan_type\":\"full\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "✅ Scan ID: $SCAN_ID"

# ── الخطوة 7: متابعة حالة الفحص ─────────────────────────────────
watch -n5 "curl -s $BASE/scans/$SCAN_ID \
  -H 'Authorization: Bearer $TOKEN' \
  | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d['status'], d.get('progress',''))\""

# انتظر حتى يظهر: completed

# ── الخطوة 8: عرض النتائج ───────────────────────────────────────
curl -s $BASE/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Status: {d[\"status\"]}')
print(f'Risk Score: {d.get(\"risk_score\", 0)}/100')
print(f'Findings: {d.get(\"findings_count\", 0)}')
for f in d.get('findings', []):
    print(f'  [{f[\"severity\"].upper()}] {f[\"title\"]}')
"

# ── الخطوة 9: AutoFixer لـ finding محدد ─────────────────────────
FINDING_ID=$(curl -s $BASE/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
findings=json.load(sys.stdin).get('findings',[])
# خذ أول critical أو high finding
for f in findings:
    if f['severity'] in ('critical','high'):
        print(f['id']); break
")

curl -s -X POST $BASE/scans/$SCAN_ID/findings/$FINDING_ID/fix \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# ── الخطوة 10: تصدير SARIF ──────────────────────────────────────
curl -s $BASE/scans/$SCAN_ID/sarif \
  -H "Authorization: Bearer $TOKEN" -o results.sarif
echo "✅ SARIF saved: results.sarif ($(wc -c < results.sarif) bytes)"

# ── الخطوة 11: تقرير موقّع ──────────────────────────────────────
REPORT_ID=$(curl -s -X POST $BASE/reports/generate/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s $BASE/reports/$REPORT_ID/verify \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 11 — اختبار نماذج AI

```bash
# اختبار سريع لجميع النماذج المُحمَّلة
python3 AI-Dev-Toolkit/Scripts/test_models.py

# الناتج المتوقع:
# Docker Model Runner → http://localhost:12434/engines/llama.cpp/v1
# نماذج متاحة: ai/granite-4.0-nano, ai/deepseek-v4-flash
#
# ─────────────────────────────────────────────────────
# النموذج              الحالة  الزمن  الرد
# ─────────────────────────────────────────────────────
# ✅ granite-4.0-nano   ok      1.2s   GRANITE_OK
# ✅ deepseek-v4-flash  ok      4.8s   DEEPSEEK_OK
# ❌ kimi-k2            error   0.1s   Connection refused
# ─────────────────────────────────────────────────────
# نجح: 2/3 نماذج

# اختبار نموذج محدد فقط
python3 -c "
import asyncio
from openai import AsyncOpenAI

async def test():
    c = AsyncOpenAI(
        base_url='http://localhost:12434/engines/llama.cpp/v1',
        api_key='unused'
    )
    r = await c.chat.completions.create(
        model='ai/deepseek-v4-flash',
        messages=[{'role':'user','content':'قل: مرحبا'}],
        max_tokens=20,
    )
    print(r.choices[0].message.content)

asyncio.run(test())
"
```

---

## 12 — إعداد AI-Dev-Toolkit

```bash
cd AI-Dev-Toolkit

# تشغيل 5 نماذج في بيئة منفصلة
docker compose up -d

# اختبار Lambda محلياً
cd lambda
docker build -t sentinel-lambda .
docker run -p 9000:8080 sentinel-lambda

# في terminal آخر
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "dockerfile",
    "target": "https://raw.githubusercontent.com/your/repo/main/Dockerfile"
  }'
```

---

## 13 — مشاكل شائعة وحلولها

### المشكلة: `docker model ls` يُعطي خطأ

```
Error: 'model' is not a docker command
```

**الحل:**
```bash
# تحقق من إصدار Docker Desktop
docker --version  # يجب أن يكون 27.x+

# فعّل Model Runner من:
# Docker Desktop → Settings → Features in Development → Docker Model Runner

# أعد تشغيل Docker Desktop كاملاً
```

---

### المشكلة: الـ API لا يبدأ

```
sentinel-guard-api-1  Exit 1
```

**التشخيص:**
```bash
docker compose logs api --tail=30
```

**حلول شائعة:**

| الخطأ في الـ log | السبب | الحل |
|----------------|-------|------|
| `SECRET_KEY must be set` | مفتاح فارغ | أضف SECRET_KEY في `.env` |
| `could not connect to server` | قاعدة البيانات لم تجهز | انتظر db healthy ثم `docker compose restart api` |
| `ModuleNotFoundError` | package مفقود | `docker compose up --build` لإعادة البناء |
| `Address already in use` | منفذ 8000 مستخدم | غيّر `"8001:8000"` في docker-compose.yml |

---

### المشكلة: الفحص يبقى `queued`

**التشخيص:**
```bash
docker compose logs worker --tail=20
```

**الحل:**
```bash
# تحقق من Redis
docker compose exec redis redis-cli ping
# PONG ← صحيح

# أعد تشغيل worker
docker compose restart worker

# إذا استمرت المشكلة
docker compose down && docker compose up -d
docker compose exec api alembic upgrade head
```

---

### المشكلة: AI لا يستجيب

```
⚠ خطأ: Connection refused [http://localhost:12434]
```

**الحل:**
```bash
# تحقق من تشغيل Model Runner
docker model ls

# إذا لم يعطِ قائمة — أعد تشغيل Docker Desktop
# ثم تحقق مجدداً:
curl http://localhost:12434/engines/llama.cpp/v1/models

# تحقق من أن النموذج محمَّل
docker model ls | grep deepseek-v4-flash
# إذا فارغ:
docker model pull ai/deepseek-v4-flash
```

---

### المشكلة: `alembic: not found`

```bash
# خطأ — لا تُنفّذ alembic من خارج container
alembic upgrade head  # ❌

# صحيح — من داخل container
docker compose exec api alembic upgrade head  # ✅
```

---

### المشكلة: Dashboard لا يتصل بـ API

```
⚠ خطأ في الاتصال بـ AI
```

**التحقق:**
```bash
# من جهاز Dashboard تجاه API
curl http://localhost:8000/health

# إذا فشل — تحقق من أن sentinel-guard يعمل
docker compose ps

# وأن SENTINEL_API_URL صحيح في empire/.env
grep SENTINEL_API_URL empire/.env
```

---

### المشكلة: نموذج AI بطيء جداً

إذا كان الرد يأخذ أكثر من دقيقة، النموذج يعمل على CPU:

```bash
# تحقق من GPU
nvidia-smi  # Linux مع NVIDIA GPU
system_profiler SPDisplaysDataType | grep VRAM  # macOS

# على CPU — استخدم نموذجاً أصغر:
AI_MODEL_GENERAL=ai/granite-4.0-nano  # أسرع بكثير على CPU

# أو زد AI_TIMEOUT:
AI_TIMEOUT=120
```

---

## 14 — نشر الإنتاج

### قائمة التحقق قبل النشر

```bash
# 1. ملفات .env لا تُرفع على git
cat .gitignore | grep env
# يجب أن يظهر: *.env  أو  .env

# 2. SECRET_KEY قوي وطويل
python3 -c "
import os
key = open('sentinel-guard/.env').read()
import re
m = re.search(r'SECRET_KEY=(.+)', key)
if m:
    print(f'Length: {len(m.group(1))} chars')
    print('✅ OK' if len(m.group(1)) >= 64 else '❌ Too short!')
"

# 3. DEBUG=false
grep 'DEBUG=' sentinel-guard/.env
# DEBUG=false ← يجب أن يكون false

# 4. CORS محدود
grep 'CORS_ORIGINS' sentinel-guard/.env
# يجب: CORS_ORIGINS=https://yourdomain.com
# ليس: CORS_ORIGINS=*

# 5. تحقق من الـ migrations
docker compose exec api alembic current
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/sentinel-guard
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options    "nosniff" always;
    add_header X-Frame-Options           "DENY" always;
    add_header X-XSS-Protection          "1; mode=block" always;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        # للـ SSE (Server-Sent Events)
        proxy_buffering    off;
        proxy_cache        off;
    }
}
```

```bash
# تفعيل وتشغيل
sudo ln -s /etc/nginx/sites-available/sentinel-guard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### تحديث SSL تلقائياً

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
# يُجدَّد تلقائياً عبر cron
```

---

## 15 — مرجع سريع

### أوامر Docker Compose

```bash
# من داخل sentinel-guard/
docker compose up -d              # تشغيل في الخلفية
docker compose up --build -d      # بناء وتشغيل
docker compose down               # إيقاف وحذف containers
docker compose down -v            # إيقاف + حذف volumes (تحذير: يحذف البيانات!)
docker compose restart api worker # إعادة تشغيل خدمات محددة
docker compose logs api -f        # لوغات مباشرة
docker compose ps                 # حالة الخدمات
docker compose exec api bash      # دخول shell داخل container
```

### أوامر Alembic (من داخل container)

```bash
docker compose exec api alembic upgrade head      # تطبيق كل migrations
docker compose exec api alembic current           # الـ migration الحالي
docker compose exec api alembic history           # تاريخ migrations
docker compose exec api alembic downgrade -1      # تراجع migration واحد
```

### أوامر Docker Model Runner

```bash
docker model ls                         # قائمة النماذج
docker model pull ai/deepseek-v4-flash  # تحميل نموذج
docker model rm ai/deepseek-v4-flash    # حذف نموذج
docker model inspect ai/granite-4.0-nano # تفاصيل نموذج
```

### روابط مهمة

| الخدمة | الرابط | الوصف |
|--------|--------|-------|
| API Swagger | http://localhost:8000/docs | اختبار تفاعلي لكل endpoints |
| API Health | http://localhost:8000/health | فحص صحة الـ API |
| Web Dashboard | http://localhost:5000 | واجهة بصرية + AI |
| Model Runner | http://localhost:12434/engines/llama.cpp/v1/models | قائمة النماذج |
| PostgreSQL | localhost:5432 | sentinel / sentinel / sentinel_db |
| Redis | localhost:6379 | قاعدة بيانات Queue |

### متغيرات البيئة الأساسية

| المتغير | الملف | الوصف |
|---------|-------|-------|
| `SECRET_KEY` | sentinel-guard/.env | **مطلوب** — JWT signing key |
| `DOCKER_MODEL_RUNNER_URL` | كلا الملفين | عنوان Model Runner |
| `AI_ENABLED` | كلا الملفين | تفعيل/تعطيل AI |
| `AI_MODEL_GENERAL` | كلا الملفين | النموذج الافتراضي للـ chatbot |
| `AI_MODEL_FAST` | كلا الملفين | نموذج AutoFixer السريع |
| `AI_MODEL_DEEP` | كلا الملفين | نموذج التحليل العميق |
| `AI_MODEL_REASON` | كلا الملفين | نموذج الاستدلال (MiMo) |
| `DASHBOARD_PASSWORD` | empire/.env | كلمة سر الـ dashboard |
| `SHODAN_API_KEY` | sentinel-guard/.env | اختياري — للـ OSINT |

---

> **السيادة كاملة لك** — لا بيانات تغادر جهازك، لا API key خارجي، لا اعتماد على cloud.
