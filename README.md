# Sentinel Guard — منصة الأمن التكتيكي

نظام فحص أمني احترافي مدعوم بالذكاء الاصطناعي المحلي.  
كل فحص يعمل **فقط** على أصول موثّقة الملكية — لا يمكن فحص أي نطاق بدون إثبات الملكية.

```
──────────────────────────────────────────────────────────
  ⬡  SENTINEL GUARD  ·  AI-POWERED  ·  SOVEREIGN  ·  FREE
──────────────────────────────────────────────────────────
  Backend  : FastAPI + PostgreSQL + Celery
  AI Core  : DeepSeek-V4 · MiMo-V2.5-Pro · Granite Nano
  Dashboard: Flask · SSE · Thinking Modes · Model Selector
  License  : MIT  ·  No API Key  ·  100% Local
──────────────────────────────────────────────────────────
```

---

## هيكل المشروع الكامل

```
sentinel-guard/                ← Backend API الأساسي
  app/
    api/v1/                    ← Auth · Assets · Scans · Reports
    core/                      ← Config · Database · Security
    models/                    ← User · Org · Asset · Scan · Report
    schemas/                   ← Pydantic validation
    services/
      scanner/
        nmap_scanner.py        ← فحص المنافذ والخدمات
        ssl_scanner.py         ← TLS/SSL + Cipher analysis
        headers_scanner.py     ← HTTP Security Headers
        shodan_scanner.py      ← OSINT سلبي
        dockerfile_scanner.py  ← Rule-based + AI analysis
        sbom_scanner.py        ← Software Bill of Materials
        ai_scanner.py          ← ModelRouter — توجيه المهام للنماذج
        auto_fixer.py          ← توليد كود الإصلاح بالذكاء
        orchestrator.py        ← تنسيق جميع الـ scanners
      verification/            ← DNS · HTTP · WHOIS ownership
      reporter/                ← تقارير RSA-2048 موقّعة
    workers/                   ← Celery background tasks
  docker-compose.yml
  requirements.txt

empire/
  sentinel_client.py           ← HTTP client للـ API
  track.sh                     ← Live terminal tracker (bash)
  .env.example

web_dashboard.py               ← Dashboard كامل (Flask)
  ├── AI chatbot               ← DeepSeek-V4 + Thinking Modes
  ├── Model Selector           ← V4-Flash · V4-Pro · Granite · MiMo
  ├── Think Block UI           ← عرض تفكير النموذج قابل للطي
  ├── Dockerfile Scanner       ← فحص مباشر من الـ dashboard
  └── SSE notifications        ← تحديثات real-time

knowledge/kali-tools/          ← قاعدة معرفة أمنية (12 ملف)
  00-INDEX.md                  ← فهرس
  01-recon.md                  ← استطلاع
  02-scanning.md               ← فحص الشبكات
  03-web-security.md           ← أمن الويب + OWASP
  04-crypto-passwords.md       ← تشفير وكلمات المرور
  05-docker-security.md        ← أمن Docker
  06-network-analysis.md       ← تحليل الشبكات
  07-pentest-frameworks.md     ← أطر اختبار الاختراق
  08-offensive-tools.md        ← أدوات هجومية
  09-ai-core-setup.md          ← إعداد الـ AI المحلي
  10-security-libraries.md     ← CVE DBs · OWASP · SecLists
  11-credential-analysis.md    ← Hash · Gerrit · Hashcat
  12-ai-models-guide.md        ← DeepSeek-V4 · MiMo · Granite

AI-Dev-Toolkit/                ← طقم أدوات AI متعدد النماذج
  docker-compose.yaml          ← تشغيل 5 نماذج بأمر واحد
  Scripts/test_models.py       ← اختبار الاستجابة + latency
  lambda/
    Dockerfile                 ← AWS Lambda container image
    scanner_handler.py         ← Lambda handler → Sentinel API
  Docs/
    DeepSeek_V4_Specs.md       ← معمارية V4 · tokens · thinking modes
    MiMo_V2_5_Pro_Specs.md     ← Xiaomi 7B reasoning model
    Granite_Specs.md           ← IBM Granite 4.0 Nano
    Kimi_K2_Specs.md           ← Kimi K2.6 MoE

.github/workflows/
  sentinel-scan.yml            ← CI: فحص Dockerfiles تلقائياً
```

