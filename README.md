# Sentinel Guard — دليل التشغيل الكامل

نظام فحص أمني احترافي مبني على FastAPI + PostgreSQL + Celery + AI محلي (Docker Model Runner).  
كل فحص يعمل فقط على أصول موثّقة الملكية — لا يمكن فحص أي موقع بدون إثبات ملكيته.

---

## هيكل المشروع

```
sentinel-guard/          ← الـ API الأساسي (FastAPI)
  app/
    api/v1/              ← endpoints: auth, assets, scans, reports
    core/                ← config, database, security
    models/              ← SQLAlchemy: User, Org, Asset, Scan, Report
    schemas/             ← Pydantic validation
    services/
      scanner/           ← 9 scanners: nmap, ssl, headers, shodan, dockerfile, sbom, ai, auto_fixer
      verification/      ← DNS / HTTP / WHOIS ownership verification
      reporter/          ← RSA-2048 signed reports
    workers/             ← Celery background tasks
  docker-compose.yml
  requirements.txt
  .env.example

empire/
  sentinel_client.py     ← HTTP client للـ API
  track.sh               ← live terminal dashboard
  .env.example

web_dashboard.py         ← واجهة الويب (Flask + DeepSeek V4 Flash AI)
.github/workflows/
  sentinel-scan.yml      ← CI: فحص Dockerfiles تلقائياً على كل push
```

---

## المتطلبات

| الأداة | الإصدار الأدنى | التحقق |
|--------|---------------|--------|
| Docker Desktop | 4.40+ | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |
| Python | 3.11+ | `python3 --version` |

---

## الخطوة 1 — تنزيل المشروع

```bash
git clone https://github.com/ass1010/claude-agent-sdk-python.git
cd claude-agent-sdk-python
```

---

## الخطوة 2 — إعداد sentinel-guard

### 2.1 نسخ ملف البيئة

```bash
cd sentinel-guard
cp .env.example .env
```

### 2.2 توليد SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

افتح `.env` وضع الناتج في `SECRET_KEY`:

```env
SECRET_KEY=الناتج_هنا
SHODAN_API_KEY=your_key_here    # اختياري — من shodan.io مجاناً
DEBUG=false
```

> لا تعدّل `DATABASE_URL` أو `REDIS_URL` — القيم الافتراضية تعمل مع docker-compose.

---

## الخطوة 3 — تشغيل الـ Backend

```bash
# داخل sentinel-guard/
docker compose up --build -d
```

**ما الذي يبدأ:**

| الخدمة | الدور |
|--------|-------|
| `db` | PostgreSQL 16 — يحفظ المستخدمين، الأصول، الفحوصات، النتائج |
| `redis` | Message broker بين الـ API والـ worker |
| `api` | FastAPI على المنفذ 8000 — يستقبل الطلبات |
| `worker` | Celery — يشغّل الفحوصات في الخلفية |

### تحقق من الحالة

```bash
docker compose ps
```

المتوقع:
```
NAME                    STATUS
sentinel-guard-api-1    Up
sentinel-guard-worker-1 Up
sentinel-guard-db-1     Up (healthy)
sentinel-guard-redis-1  Up (healthy)
```

إذا كان container بحالة `Exit`:
```bash
docker compose logs api --tail=40
docker compose logs worker --tail=40
```

---

## الخطوة 4 — تهيئة قاعدة البيانات

```bash
docker compose exec api alembic upgrade head
```

ينشئ الجداول: `users`, `organizations`, `assets`, `scans`, `scan_findings`, `reports`.

> يُنفَّذ مرة واحدة فقط عند أول تشغيل، أو بعد أي تعديل على الـ models.

---

## الخطوة 5 — التحقق من الـ API

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}
```

Swagger UI:
```
http://localhost:8000/docs
```

---

## الخطوة 6 — إعداد نماذج AI (Docker Model Runner)

### 6.1 تحقق أن Model Runner يعمل

```bash
docker model ls
```

إذا ظهر خطأ `unknown command`:
- Mac/Windows: تأكد أن Docker Desktop 4.40+ شغّال
- فعّله من: Settings → Features in development → Enable Docker Model Runner

### 6.2 حمّل النماذج

```bash
# للـ chatbot والـ dashboard (~8GB) — أساسي
docker model pull ai/deepseek-v4-flash

