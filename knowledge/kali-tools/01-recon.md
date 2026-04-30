# الاستطلاع السلبي — Passive Reconnaissance

> جميع الأدوات هنا للاستخدام على أصولك المملوكة فقط.

---

## Whois — معلومات النطاق

```bash
whois example.com
```
**ما يكشفه:** مالك النطاق، تاريخ التسجيل، nameservers، بيانات الاتصال.

---

## Dig — استعلام DNS

```bash
# سجلات A
dig example.com A

# سجلات MX (البريد)
dig example.com MX

# سجلات TXT (التحقق، SPF، DKIM)
dig example.com TXT

# نقل المنطقة (zone transfer — غالباً مسدود)
dig axfr @ns1.example.com example.com

# تتبع كامل
dig +trace example.com
```

---

## TheHarvester — جمع بيانات عامة

يجمع: emails، subdomains، IPs، hosts من محركات البحث العامة.

```bash
theHarvester -d example.com -b google,bing,yahoo -l 200
```

**المصادر المدعومة:** google, bing, yahoo, shodan, hunter, dnsdumpster

---

## Shodan — محرك البحث عن الأجهزة

```bash
# من CLI
shodan search "hostname:example.com"
shodan host 1.2.3.4

# بحث عن خدمات محددة
shodan search "product:nginx country:SA"
shodan search "port:22 org:Saudi Telecom"
```

**ما يكشفه:** منافذ مفتوحة، إصدارات الخدمات، شهادات TLS، vulnerabilities CVE.

---

## DNSRecon — استطلاع DNS متقدم

```bash
# فحص قياسي
dnsrecon -d example.com

# brute force subdomains
dnsrecon -d example.com -D /usr/share/wordlists/dnsmap.txt -t brt

# Google enumeration
dnsrecon -d example.com -t goo
```

---

## Sublist3r — اكتشاف Subdomains

```bash
sublist3r -d example.com -o subdomains.txt
sublist3r -d example.com -b -p 80,443  # مع brute force
```

---

## Nslookup — استعلام DNS بسيط

```bash
nslookup example.com
nslookup -type=MX example.com
nslookup -type=NS example.com
```

---

## OSINT Framework — دليل الأدوات المفتوحة

الفئات الرئيسية:
- **Username:** Sherlock, Namechk
- **Email:** Hunter.io, EmailRep
- **IP/Domain:** Shodan, Censys, VirusTotal
- **Social:** SpiderFoot
- **Documents:** FOCA (metadata extraction)

---

## تفسير النتائج للذكاء الاصطناعي

عند إعطاء الأمين نتائج الاستطلاع، اسأله:
- "ما أهم المعلومات المكشوفة في هذا التقرير؟"
- "ما الثغرات المحتملة بناءً على هذه البيانات؟"
- "كيف أحمي هذه المعلومات من الكشف؟"
