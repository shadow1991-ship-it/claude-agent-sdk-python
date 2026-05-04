# فحص تطبيقات الويب الشامل — Web Application Scanning

> للاستخدام على مواقعك المملوكة أو بإذن كتابي صريح فقط.

---

## Sentinel Guard — الفحص المتكامل للمواقع

كيف تفحص موقعك بالكامل خطوة بخطوة:

### الخطوة 1: تسجيل الموقع كأصل
```bash
# سجّل موقعك أولاً
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "example.com", "asset_type": "domain", "verification_method": "dns"}'
```

### الخطوة 2: إثبات الملكية (DNS challenge)
```bash
# اجلب تعليمات التحقق
curl http://localhost:8000/api/v1/assets/UUID/challenge \
  -H "Authorization: Bearer TOKEN"

# أضف TXT record في DNS:
# _sentinel-verify.example.com → القيمة التي ظهرت

# ثم تحقق
curl -X POST http://localhost:8000/api/v1/assets/UUID/verify \
  -H "Authorization: Bearer TOKEN" \
  -d '{"asset_id": "UUID"}'
```

### الخطوة 3: الفحص الشامل
```bash
# فحص كل شيء مرة واحدة
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer TOKEN" \
  -d '{"asset_id": "UUID", "scan_type": "full"}'

# فحص headers فقط
curl -X POST http://localhost:8000/api/v1/scans \
  -d '{"asset_id": "UUID", "scan_type": "headers"}'

# فحص SSL/TLS فقط
curl -X POST http://localhost:8000/api/v1/scans \
  -d '{"asset_id": "UUID", "scan_type": "ssl"}'

# فحص المنافذ فقط
curl -X POST http://localhost:8000/api/v1/scans \
  -d '{"asset_id": "UUID", "scan_type": "ports",
       "nmap_arguments": "-sV -T4 --top-ports 1000"}'
```

### الخطوة 4: قراءة النتائج
```bash
# اجلب النتيجة
curl http://localhost:8000/api/v1/scans/SCAN_UUID \
  -H "Authorization: Bearer TOKEN"

# تصدير SARIF (GitHub Code Scanning)
curl http://localhost:8000/api/v1/scans/SCAN_UUID/sarif \
  -H "Authorization: Bearer TOKEN" > results.sarif.json

# اطلب إصلاح ثغرة بالـ AI
curl -X POST http://localhost:8000/api/v1/scans/SCAN_UUID/findings/FINDING_UUID/fix \
  -H "Authorization: Bearer TOKEN"
```

---

## ماذا يكتشف كل scanner؟

### Headers Scanner
```
✅ يكتشف:
  • Strict-Transport-Security مفقود → هجوم MITM ممكن
  • Content-Security-Policy مفقود → XSS ممكن
  • X-Frame-Options مفقود → Clickjacking ممكن
  • X-Content-Type-Options مفقود → MIME sniffing
  • Referrer-Policy مفقود → تسريب URLs
  • Permissions-Policy مفقود → وصول للـ camera/mic/location
  • Server header مكشوف → تسريب إصدار الخادم
  • X-Powered-By مكشوف → تسريب التقنية المستخدمة
```

### SSL/TLS Scanner
```
✅ يكتشف:
  • شهادة منتهية الصلاحية
  • شهادة تنتهي خلال 30 يوم (تحذير)
  • شهادة غير موثوقة
  • بروتوكول قديم: TLSv1.0, TLSv1.1 (خطر)
  • SSLv2, SSLv3 (خطر جداً)
  • Cipher ضعيف: RC4, DES, EXPORT
  • لا HSTS → HTTP downgrade ممكن
```

### Nmap Scanner (فحص المنافذ)
```
✅ يكتشف:
  • منافذ قواعد بيانات مكشوفة: 3306 (MySQL), 5432 (PG), 27017 (MongoDB)
  • Redis مكشوف: 6379 (بدون auth = كارثة)
  • Telnet مفتوح: 23 (غير مشفر)
  • FTP مفتوح: 21 (نقل بيانات بدون تشفير)
  • RDP مكشوف: 3389 (هجمات brute force شائعة)
  • NSE scripts: كشف ثغرات معروفة تلقائياً
```

### Shodan Scanner (استطلاع سلبي)
```
✅ يكتشف:
  • خدمات مكشوفة على الإنترنت
  • CVEs معروفة مرتبطة بالإصدارات
  • Banners الخدمات
  • تاريخ الاكتشافات
```