# للتحليل الأمني العميق (~15GB) — اختياري
docker model pull ai/deepseek-v4-pro

# للـ AutoFixer وتوليد الكود (~2GB) — سريع جداً
docker model pull ai/granite-4.0-nano
```

### 6.3 أضف متغيرات AI إلى `sentinel-guard/.env`

```env
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_ENABLED=true
AI_MODEL_FAST=ai/granite-4.0-nano
AI_MODEL_DEEP=ai/deepseek-v4-pro
AI_MODEL_GENERAL=ai/deepseek-v4-flash
AI_TIMEOUT=60
```

أعد تشغيل الـ containers:
```bash
docker compose down && docker compose up -d
```

---

## الخطوة 7 — إعداد Web Dashboard

```bash
cd ../empire
cp .env.example .env
```

عدّل `empire/.env`:
```env
SENTINEL_API_URL=http://localhost:8000/api/v1
DASHBOARD_SECRET=<python3 -c "import secrets; print(secrets.token_urlsafe(48))">
DASHBOARD_PASSWORD=كلمة_سرك_هنا
DASHBOARD_PORT=5000
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_MODEL_GENERAL=ai/deepseek-v4-flash
```

```bash
cd ..
pip install flask openai
python web_dashboard.py
```

افتح: `http://localhost:5000`

---

## الخطوة 8 — أول استخدام

### إنشاء حساب

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourorg.com",
    "password": "StrongPass123!",
    "organization_name": "My Org"
  }' | python3 -m json.tool