---

## متطلبات التشغيل

| الأداة | الإصدار | التحقق |
|--------|---------|--------|
| Docker Desktop | 4.40+ | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |
| Python | 3.11+ | `python3 --version` |
| Docker Model Runner | مُفعَّل في Docker Desktop | `docker model ls` |

---

## الخطوة 1 — تحميل المشروع

```bash
git clone https://github.com/shadow1991-ship-it/claude-agent-sdk-python.git
cd claude-agent-sdk-python
```

---

## الخطوة 2 — تفعيل Docker Model Runner

في Docker Desktop:
```
Settings → Features in Development → Docker Model Runner → Enable
```

ثم تحميل النماذج:

```bash
# أساسي — Dashboard chatbot (سياق 1M token)
docker model pull ai/deepseek-v4-flash

# اختياري — تحليل أمني عميق
docker model pull ai/deepseek-v4-pro

# اختياري — AutoFixer سريع جداً
docker model pull ai/granite-4.0-nano

# اختياري — استدلال رياضي/منطقي (7B فقط)
docker model pull ai/mimo-v2.5-pro

# التحقق من التشغيل
curl http://localhost:12434/engines/llama.cpp/v1/models
```

---

## الخطوة 3 — إعداد sentinel-guard Backend

```bash
cd sentinel-guard
cp .env.example .env
```

عدّل `.env`:

```env
# مطلوب — ولّد مفتاح عشوائي
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# اختياري
SHODAN_API_KEY=your_key_here

# AI — Docker Model Runner
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_ENABLED=true
AI_MODEL_FAST=ai/granite-4.0-nano
AI_MODEL_DEEP=ai/deepseek-v4-pro
AI_MODEL_REASON=ai/mimo-v2.5-pro
AI_MODEL_GENERAL=ai/deepseek-v4-flash
AI_TIMEOUT=60

DEBUG=false
```

---

## الخطوة 4 — تشغيل الـ Backend

```bash
# داخل sentinel-guard/
docker compose up --build -d

# تهيئة قاعدة البيانات (مرة واحدة)
docker compose exec api alembic upgrade head
```

**التحقق:**

```bash
docker compose ps
# المتوقع: api + worker + db + redis كلها Up

curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}
```

Swagger UI: `http://localhost:8000/docs`

---

## الخطوة 5 — تشغيل Web Dashboard

```bash
cd empire
cp .env.example .env
```

عدّل `empire/.env`:

```env
SENTINEL_API_URL=http://localhost:8000/api/v1
DASHBOARD_SECRET=<مفتاح_عشوائي_طويل>
DASHBOARD_PASSWORD=كلمة_سرك_هنا

# AI
DOCKER_MODEL_RUNNER_URL=http://localhost:12434/engines/llama.cpp/v1
AI_MODEL_GENERAL=ai/deepseek-v4-flash
AI_MODEL_DEEP=ai/deepseek-v4-pro
AI_MODEL_FAST=ai/granite-4.0-nano
AI_MODEL_REASON=ai/mimo-v2.5-pro
```

```bash
cd ..
pip install flask openai
python web_dashboard.py
```

افتح: `http://localhost:5000`

---

## ميزات الـ Dashboard

### اختيار النموذج

| الخيار | النموذج | الاستخدام |
|--------|---------|-----------|
| ⚡ V4-Flash (1M) | DeepSeek-V4-Flash | chatbot عام، سياق مليون token |
| 🧠 V4-Pro (Deep) | DeepSeek-V4-Pro | تحليل أمني عميق، CVE reasoning |
| 🔧 Granite (Fix) | IBM Granite 4.0 Nano | AutoFixer، code generation |
| 🔬 MiMo (Reason) | Xiaomi MiMo-V2.5-Pro | استدلال منطقي، تحليل متعدد الخطوات |
| 💾 V3 (Fallback) | DeepSeek-V3 | fallback إذا V4 غير متاح |

### أوضاع التفكير — Thinking Modes

| الوضع | السرعة | الاستخدام |
|-------|--------|-----------|
| **OFF** (Non-think) | ⚡ فوري | أسئلة بسيطة، مهام روتينية |
| **HIGH** (Think High) | ⚡⚡ | `<think>تحليل منطقي</think>` الجواب |
| **MAX ★** (Think Max) | ⚡⚡⚡ | أصعب المسائل، استدلال متعدد الخطوات |

