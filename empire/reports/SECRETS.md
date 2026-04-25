# 🔐 ملف الأسرار الكامل — AL_HAKIM EMPIRE
**تاريخ الإنشاء:** 2026-04-25  
**⚠️ هذا الملف سري — لا ترفعه على GitHub. أضف `.env` و `keys/` إلى `.gitignore`**

---

## 1. JWT Secret Key (للـ `sentinel-guard/.env`)

```
SECRET_KEY=nrBsHr5XD4XNmySeQmgJVHUe_vzDSiPINXstIkaFq7sMEFnhMcrzCHFHSBtljlXON2RD56u6oFbTOrAKj-fPOg
```
> مولَّد بـ `secrets.token_urlsafe(64)` — 512 بت

---

## 2. Web Dashboard Secret (للـ `empire/.env`)

```
DASHBOARD_SECRET=1gNDniY0dRQkl_E-EwSTV8vU9L937JM1eNzcbiYEGjRcB0jG_nmIEHuIEX9GLsde
DASHBOARD_PASSWORD=GlFDhjRJ46o9RnSvSrd8YQ
```

---

## 3. Guardian Core Passphrase

```
GUARDIAN_CORE_PASS=ERp_Jc6mQHwW6kFg9vpjDduxN7w
```
> تُستخدم مع `python guardian.py --create-core`

---

## 4. RSA-2048 Key Pair (لتوقيع التقارير)

**احفظ الملفين في `sentinel-guard/keys/` — لا ترفعهما على git أبداً**

### المفتاح الخاص (`sentinel-guard/keys/private.pem`)
```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCeQBwyAlRRf7lg
KYGHxfgXwBrRM6K9YuzU6pjIl+dvtS0gp0cyUDEVlN3vcBLq2XSuUi7f6raBuSVx
rjVW2f9unLT3IRee4ZB2zdZ1ZKxDN1EoJeCA/MPFb+U3pKvAIel/UBbMIbWklGNy
1X5jiHRQMBRbGjhRvH7SLcti39EqEkbr5nKXNXwjBgbLkoxyURfjePlIvGdXsFiM
OrOlYgRhY9nvThiPgEML91dyOeJhqwSUOPHoLa/jN3s3yRFReRDquDVl33JkgP8s
HCQ7SulsUJ1Ndgifh9O+v7kmYuEF65n6s4KVJN57vduwwBg7TZf7DPAnEqo/DvYE
dHZY543zAgMBAAECggEAGsOlASA7unzrkUPz0E6/IuUuo+sjvvwYKfpzVJm8Xrw5
oago9m1xn8DJuFEwIeAdR85Gd0BvFYmGt69K/iFofgCq6pECObDUigNOHhSkvcmB
RFUDn00gnyfJkJudIKWbpBibgnLBEdC28RkCgzr00QsQpkfM9qX2nP15xIMuEPs6
JL1ZDmOibx7zdR8jq/lwow8+108juUK+IN45FYFEXiJ7++f3Px60COYKActpId4E
rPBGUi0fK297T5HmXX0r5XC3npijZLt3Drw+mshFILSRiLv84eP67V8iGTzCpb1s
yO3R4s8CgMz47+eBKM0bKiIAmuqKTO9OQWBplDS54QKBgQDWI3qOdB0SnD5l9TEH
Z2vTDxHFJ7nDNRvoAvOK2eCXm94JYZY2+yM22NTv6HbJ9E8TWpDxYVeNcwGprJ6e
EjMJb9qQJJkZoeZYk0Dad2RRygE+4000Lo0lrxpJPjS2u8mIyVVT63/exIStIaah
uFOkEdTRjg0mj2Tk1o0xn7f1XwKBgQC9L7hYRYoG+uBT+JiQJjdLAgtUIK/6gZZk
z/HXr9P5ZWBB2vQi0yP5FczhfaB5xZtaMvuJG66npS2gDAP5ILRl1mfUYyyeHCbl
jZoIeKHzuEIyx1da0ZgtnTm6XG1zraFoiPtDze5qPZBag6IrNd/moAXkGLfKR+De
0EFeTMO77QKBgDrxAw/o6AOyW/6Gcdte3S/4CuUgnSIdITRIc665b/drIL+mS8mQ
cM3s+xeZ/fByvb1PBWxbZdT6Xe/NIs/RpJipYBii6j1C8ftZdNVtXYChwJwFxr9h
PNqtiue0JqBRqhRrjoAN52Fy6C4bgBktemBDxDd2CSqe95+BatXI58KzAoGANRYs
7mglASxowmdhuCFhJqUeNK8vcmXmo8dOH63xF2yBBDnCg/snfv/FDAlKfKEcpMTl
nGWuLtDE6sI0YzXwKRtu60QhAwT3TTbc4D+pglBUExeoxY1G3JXf2xGQjQNN5Z16
lF425oz78so5OVLWz0pcHNNqz1I4IY3iqel0i0kCgYEAt4wudTKFi+Ky/XXvtE+1
C0tNg6WYeIXCbsnVnQnMZ+QmtFKQ2GwheH63nzZLbGH+SxwcScp9yahn0bc1EO1O
ziG/kO0p0LkLL9dMPwg51Wt4qzrezOncblB7RubL+YcrIAeTwNaxogABO6Amz8sz
sgNWIpCpiO38xr4wKthXK2E=
-----END PRIVATE KEY-----
```

