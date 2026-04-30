# أمن تطبيقات الويب — Web Application Security

> للاستخدام على مواقعك المملوكة أو بإذن كتابي صريح.

---

## Nikto — فاحص المواقع

يكتشف: ملفات حساسة، إصدارات قديمة، headers مفقودة، مشاكل SSL.

```bash
nikto -h https://example.com
nikto -h https://example.com -ssl
nikto -h https://example.com -o results.html -Format html
```

**ما يكشفه:**
- ملفات مكشوفة: `/admin`, `/backup`, `/.git`, `/.env`
- headers أمنية مفقودة (CSP, HSTS, X-Frame-Options)
- إصدارات قديمة من الخوادم
- مشاكل في شهادات TLS

---

## Gobuster — اكتشاف الملفات والمجلدات

```bash
# بحث في المسارات
gobuster dir -u https://example.com -w /usr/share/wordlists/dirb/common.txt

# بحث في Subdomains
gobuster dns -d example.com -w /usr/share/wordlists/subdomains.txt

# بحث بامتدادات محددة
gobuster dir -u https://example.com -w common.txt -x php,asp,html,txt

# مع headers مخصصة
gobuster dir -u https://example.com -w common.txt -H "Authorization: Bearer TOKEN"
```

---

## Curl — اختبار HTTP يدوي

```bash
# فحص headers
curl -I https://example.com

# طلب مع headers
curl -H "User-Agent: Mozilla/5.0" https://example.com

# POST request
curl -X POST -d '{"key":"value"}' -H "Content-Type: application/json" https://api.example.com

# فحص redirect
curl -L -v https://example.com 2>&1 | grep "< HTTP"

# تحقق من شهادة TLS
curl --cacert cert.pem https://example.com
```

---

## Security Headers — الفحص اليدوي

```bash
# فحص كل الـ security headers مرة واحدة
curl -sI https://example.com | grep -iE "strict-transport|content-security|x-frame|x-content-type|referrer-policy|permissions-policy"
```

**Headers المطلوبة:**
| Header | القيمة المثالية |
|--------|----------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `Content-Security-Policy` | `default-src 'self'` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

---

## OWASP Top 10 — الثغرات الأكثر شيوعاً (2024)

| # | الثغرة | كيف تكتشفها |
|---|--------|------------|
| A01 | Broken Access Control | تجرب `/admin`, `/user/1`, `/user/2` |
| A02 | Cryptographic Failures | فحص TLS + headers |
| A03 | Injection (SQL/XSS) | إدخال `'` و `<script>` في الحقول |
| A04 | Insecure Design | مراجعة المنطق البرمجي |
| A05 | Security Misconfiguration | Nikto + headers فحص |
| A06 | Vulnerable Components | `npm audit`, `pip-audit`, Syft |
| A07 | Auth Failures | اختبار كلمات سر ضعيفة |
| A08 | Software Integrity Failures | فحص SBOM + signatures |
| A09 | Logging Failures | مراجعة logs |
| A10 | SSRF | إدخال `http://localhost` في URL fields |

---

## WhatWeb — بصمة الموقع

```bash
whatweb https://example.com
whatweb -v https://example.com        # تفاصيل أكثر
whatweb -a 3 https://example.com      # aggressive mode
```

**يكشف:** CMS، إطار العمل، إصدار الخادم، JavaScript libraries.

---

## SSL Labs / SSLyze — تحليل TLS

```bash
# sslyze (محلي)
sslyze example.com
sslyze --regular example.com

# فحص شهادة فقط
sslyze --certinfo example.com

# فحص protocols
sslyze --sslv2 --sslv3 --tlsv1 example.com
```

**ما تبحث عنه:**
- ❌ SSLv2, SSLv3, TLSv1.0, TLSv1.1 — يجب أن تكون معطلة
- ✅ TLSv1.2, TLSv1.3 — المقبولة
- ❌ EXPORT ciphers, NULL ciphers, RC4 — خطيرة
- ✅ ECDHE, AES-GCM — آمنة

---

## تكامل مع Sentinel Guard

```json
{ "asset_id": "uuid", "scan_type": "headers" }   // فحص headers
{ "asset_id": "uuid", "scan_type": "ssl" }        // فحص TLS
{ "asset_id": "uuid", "scan_type": "full" }       // فحص شامل
```