عند وضع HIGH أو MAX، يعرض الـ dashboard **مربع `💭 تفكير` قابل للطي** يُظهر ما فكّر فيه النموذج قبل الجواب.

### قاعدة المعرفة المدمجة

الـ AI يعرف تلقائياً كل محتوى `knowledge/kali-tools/` — 12 ملف يشمل:
- أدوات Kali Linux الكاملة (Nmap، Burp، Metasploit، Hashcat…)
- OWASP Top 10، أمن Docker، تحليل الـ Hash
- دليل نماذج AI المحلية (DeepSeek-V4 · MiMo · Granite)

---

## الخطوة 6 — أول استخدام (API)

```bash
# 1. تسجيل حساب
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@myorg.com","password":"Pass123!","organization_name":"My Org"}'

# 2. تسجيل الدخول
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@myorg.com","password":"Pass123!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. إضافة أصل
ASSET_ID=$(curl -s -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"example.com","asset_type":"domain","verification_method":"dns_txt"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. التحقق من الملكية (احصل على تعليمات الـ DNS record)
curl -s http://localhost:8000/api/v1/assets/$ASSET_ID/challenge \
  -H "Authorization: Bearer $TOKEN"

# بعد إضافة الـ TXT record في DNS:
curl -s -X POST http://localhost:8000/api/v1/assets/$ASSET_ID/verify \
  -H "Authorization: Bearer $TOKEN"
```

> **لماذا التحقق ضروري؟** يمنع استخدام النظام لمهاجمة أصول الآخرين.

---

## الخطوة 7 — تشغيل الفحوصات

```bash
# فحص كامل
SCAN_ID=$(curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"asset_id\":\"$ASSET_ID\",\"scan_type\":\"full\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# فحص Dockerfile
curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"asset_id\":\"$ASSET_ID\",
    \"scan_type\":\"dockerfile\",
    \"dockerfile_url\":\"https://raw.githubusercontent.com/your/repo/main/Dockerfile\"
  }"

# متابعة الحالة
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### أنواع الفحص

| النوع | ما يفحصه | الوقت |
|-------|---------|-------|
| `full` | كل شيء | 2-5 دق |
| `ports` | Nmap — منافذ وخدمات | 1-3 دق |
| `ssl` | TLS · Ciphers · Certificate | 30 ث |
| `headers` | HTTP Security Headers | 10 ث |
| `shodan` | OSINT سلبي | 10 ث |
| `dockerfile` | Rules + DeepSeek AI | 30-60 ث |
| `sbom` | Bill of Materials + CVEs | 1-2 دق |

---

## الخطوة 8 — AutoFixer (إصلاح بالذكاء)

```bash
# عرض الـ findings
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
for f in json.load(sys.stdin).get('findings',[]):
    print(f['id'], f['severity'], f['title'])
"

# توليد كود الإصلاح (Granite Nano — < 2 ثانية)
curl -s -X POST \
  http://localhost:8000/api/v1/scans/$SCAN_ID/findings/$FINDING_ID/fix \
  -H "Authorization: Bearer $TOKEN"
```

الرد:
```json
{
  "fix_code": "HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/health",
  "fix_language": "dockerfile",
  "fix_description": "Add health check to enable container orchestration"
}
```

---

## الخطوة 9 — تصدير SARIF (GitHub Code Scanning)

```bash
# تصدير النتائج بتنسيق SARIF 2.1.0
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID/sarif \
  -H "Authorization: Bearer $TOKEN" -o results.sarif

# رفع على GitHub (يظهر في Security tab)
gh api repos/OWNER/REPO/code-scanning/sarifs \
  --field commit_sha=$(git rev-parse HEAD) \
  --field ref=refs/heads/main \
  --field sarif=@results.sarif