### المفتاح العام (`sentinel-guard/keys/public.pem`)
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnkAcMgJUUX+5YCmBh8X4
F8Aa0TOivWLs1OqYyJfnb7UtIKdHMlAxFZTd73AS6tl0rlIu3+q2gbklca41Vtn/
bpy09yEXnuGQds3WdWSsQzdRKCXggPzDxW/lN6SrwCHpf1AWzCG1pJRjctV+Y4h0
UDAUWxo4Ubx+0i3LYt/RKhJG6+ZylzV8IwYGy5KMclEX43j5SLxnV7BYjDqzpWIE
YWPZ704Yj4BDC/dXcjniYasElDjx6C2v4zd7N8kRUXkQ6rg1Zd9yZID/LBwkO0rp
bFCdTXYIn4fTvr+5JmLhBeuZ+rOClSTee73bsMAYO02X+wzwJxKqPw72BHR2WOeN
8wIDAQAB
-----END PUBLIC KEY-----
```

---

## 5. صيغة API Key (تُنشأ عبر الـ API)

```
sg_-Shth-b6z_8xlSWk56wDWCnU7jDGf7gwlsWkRPaucOY
```
> تُولَّد تلقائياً عند `POST /api/v1/auth/api-keys` — المثال أعلاه للتوضيح فقط

---

## 6. مفاتيح خارجية (يجب الحصول عليها يدوياً)

| المفتاح | المصدر | الاستخدام |
|---------|--------|----------|
| `SHODAN_API_KEY` | [shodan.io](https://shodan.io) → Account → API Key | فحص IPs سلبياً |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API Key | AI في الـ Dashboard والـ Bot |
| `TELEGRAM_BOT_TOKEN` | @BotFather على تيليغرام → /newbot | بوت التنبيهات |
| `AL_HAKIM_CHAT_ID` | ارسل رسالة للبوت ثم افتح: `https://api.telegram.org/bot<TOKEN>/getUpdates` | تقييد الوصول لك فقط |

---

## 7. ملف `sentinel-guard/.env` الكامل

```env
# App
APP_NAME=Sentinel Guard
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@db:5432/sentinel_db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Security ← غيّر هذا
SECRET_KEY=nrBsHr5XD4XNmySeQmgJVHUe_vzDSiPINXstIkaFq7sMEFnhMcrzCHFHSBtljlXON2RD56u6oFbTOrAKj-fPOg

# Shodan
SHODAN_API_KEY=YOUR_SHODAN_KEY_HERE

# RSA
RSA_PRIVATE_KEY_PATH=keys/private.pem
RSA_PUBLIC_KEY_PATH=keys/public.pem

# CORS (comma-separated domains أو * للـ dev)
CORS_ORIGINS=*
ALLOWED_HOSTS=*

# Rate limits
RATE_LOGIN=5/minute
RATE_REGISTER=3/minute
RATE_SCAN=10/minute
RATE_ASSETS=30/minute
RATE_DEFAULT=60/minute

# Scanning
MAX_CONCURRENT_SCANS=5
SCAN_TIMEOUT_SECONDS=300
```

---

## 8. ملف `empire/.env` الكامل

```env
# Sentinel Guard API
SENTINEL_API_URL=http://localhost:8000/api/v1
SENTINEL_EMAIL=admin@yourorg.com
SENTINEL_PASSWORD=YOUR_ADMIN_PASSWORD

# Dashboard
DASHBOARD_SECRET=1gNDniY0dRQkl_E-EwSTV8vU9L937JM1eNzcbiYEGjRcB0jG_nmIEHuIEX9GLsde
DASHBOARD_PASSWORD=GlFDhjRJ46o9RnSvSrd8YQ
DASHBOARD_PORT=5000

# Telegram Bot
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
AL_HAKIM_CHAT_ID=YOUR_TELEGRAM_ID_HERE

# Gemini AI
GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE

# Guardian
GUARDIAN_ROOT_PATH=..
```

---

## 9. خطوات نسخ المفاتيح

```bash
# 1. أنشئ مجلد المفاتيح
mkdir -p sentinel-guard/keys

# 2. احفظ المفتاح الخاص (من القسم 4 أعلاه)
nano sentinel-guard/keys/private.pem

# 3. احفظ المفتاح العام
nano sentinel-guard/keys/public.pem

# 4. اضبط الصلاحيات
chmod 600 sentinel-guard/keys/private.pem
chmod 644 sentinel-guard/keys/public.pem

# 5. أنشئ ملفات .env
cp sentinel-guard/.env.example sentinel-guard/.env
cp empire/.env.example empire/.env
# ثم عدّل القيم
```

---

## 10. التحقق من السلامة

```bash
# SHA3-256 للمشروع كاملاً (43 ملف)
# 24fecf15654d163867103a6dd6ae11a010dfe8b8f57e082c68c3842937d1ef3a
python3 -c "
import hashlib
from pathlib import Path
all_b = b''
for p in sorted(list(Path('sentinel-guard').rglob('*.py'))+list(Path('empire').rglob('*.py'))):
    all_b += p.read_bytes()
print(hashlib.sha3_256(all_b).hexdigest())
"
```

---

*👑 AL_HAKIM — لا تشارك هذا الملف مع أحد*