```

### تسجيل الدخول

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourorg.com","password":"StrongPass123!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

### إضافة أصل

```bash
ASSET_ID=$(curl -s -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "example.com",
    "asset_type": "domain",
    "verification_method": "dns_txt"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Asset ID: $ASSET_ID"
```

### التحقق من الملكية

```bash
# احصل على تعليمات التحقق
curl -s http://localhost:8000/api/v1/assets/$ASSET_ID/challenge \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# أضف الـ TXT record في DNS حسب التعليمات
# انتظر 5-60 دقيقة للانتشار، ثم:

curl -s -X POST http://localhost:8000/api/v1/assets/$ASSET_ID/verify \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

> **لماذا التحقق ضروري؟** النظام يرفض فحص أي أصل لم تُثبت ملكيته — حماية من استخدامه لمهاجمة مواقع الآخرين.

---

## الخطوة 9 — تشغيل الفحوصات

### فحص كامل

```bash
SCAN_ID=$(curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"asset_id\":\"$ASSET_ID\",\"scan_type\":\"full\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Scan ID: $SCAN_ID"
```

### فحص Dockerfile

```bash
curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"asset_id\":\"$ASSET_ID\",
    \"scan_type\":\"dockerfile\",
    \"dockerfile_url\":\"https://raw.githubusercontent.com/your/repo/main/Dockerfile\"
  }" | python3 -m json.tool
```

### متابعة حالة الفحص

```bash
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

انتظر حتى يصبح `"status": "completed"`.

### أنواع الفحص المتاحة

| النوع | ما يفحصه | الوقت التقريبي |
|-------|---------|---------------|
| `full` | كل شيء: ports + ssl + headers + shodan + AI | 2-5 دقائق |
| `ports` | Nmap — المنافذ المفتوحة والخدمات | 1-3 دقائق |
| `ssl` | شهادة TLS: صلاحية، ciphers، protocols | 30 ثانية |
| `headers` | HTTP security headers المفقودة | 10 ثوانٍ |
| `shodan` | بيانات Shodan السلبية | 10 ثوانٍ |
| `dockerfile` | ثغرات Dockerfile: rule-based + DeepSeek AI | 30-60 ثانية |
| `sbom` | Software Bill of Materials + CVE analysis | 1-2 دقيقة |

---

## الخطوة 10 — إصلاح تلقائي بالـ AI

```bash
# استخرج finding_id من نتيجة الفحص أولاً
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
for f in d.get('findings',[]):
    print(f['id'], '-', f['severity'], '-', f['title'])
"

# ثم شغّل AutoFixer على finding محدد
curl -s -X POST \
  http://localhost:8000/api/v1/scans/$SCAN_ID/findings/$FINDING_ID/fix \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

الرد:
```json
{
  "fix_code": "FROM ubuntu:22.04@sha256:abc123...",
  "fix_language": "dockerfile",
  "fix_description": "Pin image to digest to prevent supply chain attacks"
}
```

---

## الخطوة 11 — تصدير SARIF (GitHub Code Scanning)

```bash
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID/sarif \
  -H "Authorization: Bearer $TOKEN" \
  -o results.sarif

# ارفعه على GitHub
gh api repos/OWNER/REPO/code-scanning/sarifs \
  --field commit_sha=$(git rev-parse HEAD) \
  --field ref=refs/heads/main \
  --field sarif=@results.sarif
```

---

## الخطوة 12 — تقارير موقّعة

```bash
# توليد تقرير
REPORT_ID=$(curl -s -X POST \
  http://localhost:8000/api/v1/reports/generate/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# التحقق من التوقيع
curl -s http://localhost:8000/api/v1/reports/$REPORT_ID/verify \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

التقارير موقّعة بـ RSA-2048/PSS — يمكن التحقق منها offline في أي وقت.

---

## الخطوة 13 — Live Terminal Tracker

```bash
cd empire
chmod +x track.sh
./track.sh http://localhost:8000/api/v1 $TOKEN
```

```
  🛡️  Sentinel Guard Tracker  —  14:32:07
  ─────────────────────────────────────────
  Total Scans:       12
  Running:           1
  Critical:          3
  Avg Risk:          42.5 / 100
  Risk: ████████░░░░░░░░░░░░ 42.5/100
```

---

## الإنتاج (Production Checklist)

### ✅ قبل النشر

```bash
# 1. تأكد أن .env ليس في git
git status | grep '\.env'
# يجب أن لا يظهر شيء

# 2. SECRET_KEY قوي (80+ حرف)
python3 -c "import secrets; print(len(secrets.token_urlsafe(64)))"

# 3. DEBUG=false
grep DEBUG sentinel-guard/.env

# 4. CORS محدود لدومينك فقط
# CORS_ORIGINS=https://yourdomain.com
# ALLOWED_HOSTS=yourdomain.com
```

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300;
    }
}
```

---

## جدول الخدمات

| الخدمة | الرابط | الوصف |
|--------|--------|-------|
| API Swagger | `localhost:8000/docs` | اختبار جميع الـ endpoints |
| Web Dashboard | `localhost:5000` | واجهة بصرية + AI chatbot |
| Docker Model Runner | `localhost:12434` | نماذج AI محلية |
| PostgreSQL | `localhost:5432` | قاعدة البيانات |
| Redis | `localhost:6379` | message broker |

---

## حل المشاكل الشائعة

| المشكلة | السبب | الحل |
|---------|-------|------|
| API لا يبدأ | `SECRET_KEY` فارغ | أضف مفتاح عشوائي في `.env` |
| DB لا تتصل | المنفذ 5432 مستخدم | غيّر port في docker-compose.yml |
| AI لا يستجيب | Model Runner لا يعمل | تحقق من Docker Desktop settings |
| الفحص يبقى `queued` | Redis غير متصل | `docker compose restart redis worker` |
| `alembic: not found` | تنفيذ خارج الـ container | استخدم `docker compose exec api alembic ...` |

```bash
# لوغات مباشرة
docker compose logs api -f
docker compose logs worker -f

# إعادة تشغيل كاملة
docker compose down && docker compose up -d
docker compose exec api alembic upgrade head
```

---

## نماذج AI (Docker Model Runner — كلها محلية ومجانية)

| النموذج | الحجم | الاستخدام |
|---------|-------|----------|
| `ai/deepseek-v4-flash` | ~8GB | Dashboard chatbot، SSE streaming |
| `ai/deepseek-v4-pro` | ~15GB | تحليل Dockerfile عميق، CVE reasoning |
| `ai/granite-4.0-nano` | ~2GB | AutoFixer، code generation سريع |

لا إنترنت، لا API key، لا تكلفة — كل شيء يعمل على جهازك.