```

أو عبر GitHub Actions (`.github/workflows/sentinel-scan.yml`) — يعمل تلقائياً على كل push.

---

## الخطوة 10 — تقارير موقّعة

```bash
# توليد تقرير RSA-2048
REPORT_ID=$(curl -s -X POST \
  http://localhost:8000/api/v1/reports/generate/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# التحقق من التوقيع
curl -s http://localhost:8000/api/v1/reports/$REPORT_ID/verify \
  -H "Authorization: Bearer $TOKEN"
```

---

## AI-Dev-Toolkit — تشغيل متعدد النماذج

```bash
# تشغيل 5 نماذج محلية دفعة واحدة
cd AI-Dev-Toolkit
docker compose up -d

# اختبار الاستجابة من كل نموذج
python3 Scripts/test_models.py
# ✅ granite-4.0-nano  |  1.2s  | GRANITE_OK
# ✅ kimi-k2           | 18.4s  | KIMI_OK
# ✅ deepseek-v4-flash |  4.1s  | DEEPSEEK_OK

# اختبار Lambda محلياً (اختياري)
cd lambda
docker build -t sentinel-lambda .
docker run -p 9000:8080 sentinel-lambda
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"scan_type":"dockerfile","target":"https://raw.github.com/.../Dockerfile"}'
```

---

## نماذج AI المدعومة

| النموذج | المطوّر | الحجم | السياق | الاستخدام |
|---------|---------|-------|--------|-----------|
| `ai/deepseek-v4-flash` | DeepSeek | 284B (13B active) | **1M token** | Dashboard chatbot |
| `ai/deepseek-v4-pro` | DeepSeek | 1.6T (49B active) | **1M token** | تحليل أمني عميق |
| `ai/granite-4.0-nano` | IBM | ~4B | 128K | AutoFixer — < 2ث |
| `ai/mimo-v2.5-pro` | Xiaomi | 7B | 32K | استدلال منطقي |
| `ai/kimi-k2` | Moonshot | ~1T MoE | 128K | Dockerfile analysis |
| `ai/deepseek-v3-0324` | DeepSeek | 671B (37B active) | 64K | Fallback عام |

**كلها مجانية — لا API key — لا إنترنت — تعمل على جهازك.**

---

## جدول الخدمات

| الخدمة | الرابط | الوصف |
|--------|--------|-------|
| API Swagger | `localhost:8000/docs` | اختبار جميع الـ endpoints |
| Web Dashboard | `localhost:5000` | واجهة بصرية + AI chatbot |
| Docker Model Runner | `localhost:12434` | نماذج AI محلية |
| PostgreSQL | `localhost:5432` | قاعدة البيانات |
| Redis | `localhost:6379` | Message broker |

---

## حل المشاكل الشائعة

| المشكلة | السبب | الحل |
|---------|-------|------|
| `docker model ls` يُعطي خطأ | Model Runner غير مُفعَّل | Docker Desktop → Settings → Features |
| API لا يبدأ | `SECRET_KEY` فارغ | أضف مفتاحاً عشوائياً في `.env` |
| الفحص يبقى `queued` | Redis غير متصل | `docker compose restart redis worker` |
| AI لا يستجيب | النموذج غير محمَّل | `docker model pull ai/deepseek-v4-flash` |
| `alembic: not found` | تنفيذ خارج الـ container | `docker compose exec api alembic upgrade head` |

```bash
# لوغات مباشرة
docker compose logs api -f
docker compose logs worker -f

# إعادة تشغيل كاملة
docker compose down && docker compose up -d
docker compose exec api alembic upgrade head
```

---

## إنتاج (Production Checklist)

```bash
# 1. ملفات .env خارج git
cat .gitignore | grep '\.env'

# 2. SECRET_KEY قوي (80+ حرف)
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# 3. DEBUG=false في sentinel-guard/.env
grep DEBUG sentinel-guard/.env

# 4. HTTPS عبر Nginx
# ssl_certificate + proxy_pass http://127.0.0.1:8000
```

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
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

## قواعد السيادة — لا استثناء

```
✅ فحص أصولك فقط (domains + IPs تملكها)
✅ CTF: HackTheBox · TryHackMe · VulnHub
✅ بيئات اختبار معزولة (Docker · VM)
✅ AI يعمل محلياً — بياناتك لا تغادر جهازك
❌ ممنوع --privileged | ممنوع --net=host على الإنتاج
❌ ممنوع فحص أصول الغير بدون إذن خطي
❌ الذكاء لا يُنفّذ إلا بأمرك الصريح
```