### Dockerfile Scanner
```
✅ يكتشف:
  • FROM بدون @sha256 → image ليست pinned
  • ENV PASSWORD=xxx → سر مكشوف
  • RUN curl ... | bash → تنفيذ كود عشوائي
  • ADD بدلاً من COPY → أقل أماناً
  • RUN apt بدون clean → cache متراكم
  • تحليل AI عميق للسياق
```

---

## أدوات خارجية تكمل Sentinel Guard

### curl — فحص يدوي سريع
```bash
# فحص headers موقع
curl -sI https://example.com

# تحقق من redirect HTTPS
curl -I http://example.com | grep Location

# فحص شهادة TLS
curl -v https://example.com 2>&1 | grep -E "subject|expire|SSL"

# فحص response time
curl -w "@curl-format.txt" -o /dev/null -s https://example.com
```

### openssl — تحليل TLS يدوي
```bash
# عرض تفاصيل الشهادة الكاملة
openssl s_client -connect example.com:443 </dev/null 2>/dev/null | openssl x509 -text

# تحقق من انتهاء الصلاحية
openssl s_client -connect example.com:443 </dev/null 2>/dev/null | openssl x509 -noout -dates

# فحص TLS 1.3 مدعوم أم لا
openssl s_client -connect example.com:443 -tls1_3 </dev/null 2>&1 | grep "Protocol"

# قائمة الـ ciphers المدعومة
openssl ciphers -v | grep TLSv1.3
```

### Nmap — فحص الموقع مباشرة
```bash
# فحص شامل لموقع ويب
nmap -sV -sC -p 80,443,8080,8443 example.com

# فحص ثغرات HTTP
nmap --script=http-vuln* -p 80,443 example.com

# فحص headers
nmap --script=http-headers example.com

# كشف CMS (WordPress, Joomla...)
nmap --script=http-generator,http-wordpress-enum example.com

# فحص SSL ciphers
nmap --script=ssl-enum-ciphers -p 443 example.com

# فحص Heartbleed
nmap --script=ssl-heartbleed -p 443 example.com
```

---

## قراءة نتائج الفحص — دليل تفسير الـ Severity

| المستوى | الوزن | المعنى | الأولوية |
|---------|-------|---------|---------|
| CRITICAL | 40 | ثغرة تُمكّن من الاختراق الفوري | إصلاح فوري < 24 ساعة |
| HIGH | 20 | ثغرة خطيرة قابلة للاستغلال | إصلاح < أسبوع |
| MEDIUM | 8 | ثغرة تحتاج ظروف محددة | إصلاح < شهر |
| LOW | 3 | ضعف منخفض الخطر | إصلاح في أقرب release |
| INFO | 0 | معلومة للعلم | لا يحتاج إصلاح فورياً |

---

## قائمة فحص أمان الموقع الكاملة ✅

```
الـ HTTPS:
  [ ] شهادة TLS صالحة وموثوقة
  [ ] HSTS مُفعّل (max-age > 31536000)
  [ ] TLSv1.2 و TLSv1.3 فقط (SSLv3/TLS1.0/1.1 معطلة)
  [ ] Redirect تلقائي من HTTP → HTTPS

الـ Headers:
  [ ] Content-Security-Policy
  [ ] X-Frame-Options: DENY
  [ ] X-Content-Type-Options: nosniff
  [ ] Referrer-Policy
  [ ] Permissions-Policy
  [ ] لا Server header مكشوف
  [ ] لا X-Powered-By

المنافذ:
  [ ] لا قواعد بيانات مكشوفة على الإنترنت
  [ ] لا Redis مكشوف
  [ ] لا Telnet مفتوح
  [ ] SSH على port غير 22 (اختياري للأمان الإضافي)

الكود:
  [ ] لا أسرار في git history
  [ ] .env لا يُرفع على GitHub
  [ ] Dependencies محدثة (pip-audit, npm audit)
  [ ] Dockerfile images مع @sha256

الـ API:
  [ ] Rate limiting مُفعّل
  [ ] JWT tokens تنتهي صلاحيتها
  [ ] CORS مقيّد للـ origins المعروفة
  [ ] Input validation على كل endpoint
```

---

## سيناريوهات الفحص الشائعة

### فحص بعد نشر جديد (Pre-production check)
```json
{ "scan_type": "headers" }    // 30 ثانية
{ "scan_type": "ssl" }        // دقيقة
```

### فحص أسبوعي شامل
```json
{ "scan_type": "full" }       // 5-10 دقائق
```

### فحص Dockerfile قبل النشر
```json
{
  "scan_type": "dockerfile",
  "dockerfile_url": "https://raw.githubusercontent.com/user/repo/main/Dockerfile"
}
```

### فحص ثغرات CVE في dependencies
```json
{ "scan_type": "sbom", "image_ref": "myapp:latest" }
```
