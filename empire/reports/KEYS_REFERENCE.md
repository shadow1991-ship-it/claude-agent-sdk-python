# 🔑 مرجع المفاتيح والإعدادات — Sentinel Guard
**تاريخ الإنشاء:** 2026-04-25  
**المالك:** AL_HAKIM

---

## المفاتيح المطلوبة

### 1. JWT SECRET_KEY (للـ `sentinel-guard/.env`)
احصل عليه بتشغيل:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```
**مثال على الناتج:**
```
vKINRDmhsZnqbsKveTI5LwYHyxS7Sig0HAtpG-Mb9eycL1a8fp16CnK6Nr4vyREHuifvAgjFqn08WO7GHgL-xw
```
> ⚠️ هذا المثال فقط — أنشئ مفتاحك الخاص ولا تستخدم هذا

---

### 2. صيغة API Key (تُنشأ عبر API)
```
POST /api/v1/auth/api-keys
Authorization: Bearer <access_token>
{"name": "my-key", "expires_days": 30}
```
**الناتج:**
```
sg_<random_48_chars>
```
مثال: `sg_t9K3xFcWw5Fhqfl4hKXV6IMcXMPK1rjstnIeWhCb4OA`

---

### 3. RSA Key Pair (للتوقيع على التقارير)
تُنشأ تلقائياً عند أول تشغيل في `sentinel-guard/keys/`
أو يدوياً:
```bash
mkdir -p sentinel-guard/keys
openssl genrsa -out sentinel-guard/keys/private.pem 2048
openssl rsa -in sentinel-guard/keys/private.pem -pubout -out sentinel-guard/keys/public.pem
```

---

### 4. مفاتيح خارجية (تحتاج تسجيل)

| المفتاح | المصدر | الاستخدام |
|---------|--------|----------|
| `SHODAN_API_KEY` | https://shodan.io | الاستطلاع السلبي للـ IPs |
| `GEMINI_API_KEY` | https://aistudio.google.com | الذكاء الاصطناعي في الـ Bot والـ Dashboard |
| `TELEGRAM_BOT_TOKEN` | @BotFather على تيليغرام | بوت التنبيهات |

---

## بصمة المشروع (للتحقق من السلامة)

```
SHA3-256: 24fecf15654d163867103a6dd6ae11a010dfe8b8f57e082c68c3842937d1ef3a
SHA3-512: 1572a1122d0bdba920441df7fd6f1beed2b99968e4336461d48ffac0692b4aeec3411d20433b796d9ae6026c49eb89a2983d83331049245b2de62e4f5c748590
الملفات:  43 ملف
التاريخ:  2026-04-25T18:09:42Z
```

للتحقق من أي ملف:
```bash
python3 -c "
import hashlib
print(hashlib.sha3_256(open('sentinel-guard/app/main.py','rb').read()).hexdigest())
"
```

---

## ترتيب الإعداد (خطوة بخطوة)

```bash
# 1. انسخ ملفات الإعداد
cp sentinel-guard/.env.example sentinel-guard/.env
cp empire/.env.example empire/.env

# 2. عدّل المفاتيح في الملفين

# 3. شغّل Sentinel Guard
cd sentinel-guard && docker compose up --build -d

# 4. شغّل Dashboard
cd empire && pip install flask google-generativeai httpx
python web_dashboard.py

# 5. شغّل Bot
python al_hakim_bot.py
```
