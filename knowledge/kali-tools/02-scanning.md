# فحص المنافذ والشبكة — Network Scanning

> للاستخدام على أصولك المملوكة فقط — Sentinel Guard يتحقق من الملكية قبل أي فحص.

---

## Nmap — الرادار الشبكي

### فحص سريع
```bash
nmap -sn 192.168.1.0/24          # اكتشاف الأجهزة (ping sweep)
nmap -sV example.com              # إصدارات الخدمات
nmap -sS -p- example.com         # كل المنافذ (SYN scan)
nmap -A example.com               # فحص شامل (OS + version + scripts)
```

### الفحوصات الأكثر استخداماً
```bash
# أسرع فحص للمنافذ الـ 1000 الأشهر
nmap -T4 -F example.com

# فحص UDP (أبطأ لكن مهم)
nmap -sU --top-ports 20 example.com

# كشف نظام التشغيل
nmap -O example.com

# فحص مع scripts الأمنية
nmap --script=vuln example.com
nmap --script=ssl-enum-ciphers -p 443 example.com
nmap --script=http-headers example.com
```

### حفظ النتائج
```bash
nmap -oX results.xml example.com    # XML
nmap -oN results.txt example.com    # نص عادي
nmap -oA results example.com        # الثلاثة معاً
```

### تفسير الحالات
| الحالة | المعنى |
|--------|--------|
| open | المنفذ مفتوح وخدمة تستجيب |
| closed | المنفذ مغلق لكن الجهاز يرد |
| filtered | جدار ناري يحجب الاستجابة |
| open\|filtered | لا يمكن التحديد |

---

## Masscan — فحص سريع جداً

```bash
# فحص /24 بالكامل على المنفذ 443
masscan 192.168.1.0/24 -p443 --rate=1000

# فحص كل المنافذ
masscan example.com -p0-65535 --rate=10000
```

---

## Netcat — السكين السويسري

```bash
# فحص منفذ مفرد
nc -zv example.com 443

# فحص نطاق منافذ
nc -zv example.com 20-100

# قراءة banner الخدمة
echo "" | nc -w3 example.com 80
```

---

## OpenSSL — تحليل TLS

```bash
# فحص الشهادة
openssl s_client -connect example.com:443 </dev/null

# عرض تفاصيل الشهادة
openssl s_client -connect example.com:443 </dev/null | openssl x509 -text

# اختبار cipher محدد
openssl s_client -connect example.com:443 -cipher AES128-SHA

# فحص TLS 1.3
openssl s_client -connect example.com:443 -tls1_3
```

---

## أهم المنافذ ومعانيها

| المنفذ | البروتوكول | الخطر إذا مفتوح |
|--------|-----------|----------------|
| 22 | SSH | brute force إذا كلمة سر ضعيفة |
| 23 | Telnet | ⚠️ غير مشفر — خطر جداً |
| 25 | SMTP | Open relay إذا غير مضبوط |
| 80/443 | HTTP/HTTPS | Web vulnerabilities |
| 3306 | MySQL | ⚠️ يجب أن يكون مغلقاً من الإنترنت |
| 3389 | RDP | ⚠️ هجمات brute force شائعة |
| 6379 | Redis | ⚠️ بدون auth = كارثة |
| 27017 | MongoDB | ⚠️ كثير منها مكشوف بدون auth |

---

## تكامل مع Sentinel Guard

Sentinel Guard يستخدم `nmap3` (Python wrapper) تلقائياً عند `scan_type: "ports"`:
```json
{
  "asset_id": "uuid",
  "scan_type": "ports",
  "nmap_arguments": "-sV -T4 --top-ports 1000"
}
```
